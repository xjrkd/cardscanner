from rfdetr import RFDETRNano
from card_detector import CardDetector
from card_finder import CardFinder
import argparse
from PIL import Image
from database import PokemonDatabase
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--path", required=True)
parser.add_argument("--db_name", required=True)
parser.add_argument("--model_path", required=True)
args = parser.parse_args()
model = RFDETRNano(pretrain_weights=args.model_path)
carddetector = CardDetector(model)
cardfinder = CardFinder(carddetector=carddetector)

def main():
    dir = Path(args.path)
    if dir.is_dir(): 
        files = dir.iterdir()
    else: 
        files = [dir]
    
    for file in files:
        if str(file).endswith((".png",".jpg",".JPEG")): 
            image = Image.open(file)
            detections = carddetector.detect_cards(image)
            snipped_cards = carddetector.snip_cards(image, detections)
            ocr_result_array = carddetector.ocr_on_image(snipped_cards)
            matched_cards = carddetector.match_cards(ocr_result_array)
            
            ## Cardfinder
            matched_cards = cardfinder.find_cards(matched_cards)
            matched_cards = cardfinder.get_pricing(matched_cards)
            print("--------------------------------------------------- \n \n")
            
            ### Database 
            database = PokemonDatabase(db_name = args.db_name)
            database.create_tables()
            database.insert_card_data(matched_cards, db_name = args.db_name)
            database.fill_portfolio_values()
        

if __name__ == "__main__":
    main()