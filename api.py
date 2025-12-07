from fastapi import FastAPI, UploadFile, File
from PIL import Image, ImageOps
import io
import pandas as pd
# Import your existing classes
# Assuming your classes are in a file named 'my_pokemon_logic.py' or similar
from main import CardDetector, CardFinder, PokemonDatabase
from rfdetr import RFDETRNano
import base64
import numpy as np
import cv2

app = FastAPI()

# GLOBAL VARIABLES
# We define these outside of functions so they load ONLY ONCE when the server starts.
# If we put this inside the function, your app would freeze for 5 seconds on every request to load the model.
print("Loading AI Models... please wait...")
model = RFDETRNano(pretrain_weights="E:\\PythonProjects\\pokemon\\rfdetr_train\\checkpoint0004.pth")
carddetector = CardDetector(model)
cardfinder = CardFinder(carddetector=carddetector)
database = PokemonDatabase(db_name="portfolio.db")
print("AI Models loaded! Server is ready.")

@app.get("/")
def home():
    return {"message": "Pokemon Card Scanner API is running!"}

@app.post("/scan")
async def scan_card(file: UploadFile = File(...)):
    """
    This endpoint receives an image file from the App,
    processes it, saves to DB, and returns the results.
    """
    
    # 1. Read the image bytes sent
    image_data = await file.read()
    
    # 2. Convert bytes to a PIL Image
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image) # FIX phone error EXIF Orientation.
    # When you take a photo with a phone, the camera saves the pixels in the orientation of the sensor (usually "sideways" or landscape), even if you held the phone vertically. It adds a metadata tag (EXIF) saying "Rotate this 90 degrees when viewing."
    
    # Detect cards
    detections = carddetector.detect_cards(image)
    
    # Snip cards
    snipped_cards = carddetector.snip_cards(image, detections)
    
    # OCR
    ocr_result_array = carddetector.ocr_on_image(snipped_cards)
    
    # Match
    matched_cards = carddetector.match_cards(ocr_result_array)
    
    # Find & Price
    matched_cards = cardfinder.find_cards(matched_cards)
    matched_cards = cardfinder.get_pricing(matched_cards)
    
    # Database
    # Note: In a real app, we might want to ask the user to "Confirm" before saving,
    # but for now, we save immediately like your script did.
    database.insert_card_data(matched_cards)  
  
    response_data = convert_nparray_to_string(matched_cards)
    # Return the data as JSON so the App can display it
    print("Breakpoint")
    return {"status": "success", "cards": response_data}


def convert_nparray_to_string(matched_cards: list) -> list: 
    for card in matched_cards:
        image_array_card = card.get("card")
        image_array_template = card.get("template_card")
        if isinstance(image_array_card, np.ndarray) and isinstance(image_array_template, np.ndarray):
            # 1. Encode array to jpg (compressed)
            image_array_card = cv2.cvtColor(image_array_card, cv2.COLOR_RGB2BGR) #Solves RGB/BGR issues 
            image_array_template = cv2.cvtColor(image_array_template, cv2.COLOR_RGB2BGR)
            success_card, buffer_card = cv2.imencode(".jpg", image_array_card)
            success_template, buffer_template = cv2.imencode(".jpg", image_array_template)
            if success_card and success_template:
                # 2. Convert to base64 string
                jpg_as_text_card = base64.b64encode(buffer_card).decode('utf-8')
                jpg_as_text_template = base64.b64encode(buffer_template).decode('utf-8')
                card["card"] = jpg_as_text_card
                card["template_card"] = jpg_as_text_template

    return matched_cards