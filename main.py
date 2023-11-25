from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI

llm = OpenAI()
a = llm.predict("How many planets are there?")

chat = ChatOpenAI()
b = chat.predict("How many planets are there?")

a, b 
print(a)
print(b)