import streamlit as st
from database import PokemonDatabase
st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write('''
         # Welcome
        A name can be entered on this page to create a separate database, allowing multiple users to manage their collections independently.
         
        Upload an image on the Upload page to have it analyzed. Detected cards can be selected and added to the database.
        
        The Portfolio page provides insights into card value trends over time, the total number of cards collected, the number of unique cards, and distribution statistics
             ''')

username = st.text_input("(Optional) Enter your username", st.session_state.get("user_for_db", ""))

st.session_state.user_for_db = username.strip() if username else None

st.write("Current username:", st.session_state.user_for_db)

st.write(st.session_state.user_for_db)

# if "database" not in st.session_state:

username = st.session_state.get("user_for_db")

if username:
    db_name = f"{username}.db"
else:
    db_name = "portfolio.db"

st.session_state.database = PokemonDatabase(db_name)
st.session_state.language = st.selectbox("Choose language", ("de","en"))

from utils import get_model
model = get_model()

