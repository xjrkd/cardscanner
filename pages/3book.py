import streamlit as st
import sqlite3 
import pandas as pd 
import cv2
import numpy as np
from urllib.request import urlopen
from PIL import Image
import requests
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Book", page_icon="")

st.sidebar.header("Book")
st.markdown("# Book")

conn = sqlite3.connect('portfolio.db')
cursor = conn.cursor()



def get_set_names(): 
    cursor.execute("SELECT DISTINCT set_name, set_id FROM set_info")
    row = cursor.fetchall()

    set_selector = st.selectbox("Select a set", (f"{name}-{setid}" for name,setid in row))
    st.write(set_selector.split("-")[-1])

    get_all_images_from_set(set_selector.split("-")[-1])

@st.cache_data          #Cache img data to avoid calling api multiple times
def fetch_images(url:str, _session: requests.sessions.Session) -> np.ndarray:  
    '''
    Fetch images from tcgdex.dev.
    If no image is found with low suffix then high is used to get the image.
    If there is also no image return a 50x50 grayscale image
    
    :param url: Image Url for tcgdex
    :param _session: requests session
    '''
    try: 
        response = _session.get(url) #TODO improve performance
        image_bytes = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    except cv2.error as e: 
        response = _session.get(url.replace("low","high")) #TODO improve performance
        image_bytes = np.asarray(bytearray(response.content), dtype=np.uint8)
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray
    except: 
       return (np.random.randint(0, 256, size=(50, 50), dtype=np.uint8))


def get_all_images_from_set(set_id: str, cols_per_row: int = 4): 
    cursor.execute("SELECT image_url, card_id FROM set_info WHERE set_id = ? ORDER BY id ASC",(set_id,))
    rows = cursor.fetchall()
 
    img_urls = [(image, card_id) for image, card_id in rows] #Create tuple of url and card_id for later check

    cursor.execute("SELECT id FROM pokemon_cards WHERE set_id = ?",(set_id,))
    owned_cards_rows = cursor.fetchall()
    owned_cards_rows = [x[0] for x in owned_cards_rows]

    #print(img_urls)
    session = requests.Session()
    for i in range(0, len(img_urls), cols_per_row): 
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if (i+j)>=len(img_urls): 
                continue    #Stopping if row ends on e.g. 2/4 cards 
            if img_urls[i+j][1] in owned_cards_rows:
                col.image(img_urls[i+j][0])
            else: 
                #print(img_urls[i+j][0])
                gray = fetch_images(img_urls[i+j][0], session)
                col.image(gray)
        i=i+j


get_set_names()