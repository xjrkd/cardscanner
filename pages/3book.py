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
st.write(f"Connected to {st.session_state.database.db_name}")

conn = sqlite3.connect(f"{st.session_state.database.db_name}")
cursor = conn.cursor()


def get_set_names(): 
    '''
    Retrieves all distinct Pokémon card set names and set IDs from the database,
    displays them in a Streamlit selectbox, and triggers loading of all images 
    for the selected set.
    - Queries the `set_info` table for unique (set_name, set_id) pairs.
    - Lets the user pick a set via a Streamlit dropdown formatted as "name-id".
    - Extracts the selected set_id.
    - Calls `get_all_images_from_set()` with the chosen set_id.

    '''
    cursor.execute("SELECT DISTINCT set_name, set_id FROM set_info")
    row = cursor.fetchall()
    options = [f"{name}-{setid}" for name,setid in row]
    options.append("Cards-in-collection")
    set_selector = st.selectbox("Select a set", options)
    # st.write(set_selector.split("-")[-1])

    if set_selector ==  "Cards-in-collection": 
        cursor.execute("SELECT card_id, name, set_name, image_url FROM pokemon_cards")
        rows = cursor.fetchall()
        image_urls = [(image_url, id) for id, name, set_name, image_url in rows]
        card_ids = [id for id, name, set_name, image_url in rows]
        draw_cards(image_urls, 4, card_ids)
    else:
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


def draw_cards(img_urls: list, cols_per_row: int, owned_cards_rows: list): 
    '''
    Draws cards in a Ax4 grid.  
    
    :param img_urls: List of tuples consisting of (image_urls, card_id) to be displayed
    :param cols_per_row: Integer determining how many cols are displayed
    :param owned_cards_rows: List of owend cards to be drawn in color
    '''
    session = requests.Session()
    for i in range(0, len(img_urls), cols_per_row): 
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if (i+j)>=len(img_urls): 
                continue    #Stopping if row ends on e.g. 2/4 cards 
            if img_urls[i+j][1] in owned_cards_rows and img_urls[i+j][0] is not None :
                col.image(img_urls[i+j][0])
            else: 
                #print(img_urls[i+j][0])
                gray = fetch_images(img_urls[i+j][0], session)
                col.image(gray)
        i=i+j


def get_all_images_from_set(set_id: str, cols_per_row: int = 4): 
    '''Displays all card images from a given Pokémon card set in a grid layout.

    This function:
    - Retrieves all image URLs and card IDs for the specified set from the `set_info` table.
    - Retrieves card IDs owned by the user from the `pokemon_cards` table.
    - Displays the sets images in a Streamlit grid with `cols_per_row` columns.
    - Shows owned cards in full color.
    - Shows unowned cards in grayscale (fetched using `fetch_images`).
    
    Args:
        set_id (str): The unique identifier of the card set to display.
        cols_per_row (int, optional): Number of images to display per row. 
                                      Defaults to 4.
    '''
    
    cursor.execute("SELECT image_url, card_id FROM set_info WHERE set_id = ? ORDER BY id ASC",(set_id,)) #Full Set
    rows = cursor.fetchall()
 
    img_urls = [(image, card_id) for image, card_id in rows] #Create tuple of url and card_id for later check

    cursor.execute("SELECT card_id FROM pokemon_cards WHERE set_id = ?",(set_id,))    #Owned cards
    owned_cards_rows = cursor.fetchall()
    owned_cards_rows = [x[0] for x in owned_cards_rows]

    draw_cards(img_urls, cols_per_row, owned_cards_rows)


get_set_names()