import streamlit as st
import requests 
import base64
from PIL import Image, ImageOps
import io
from database import PokemonDatabase
from card_detector import CardDetector
from card_finder import CardFinder
from utils import get_model
import time

st.set_page_config(page_title="Upload", page_icon="📈")

st.sidebar.header("Upload")
st.markdown("# Upload")
st.write(
    """Upload a file with trading cards here. Alternatively you can also enter the cards name and HP and select the card manually.
    Selected cards can be added to the database."""
)

st.write("Using database:", st.session_state.database.db_name)

if "detector" not in st.session_state: 
    st.session_state.detector = CardDetector(get_model())

if "finder" not in st.session_state: 
    st.session_state.finder = CardFinder(st.session_state.detector)

placeholder = st.empty()
container = placeholder.container(border=True)

if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

if "matched_cards_list" not in st.session_state:
    st.session_state.matched_cards_list = []

if "multi_select_options" not in st.session_state:
    st.session_state.multi_select_options = []



def clear_input_field(): 
    st.session_state.manual_input_field = st.text_input("Enter card and HP manually. Or upload files below.", value="")

if "manual_input_field" not in st.session_state: 
    st.session_state.manual_input_field = ""

st.session_state.manual_input_field = st.text_input("Enter card and HP manually. Or upload files below.", value=st.session_state.manual_input_field)


uploaded_files = st.file_uploader("Upload Card", type=["jpg", "png"], accept_multiple_files=True, key=st.session_state["file_uploader_key"])

def scan_and_analyze_cards():

    # Check if new files have been uploaded
    if uploaded_files:
        # Convert upload list to filenames to compare
        uploaded_filenames = [f.name for f in uploaded_files]
        st.session_state["uploaded_files"] = uploaded_files
        # Run processing only if files changed
        if st.session_state.get("last_uploaded_files") != uploaded_filenames:
            st.session_state.last_uploaded_files = uploaded_filenames

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




def manual_card_input(): 
    if "manual_input_field" in st.session_state and st.session_state.manual_input_field != "":
        print("Manual INput st:", st.session_state.manual_input_field)
        mon = st.session_state.manual_input_field.split(";")[0]
        hp = st.session_state.manual_input_field.split(";")[-1].replace(";","")
        url = f"https://api.tcgdex.net/v2/de/cards?name={mon}&hp={hp}"
        response = requests.get(url).json()
        manual_multi_select = []
        for entry in response: 
            full_info_url = f"https://api.tcgdex.net/v2/de/cards/{entry['id']}"
            full_info = requests.get(full_info_url).json()
            entry["full_info"] = full_info
            entry["matched_pokemon"] = full_info["name"]
            entry["hp"] = hp
            entry["best_card_url"] = f'{full_info["image"]}/low.jpg'
            entry["missing_url"] = False
            manual_multi_select.append((full_info["name"], entry["id"]))
        
        # st.session_state.matched_cards_list.append(response)
        # st.session_state.multi_select_options = manual_multi_select
        return [response], manual_multi_select
    return [], []


def display(matched_cards_list, multi_select_options):
    with container:
        if matched_cards_list:
            for cards in matched_cards_list:    
                for i in range(0, len(cards), 3):
                    cols = container.columns(3)
                    for col, card in zip(cols, cards[i:i+3]):
                        col.image(card["best_card_url"])
                        if card["missing_url"]: 
                            warning_missing_url = "Warning: Incomplete API Database. Card might be wrong!"
                        else: 
                            warning_missing_url = ""
                        col.write(f'{card["matched_pokemon"], card["id"], warning_missing_url }')

        multi_select = st.multiselect(
            "Exclude the following cards from being added to the database",
            multi_select_options,
        )
        return multi_select

