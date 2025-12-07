from rfdetr import RFDETRNano
import supervision as sv
from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt
from rapidocr import RapidOCR
import matplotlib.pyplot as plt
import pandas as pd 
import urllib.request
import re
from rapidfuzz import fuzz, process
import re, unicodedata
import sqlite3
import torch


class CardDetector: 
    def __init__(self, model=None):
        self.model = model
        self.pokedex_csv = pd.read_csv("international_dex.csv") #With international names, further has attacks etc. https://www.pokecommunity.com/threads/international-list-of-names-in-csv.460446/

    # def initialize_model(self, model):
    #     self.model = model

    def initialize_paths(): 
        ds = sv.DetectionDataset.from_coco(
        images_directory_path="E:\\PythonProjects\\pokemon\\cardsdataset\\data\\test",
        annotations_path="E:\\PythonProjects\\pokemon\\cardsdataset\\data\\test\\_annotations.coco.json",
        )
        return ds

    def detect_cards(self, image):
        predictions = []
        detections = self.model.predict(image, threshold=0.2)
        predictions.append(detections)
        return detections

    def snip_cards(self, image, detections)->list: 
        '''
        Crops detected bounding boxes of cards from the image and returns them in a list.
        '''
        image_np = np.array(image)
        cards_array = []
        for i, box in enumerate(detections.xyxy,0): 
                x1, y1, x2, y2 = map(int, box)
                crop = image_np[y1:y2, x1:x2]
                cards_array.append(crop)
        return cards_array
    

    def ocr_on_image(self, cards_array)->list: 
        '''
        Perform OCR on an array of cards. Returns a list of dictionaries containing the detected texts and xy positions. 
        '''
        engine = RapidOCR()

        ocr_result_array = []
        for i, card in enumerate(cards_array): 
            result = engine(card)

            # Extract per-word info
            boxes = result.boxes
            texts = result.txts  # RapidOCR returns recognized text strings here
            scores = result.scores if hasattr(result, "scores") else [None] * len(texts)

            card_height, card_width = card.shape[:2]

            # Build structured result
            detections = []
            for text, box, score in zip(texts, boxes, scores):
                # box is 4x2 array -> extract average y (vertical position) (4x [x,y])
                y_mean = np.mean([pt[1] for pt in box])
                x_mean = np.mean([pt[0] for pt in box])
                detections.append({
                    "text": text,
                    "box": box,
                    "score": score,
                    "y_mean": y_mean,
                    "relative_y": y_mean / card_height,  # normalized position 0-1
                    "x_mean": x_mean,
                    "relative_x": x_mean/card_width,
                    "card_height": card_height,
                    "card_width": card_width,
                    "card":card
                })

            # Sort detections top-to-bottom
            detections.sort(key=lambda d: d["y_mean"])

            ocr_result_array.append({
                "card_index": i,
                "detections": detections,
            })

        return ocr_result_array


    def normalize_detected_name(self, name: str, dex: bool, pokedex=None) -> str:
        '''
        Normalize names from pokedex csv and detected names. 
        Removes prefixes and suffixes such as "alola or ex".
        '''
        # Unicode normalize and lowercase
        name = unicodedata.normalize("NFKD", name).lower().strip()
        # Replace dash-like chars with '-'
        name = re.sub(r"[–—−]", "-", name)
        # Remove ex-like suffixes, only on runs with ocr not pokedex
        name = re.sub(r"^alolan?\s*-?\s*", "", name)
        if not dex:
            match_found= False
            for key in sorted(pokedex.keys(), key=len, reverse=True):
                if name.startswith(key): 
                    name = key
                    match_found = True
                    break
            if not match_found:
                name = re.sub(r"(-?\s*ex|alola)$", "", name) #TODO ex|e|x war vorher -> führt dazu dass beim matchen blastoise blastois wird -> kein treffer
        # Remove other non-alphanumeric chars
        name = re.sub(r"[^a-z0-9-]", "", name)
        
        return name

    def find_hp(self, detection)->str: 
        '''
        Searches for hp value in a certain area of the card.
        Returns the string value of hp.
        '''
        # print(type(result))
        top_texts = []
        #print(f"{detection} \n")
        hp = re.sub(r'[^0-9]', '', detection["text"])
        if hp and detection["relative_y"] <= 0.2 and detection["relative_x"] >=0.6:
            print("FIND HP: ",hp)
            if 999<int(hp):             #Quick fix
                hp=hp[:-1]
            # top_texts.append(hp)
            return hp
        
    def match_cards(self, ocr_result_array)->list:
        # Prepare normalized Pokédex list once
        '''
        Iterates through the entire ocr detected text to match detections against names from the pokedex.csv file.
        Returns a list of dictionaries containing name, image and hp.
        '''
        normalized_pokedex = {self.normalize_detected_name(p, True): p for p in self.pokedex_csv["de"]}
        matched_pokemon = []


        for i, result in enumerate(ocr_result_array):
            top_texts = []
            matched_pokemon_for_this_card ={}

            for detection in result["detections"]:
                detected_text = detection["text"]
                
                cleaned = self.normalize_detected_name(detected_text, False, normalized_pokedex)
                
                hp_texts = self.find_hp(detection)
                if hp_texts:
                    top_texts.append(hp_texts)
                

                if len(cleaned) < 4:
                    continue  # skip short, unreliable OCR results like "Tera", "ex", "HP"

                # Fuzzy match only if exact match fails
                #print("cleaned:", cleaned)
                if cleaned in normalized_pokedex:
                    print(f"Matched: {normalized_pokedex[cleaned]} (from '{detected_text}')")
                    
                    matched_pokemon_for_this_card["matched_pokemon"] = normalized_pokedex[cleaned]     #convert to dict with hp
                    
            print("All Found HP Texts: ", top_texts)
            matched_pokemon_for_this_card["hp"] = top_texts[0]
            matched_pokemon_for_this_card["card"] = ocr_result_array[i]["detections"][0]["card"]
            matched_pokemon.append(matched_pokemon_for_this_card)

        print(f"\n \n Matched Pokemon in match_cards: {matched_pokemon} \n")
        return matched_pokemon

        
