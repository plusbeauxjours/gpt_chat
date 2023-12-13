import streamlit as st

st.title("sidebar")

with st.sidebar:
    st.sidebar.title("sidebar")
    st.sidebar.text_input("sidebainputr")

tab_one, tab_two, twb_three, tab_four = st.tabs(["a", "b", "c", "d"])

with tab_one:
    st.write("one")

with tab_two:
    st.write("two")

with twb_three:
    st.write("three")

with tab_four:
    st.write("four")
