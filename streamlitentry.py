import streamlit as st
from rfdetr import RFDETRNano
from utils import get_model
st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome")

username = st.text_input("(Optional) Enter your username", st.session_state.get("user_for_db", ""))

st.session_state.user_for_db = username.strip() if username else None

st.write("Current username:", st.session_state.user_for_db)

st.write(st.session_state.user_for_db)

model = get_model()