def add_cards_to_database(selection): 
    if "matched_cards_list" not in st.session_state:
        st.session_state.matched_cards_list = []
    if not st.session_state.matched_cards_list:
        print("returning, no cards list (None)")
        return  
    
    ids_to_remove = [id[1] for id in selection]
    cards_to_add_to_database = [card for card in st.session_state.matched_cards_list[0] if card["id"] not in ids_to_remove]
    
    if st.button("Submit to database"):
        st.session_state.database.insert_card_data(cards_to_add_to_database, f"{st.session_state.database.db_name}")
        placeholder.empty()
        st.session_state["file_uploader_key"] += 1
        st.session_state.matched_cards_list = []            #Reset so old card isn't displayed anymore
        st.session_state.multi_select_options = []
        st.session_state.manual_input_field = st.text_input("Enter card and HP manually. Or upload files below.", value="", on_change=clear_input_field)
        print(st.session_state.multi_select_options, st.session_state.matched_cards_list)
        st.rerun()
    
def manage_selection_and_submit(matched_cards_list, multi_select_options):
    with container:
        # Interaction with widgets inside here WON'T trigger a rerun.
        with st.form("validation_form"):
            
            # Display Logic 
            if matched_cards_list:
                for cards in matched_cards_list:    
                    for i in range(0, len(cards), 3):
                        cols = st.columns(3) # Use st.columns inside the form
                        for col, card in zip(cols, cards[i:i+3]):
                            col.image(card["best_card_url"])
                            if card["missing_url"]: 
                                warning_missing_url = "Warning: Incomplete API Database."
                            else: 
                                warning_missing_url = ""
                            col.write(f'{card["matched_pokemon"], card["id"], warning_missing_url }')

            # Multiselect Logic
            selection = st.multiselect(
                "Exclude the following cards from being added to the database",
                multi_select_options,
            )

            # Submit Button 
            submitted = st.form_submit_button("Submit to database")
            
            if submitted:
                if not st.session_state.matched_cards_list:
                    st.warning("No cards to add.")
                    return

                ids_to_remove = [id[1] for id in selection]
                
                cards_to_add_to_database = [
                    card for card in st.session_state.matched_cards_list[0] 
                    if card["id"] not in ids_to_remove
                ]
                
                st.session_state.database.insert_card_data(
                    cards_to_add_to_database, 
                    f"{st.session_state.database.db_name}"
                )
                
                # Cleanup 
                placeholder.empty()
                st.session_state["file_uploader_key"] += 1
                st.session_state.matched_cards_list = []
                st.session_state.multi_select_options = []
                
                # Clear manual input variable directly in state
                st.session_state.manual_input_field = "" 
                
                st.rerun()



##Main
if uploaded_files: 
    print("files uploaded")
    matched_cards_list, multi_select_options = scan_and_analyze_cards()
    manage_selection_and_submit(matched_cards_list, multi_select_options)
    
if "manual_input_field" in st.session_state and st.session_state.manual_input_field != "":
    print("manual input")
    manual_matched_cards, manual_multi_select = manual_card_input()
    if manual_matched_cards:
        st.session_state.matched_cards_list = manual_matched_cards 
        st.session_state.multi_select_options = manual_multi_select
    manage_selection_and_submit(manual_matched_cards, manual_multi_select)





# ###Matched_cards_list 
#[
# {'matched_pokemon': 'Darkrai', 'hp': '130', 'card': array([[[146, 139, 121],
        
#         [124, 117,  99],
#         [164, 157, 139]]], shape=(1112, 855, 3), dtype=uint8), 'best_card_url': 'https://assets.tcgdex.net/de/sv/sv03/136/low.jpg', 'template_card': array([[[0, 0, 0],
#         [0, 0, 0],
        
#         [0, 0, 0]]], shape=(337, 245, 3), dtype=uint8), 'id': 'sv03-136', 'missing_url': False, 'full_info': {'category': 'Pokémon', 'id': 'sv03-136', 'illustrator': 'Bun Toujo', 'image': 'https://assets.tcgdex.net/de/sv/sv03/136', 'localId': '136', 'name': 'Darkrai', 'rarity': 'Selten', 'set': {...}, 'variants': {...}, 'variants_detailed': [...], 'dexId': [...], 'hp': 130, 'types': [...], 'stage': 'Basis', 'attacks': [...], 'retreat': 2, 'regulationMark': 'G', 'legal': {...}, 'updated': '2025-08-16T20:39:55Z', ...}}
#]

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
