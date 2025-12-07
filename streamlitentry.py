import streamlit as st
from rfdetr import RFDETRNano

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome")

@st.cache_resource
def get_model(): 
    with st.spinner("Loading Model"):
       return RFDETRNano(pretrain_weights="E:\\PythonProjects\\pokemon\\rfdetr_train\\checkpoint0004.pth")


get_model()

