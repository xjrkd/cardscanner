import streamlit as st
from rfdetr import RFDETRNano


@st.cache_resource
def get_model():
    with st.spinner("Loading Model"):
        model = RFDETRNano(pretrain_weights=".\\rfdetr_train\\checkpoint0004.pth")
    return model