def main(): 
    print("In main card_detector")

if __name__ == "__main__":
    main()

# import supervision as sv
# from PIL import Image
# import numpy as np
# import cv2
# import matplotlib.pyplot as plt
# import matplotlib.pyplot as plt
# import pandas as pd 
# import urllib.request
# from rapidfuzz import fuzz, process
# import re
# import requests

# class CardFinder(): 
    
#     def __init__(self, carddetector):
#         self.carddetector = carddetector


#     def template_match_card(self, entry, template: np.array = None, res: int = -1): 

#         card = cv2.cvtColor(entry["card"], cv2.COLOR_RGB2GRAY)
#         #template = cv2.cvtColor(cv2.imread("./images/meow.jpg"), cv2.COLOR_BGR2GRAY)
#         height_card, width_card = card.shape[:2]
#         artwork_card = card[int(height_card*0.05):int(height_card*0.6), 0:width_card]
#         #template = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
#         height_template, width_template = template.shape[:2]
#         template_artwork = template[int(height_template*0.05):int(height_template*0.6),0:width_template]
#         template_artwork = cv2.resize(template_artwork, (artwork_card.shape[1], artwork_card.shape[0]))
        
#         artwork_card = artwork_card.astype(np.uint8)
#         template_artwork = template_artwork.astype(np.uint8)

#         res_mt = cv2.matchTemplate(artwork_card,template_artwork,cv2.TM_CCOEFF_NORMED)
        
#         print("\n")
#         return card, res_mt

#     def find_best_match_for_pokemon(self, entry, pokemon_images):
#         highest_score = -1
#         best_card = None
#         best_card_url = None
#         template_rgb = None
#         card_id = None

#         for img_data in pokemon_images:
#             img_url = f'{img_data["image"]}/low.jpg'
#             res = urllib.request.urlopen(img_url)
#             arr = np.asarray(bytearray(res.read()), dtype=np.uint8)
#             template_rgb = cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB)
#             template = cv2.cvtColor(template_rgb, cv2.COLOR_RGB2GRAY)

#             # Now check for template match with the current card image
#             result_mt = -1
#             card, result_mt = self.template_match_card(entry, template, result_mt)

#             if result_mt > highest_score:  # if we found a higher match score
#                 highest_score = result_mt
#                 best_card = card
#                 best_card_url = img_url
#                 card_id = img_data["id"]

#         # After all images are checked, return the card with the highest match score
#         return best_card, highest_score, best_card_url, template_rgb, card_id


        
#     def find_cards(self, matched_pokemon):
#         for i, entry in enumerate(matched_pokemon):
#             pokemon = entry["matched_pokemon"]
#             hp = entry["hp"]
#             url = f"https://api.tcgdex.net/v2/en/cards?name={pokemon}&hp={hp}" #TODO /de/ für deutsche Karten
#             response = requests.get(url)
#             response = response.json()

#             best_card, highest_score, best_card_url, template, card_id = self.find_best_match_for_pokemon(entry, response)

#             if best_card is not None:   #best_card is the image taken with a camera
#                 print(f"Best match for {pokemon} (HP {hp}): Score = {highest_score}, Url: {best_card_url}")
#                 entry["best_card_url"] = best_card_url
#                 entry["template_card"] = template
#                 entry["id"] = card_id
                
#                 plt.imshow(template)
          
#             else:
#                 print(f"No match found for {pokemon} (HP {hp})")

#             print("\n")
#         return matched_cards
        
#     def get_pricing(self, matched_pokemon): 
#         for entry in matched_pokemon: 
#             print(entry["id"], "\n \n")
#             url = f"https://api.tcgdex.net/v2/en/cards/{entry['id']}"
#             full_card_response = requests.get(url).json()
#             entry["pricing"] = full_card_response["pricing"]
#             entry["set_info"] = full_card_response["set"]
#             entry["types"] = full_card_response["types"]
#             #Evemtuell variants_detailed für unterscheidung zw. holo und non holo karten -> unterschied im preis
#             print("FULLCARD RESPONSE:", full_card_response)
#         return matched_cards


# carddetector = CardDetector()
# image = Image.open("E:\PythonProjects\pokemon\images\cards3r.jpg")
# detections = carddetector.detect_cards(image)
# snipped_cards = carddetector.snip_cards(image, detections)
# ocr_result_array = carddetector.ocr_on_image(snipped_cards)
# matched_cards = carddetector.match_cards(ocr_result_array)
# ### API Eigene Klasse 
# cardfinder = CardFinder(carddetector=carddetector)
# matched_cards = cardfinder.find_cards(matched_cards)
# matched_cards = cardfinder.get_pricing(matched_cards)


# print(matched_cards)
