import streamlit as st
import requests 
import base64
from PIL import Image, ImageOps
import io
from database import PokemonDatabase
from card_detector import CardDetector
from card_finder import CardFinder
from utils import get_model

st.set_page_config(page_title="Upload", page_icon="📈")

st.sidebar.header("Upload")
st.markdown("# Upload")
st.write(
    """Upload a file with trading cards here."""
)

if "database" not in st.session_state:

    username = st.session_state.get("user_for_db")

    if username:
        db_name = f"{username}.db"
    else:
        db_name = "portfolio.db"

    st.session_state.database = PokemonDatabase(db_name)

st.write("Using database:", st.session_state.database.db_name)

if "detector" not in st.session_state: 
    st.session_state.detector = CardDetector(get_model())

if "finder" not in st.session_state: 
    st.session_state.finder = CardFinder(st.session_state.detector)

placeholder = st.empty()
container = placeholder.container(border=True)


def scan_and_analyze_cards():
    uploaded_files = st.file_uploader("Upload Card", type=["jpg", "png"], accept_multiple_files=True)

    # Check if new files have been uploaded
    if uploaded_files:
        # Convert upload list to filenames to compare
        uploaded_filenames = [f.name for f in uploaded_files]

        # Run processing only if files changed
        if st.session_state.get("last_uploaded_files") != uploaded_filenames:
            st.session_state.last_uploaded_files = uploaded_filenames
            st.session_state.matched_cards_list = []
            st.session_state.multi_select_options = [] #list of tuples

            for file in uploaded_files:
                with st.spinner("Processing..."):
                    try:
                        image_data = file.read()
                        image = Image.open(io.BytesIO(image_data))
                        image = ImageOps.exif_transpose(image) # FIX phone error EXIF Orientation. # When you take a photo with a phone, the camera saves the pixels in the orientation of the sensor (usually "sideways" or landscape), even if you held the phone vertically. It adds a metadata tag (EXIF) saying "Rotate this 90 degrees when viewing."

                        detections = st.session_state.detector.detect_cards(image)
                        snipped_cards = st.session_state.detector.snip_cards(image, detections)
                        ocr_result_array = st.session_state.detector.ocr_on_image(snipped_cards)
                        matched_cards = st.session_state.detector.match_cards(ocr_result_array)
                        matched_cards = st.session_state.finder.find_cards(matched_cards)
                        matched_cards = st.session_state.finder.get_pricing(matched_cards)

                        st.session_state.matched_cards_list.append(matched_cards)

                        for card in matched_cards:
                            st.session_state.multi_select_options.append(
                                (card["matched_pokemon"], card["id"])
                            )

                    except Exception as e:
                        st.error(f"Processing error: {e}")

    return (
        st.session_state.get("matched_cards_list", []),
        st.session_state.get("multi_select_options", []),
    )

def display(matched_cards_list, multi_select_options):
    with container:
        if matched_cards_list:
            for card in matched_cards_list[0]:
                st.image(card["best_card_url"])
                st.write(card["matched_pokemon"])

        multi_select = st.multiselect(
            "Exclude the following cards from being added to the database",
            multi_select_options,
            )
        return multi_select

def add_cards_to_database(selection): 
    if "matched_cards_list" not in st.session_state:
        st.session_state.matched_cards_list = []
    if not st.session_state.matched_cards_list:
        return  
    
    ids_to_remove = [id[1] for id in selection]
    cards_to_add_to_database = [card for card in st.session_state.matched_cards_list[0] if card["id"] not in ids_to_remove]
    #print(st.session_state.matched_cards_list)
    if st.button("Submit to database"):
        st.session_state.database.insert_card_data(cards_to_add_to_database, f"{st.session_state.database.db_name}")
        placeholder.empty()

matched_cards_list, multi_select_options = scan_and_analyze_cards()
multi_select = display(matched_cards_list, multi_select_options)
add_cards_to_database(multi_select)






##Deprecated

def api_request(): 
    uploaded_files = st.file_uploader("Upload Card", type=["jpg", "png"], accept_multiple_files=True)

    for file in uploaded_files: 
        with st.spinner("Processing..."): 
            try: 
                response = requests.post("http://127.0.0.1:8000/scan", files={"file": file})
                if response.status_code == 200:
                    data = response.json()
                    cards = data["cards"]
                    
                    st.success(f"API found {len(cards)} cards")
                    print(f"CARDS: \n \n {cards} \n \n")
                    # 3. Decode the Base64 string back to an image to show it
                    for card in cards:
                        pricing = card.get('pricing', {})
                        #st.write(card)
                        # 2. Extract Cardmarket specifically
                        # Use .get() here because 'pricing' might not contain 'cardmarket'
                        cm_data = pricing.get('cardmarket')

                        # 3. Check if we actually found data (it might be None)
                        if cm_data:
                            price = cm_data.get('avg', 'N/A')
                            currency = cm_data.get('unit', '€')
                            price_display = f"{price} {currency}"
                        else:
                            price_display = "No Price Found"

                        # 4. Display it
                        st.write(f"**{card['matched_pokemon']}** - {pricing}")
                        
                        # Clean the base64 string if necessary
                        b64_str = card['template_card']
                        image_data = base64.b64decode(b64_str)
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image)
                else:
                    st.error(f"API Error: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to API. Is 'uvicorn api:app' running?")
