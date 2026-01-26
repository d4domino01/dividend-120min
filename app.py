import streamlit as st

st.title("Dropdown Test")

with st.expander("ONE", expanded=True):
    st.write("First dropdown")

st.divider()

with st.expander("TWO"):
    st.write("Second dropdown")

st.divider()

with st.expander("THREE"):
    st.write("Third dropdown")

st.divider()

with st.expander("FOUR"):
    st.write("Fourth dropdown")
