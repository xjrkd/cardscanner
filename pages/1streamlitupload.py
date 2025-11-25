import streamlit as st
import requests # <--- You use requests to talk to your API
import base64
from PIL import Image
import io


st.set_page_config(page_title="Upload", page_icon="📈")

st.sidebar.header("Upload")
st.markdown("# Upload")
st.write(
    """Upload a file with trading cards here."""
)


uploaded_files = st.file_uploader("Upload Card", type=["jpg", "png"], accept_multiple_files=True)

for file in uploaded_files: 
    with st.spinner("Sending to API..."): 
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
                    st.write(card)
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
