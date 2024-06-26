import streamlit as st
import subprocess
import math
from pydub import AudioSegment
import glob
import openai
import os
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import StrOutputParser
from langchain.vectorstores.faiss import FAISS
from langchain.embeddings import OpenAIEmbeddings, CacheBackedEmbeddings
from langchain.memory import ConversationSummaryBufferMemory, ConversationBufferMemory
from langchain.storage import LocalFileStore
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda


class ChatCallbackHandler(BaseCallbackHandler):
    message = ""

    def on_llm_start(self, *args, **kwargs):
        self.message_box = st.empty()

    def on_llm_end(self, *args, **kwargs):
        save_message(self.message, "ai")

    def on_llm_new_token(self, token, *args, **kwargs):
        self.message += token
        self.message_box.markdown(self.message)


llm = ChatOpenAI(
    temperature=0.1,
    streaming=True,
    callbacks=[
        ChatCallbackHandler(),
    ],
)

summary_llm = ChatOpenAI(
    temperature=0.1,
    streaming=True,
)

memory = ConversationBufferMemory(
    llm=llm,
    max_token_limit=120,
    memory_key="chat_history",
    return_messages=True,
)

has_transcript = os.path.exists("./.cache/podcast.txt")

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=800,
    chunk_overlap=100,
)


@st.cache_data()
def embed_file(file_path):
    cache_dir = LocalFileStore(f"./.cache/embeddings/{file.name}")
    loader = TextLoader(file_path)
    docs = loader.load_and_split(text_splitter=splitter)
    embedder = OpenAIEmbeddings()
    cached_embeddings = CacheBackedEmbeddings.from_bytes_store(embedder, cache_dir)
    vectorstore = FAISS.from_documents(docs, cached_embeddings)
    retriever = vectorstore.as_retriever()
    return retriever


def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})


def save_memory(input, output):
    st.session_state["chat_history"].append({"input": input, "output": output})


def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)


def paint_history():
    for message in st.session_state["messages"]:
        send_message(message["message"], message["role"], save=False)


def restore_memory():
    for history in st.session_state["chat_history"]:
        memory.save_context({"input": history["input"]}, {"output": history["output"]})


def format_docs(docs):
    return "\n\n".join(document.page_content for document in docs)


def load_memory(input):
    return memory.load_memory_variables({})["chat_history"]


def invoke_chain(message):
    result = chain.invoke(message)
    save_memory(message, result.content)


@st.cache_data()
def transcribe_chunks(chunk_folder, destination):
    if has_transcript:
        return
    files = glob.glob(f"{chunk_folder}/*.mp3")
    files.sort()
    for file in files:
        with open(file, "rb") as audio_file, open(destination, "a") as text_file:
            transcript = openai.Audio.transcribe(
                "whisper-1",
                audio_file,
            )
            text_file.write(transcript["text"])


@st.cache_data()
def extract_audio_from_video(video_path):
    if has_transcript:
        return
    audio_path = video_path.replace("mp4", "mp3")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        audio_path,
    ]
    subprocess.run(command)


@st.cache_data()
def cut_audio_in_chunks(audio_path, chunk_size, chunks_folder):
    if has_transcript:
        return
    track = AudioSegment.from_mp3(audio_path)
    chunk_len = chunk_size * 60 * 1000
    chunks = math.ceil(len(track) / chunk_len)
    for i in range(chunks):
        start_time = i * chunk_len
        end_time = (i + 1) * chunk_len
        chunk = track[start_time:end_time]
        chunk.export(
            f"./{chunks_folder}/chunk_{i}.mp3",
            format="mp3",
        )


st.set_page_config(
    page_title="MeetingGPT",
    page_icon="💼",
)

st.markdown(
    """
        # MeetingGPT
        Welcome to MeetingGPT, upload a video and I will give you a transcript,
        a summary and a chat bot to ask any questions about it.
        Get started by uploading a video file in the sidebar.
    """
)

with st.sidebar:
    video = st.file_uploader(
        "Video",
        type=["mp4", "avi", "mkv", "mov"],
    )

if video:
    chunks_folder = "./.cache/chunks"
    with st.status("Loading video...") as status:
        video_content = video.read()
        video_path = f"./.cache/{video.name}"
        audio_path = video_path.replace("mp4", "mp3")
        transcript_path = video_path.replace("mp4", "txt")
        with open(video_path, "wb") as f:
            f.write(video_content)
        status.update(label="Extracting audio...")
        extract_audio_from_video(video_path)
        status.update(label="Cutting audio segments...")
        cut_audio_in_chunks(audio_path, 10, chunks_folder)
        status.update(label="Transcribing audio...")
        status.update(label="Complete.")
        transcribe_chunks(chunks_folder, transcript_path)

    transcript_tab, summary_tab, qa_tab = st.tabs(
        [
            "Transcript",
            "Summary",
            "Q&A",
        ]
    )

    with transcript_tab:
        with open(transcript_path, "r") as file:
            st.write(file.read())

    with summary_tab:
        generate = st.button("Generate summary")

        if generate:
            loader = TextLoader(transcript_path)
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=800,
                chunk_overlap=100,
            )
            docs = loader.load_and_split(text_splitter=splitter)

            first_summary_prompt = ChatPromptTemplate.from_template(
                """
                Write a concise summary of the following:
                "{text}"
                CONCISE SUMMARY:                
            """
            )

            first_summary_chain = first_summary_prompt | summary_llm | StrOutputParser()

            summary = first_summary_chain.invoke(
                {"text": docs[0].page_content},
            )

            refine_prompt = ChatPromptTemplate.from_template(
                """
                    Your job is to produce a final summary.
                    We have provided an existing summary up to a certain point: {existing_summary}
                    We have the opportunity to refine the existing summary (only if needed) with some more context below.
                    ------------
                    {context}
                    ------------
                    Given the new context, refine the original summary.
                    If the context isn't useful, RETURN the original summary.
                """
            )

            refine_chain = refine_prompt | summary_llm | StrOutputParser()

            with st.status("Summarizing...") as status:
                for i, doc in enumerate(docs[1:]):
                    status.update(label=f"Processing document {i+1}/{len(docs)-1} ")
                    summary = refine_chain.invoke(
                        {
                            "existing_summary": summary,
                            "context": doc.page_content,
                        }
                    )
                    st.write(summary)

    with qa_tab:
        retriever = embed_file(transcript_path)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                        Answer the question using ONLY the following context. If you don't know the answer, just say you don't know. DO NOT MAKE UP anything.
                        Context:{context}
                    """,
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        send_message("Ask anything about the video", "ai", save=False)
        restore_memory()
        paint_history()
        question = st.text_input("Type your question here.")
        if question:
            send_message(question, "human")
            chain = (
                {
                    "context": retriever | RunnableLambda(format_docs),
                    "chat_history": load_memory,
                    "question": RunnablePassthrough(),
                }
                | prompt
                | llm
            )
            with st.chat_message("ai"):
                invoke_chain(question)
else:
    st.session_state["messages"] = []
    st.session_state["chat_history"] = []
