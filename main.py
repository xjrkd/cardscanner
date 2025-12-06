import re
from rfdetr import RFDETRNano
from card_detector import CardDetector
from card_finder import CardFinder
import sqlite3
import json
from PIL import Image
from database import PokemonDatabase
import matplotlib.pyplot as plt

def main():
    model = RFDETRNano(pretrain_weights="E:\\PythonProjects\\pokemon\\rfdetr_train\\checkpoint0004.pth")
    carddetector = CardDetector(model)
    image = Image.open("E:\PythonProjects\pokemon\images\kokowei.jpg")
    detections = carddetector.detect_cards(image)
    snipped_cards = carddetector.snip_cards(image, detections)
    ocr_result_array = carddetector.ocr_on_image(snipped_cards)
    matched_cards = carddetector.match_cards(ocr_result_array)
    # ### API Eigene Klasse 
    cardfinder = CardFinder(carddetector=carddetector)
    matched_cards = cardfinder.find_cards(matched_cards)
    matched_cards = cardfinder.get_pricing(matched_cards)
    print("--------------------------------------------------- \n \n")
    print(matched_cards)
    
    ### Database 
    database = PokemonDatabase(db_name="portfolio.db")
    #database.create_tables()
    # database.migrate_add_quantity_to_pricing()
    database.insert_card_data(matched_cards)

    

# Insert the card data into the database

if __name__ == "__main__":
    main()
    #insert_card_data(card_data)