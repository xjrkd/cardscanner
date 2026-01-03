from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import urllib.request
import requests

class CardFinder(): 
    
    def __init__(self, carddetector, language):
        self.carddetector = carddetector
        self.flag_url_missing = False
        self.language = language 

    def template_match_card(self, entry, template: np.array = None, res: int = -1): 
        '''
        Matches a detected and cropped card against a template from the api.
        '''
        
        card = cv2.cvtColor(entry["card"], cv2.COLOR_RGB2GRAY)
        #template = cv2.cvtColor(cv2.imread("./images/meow.jpg"), cv2.COLOR_BGR2GRAY)
        height_card, width_card = card.shape[:2]
        artwork_card = card[int(height_card*0.05):int(height_card*0.6), 0:width_card]
        #template = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
        height_template, width_template = template.shape[:2]
        template_artwork = template[int(height_template*0.05):int(height_template*0.6),0:width_template]
        template_artwork = cv2.resize(template_artwork, (artwork_card.shape[1], artwork_card.shape[0]))
        
        artwork_card = artwork_card.astype(np.uint8)
        template_artwork = template_artwork.astype(np.uint8)

        res_mt = cv2.matchTemplate(artwork_card,template_artwork,cv2.TM_CCOEFF_NORMED)


        ## FULL CARD MATCH
        # card = cv2.cvtColor(entry["card"], cv2.COLOR_RGB2GRAY)
        # height_card, width_card = card.shape[:2]
        # artwork_card = card[0:height_card, 0:width_card]

        # height_template, width_template = template.shape[:2]

        # # Use full height for template
        # template_artwork = template[0:height_template, 0:width_template]

        # # Resize template to match the size of the card's artwork
        # template_artwork = cv2.resize(template_artwork, (artwork_card.shape[1], artwork_card.shape[0]))

        # artwork_card = artwork_card.astype(np.uint8)
        # template_artwork = template_artwork.astype(np.uint8)

        # ## Perform template matching
        # res_mt = cv2.matchTemplate(artwork_card, template_artwork, cv2.TM_CCOEFF_NORMED)
        
        print("\n")
        return card, res_mt

    def find_best_match_for_pokemon(self, entry, pokemon_images):
        '''
        Iterates over all images returned from an api call in another function.
        Calls template_match_card and updates best score. 
        Returns best_card, highest_score, best_card_url, template_rgb, card_id
        '''
        highest_score = -1
        best_card = None
        best_card_url = None
        template_rgb = None
        card_id = None
        best_template = None

        for img_data in pokemon_images:
            if not img_data.get("image"): 
                continue
            img_url = f'{img_data["image"]}/low.jpg'
            try: 
                res = urllib.request.urlopen(img_url)
                arr = np.asarray(bytearray(res.read()), dtype=np.uint8)
            except:  #If /low.jpg does not work
                img_url = f'{img_data["image"]}/high.jpg'
                res = urllib.request.urlopen(img_url)
                arr = np.asarray(bytearray(res.read()), dtype=np.uint8)
            template_rgb = cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB)
            template = cv2.cvtColor(template_rgb, cv2.COLOR_RGB2GRAY)

            # Now check for template match with the current card image
            result_mt = -1
            card, result_mt = self.template_match_card(entry, template, result_mt)

            print(f"Url: {img_url}, score: {result_mt}")

            if result_mt > highest_score:  # if we found a higher match score
                highest_score = result_mt
                best_card = card
                best_card_url = img_url
                card_id = img_data["id"]
                best_template = template_rgb            #FIXED the issue of having a missmatch between matched_cards json and actual image, as it was always overwritten by the last downloaded image instead of best template

        # After all images are checked, return the card with the highest match score
        return best_card, highest_score, best_card_url, best_template, card_id

    def find_cards(self, matched_pokemon):
        '''
        Iterates over all pokemon names detected by ocr. 
        Calls the api with pokemon name and hp. 
        Updates list with template and image url.
        '''
        for i, entry in enumerate(matched_pokemon):
            pokemon = entry["matched_pokemon"]
            hp = entry["hp"]
            if hp:
                url = f"https://api.tcgdex.net/v2/{self.language}/cards?name={pokemon}&hp={hp}" #TODO /de/ für deutsche Karten
            else:
                print("Find Card, resorting to just pokemon, no hp \n \n")
                url = f"https://api.tcgdex.net/v2/{self.language}/cards?name={pokemon}"
            
            try:
                response = requests.get(url)
                response = response.json()
            except requests.exceptions.RequestException as e: 
                print("Request Error: ", e)

            flag_url_missing = any("image" not in response_card for response_card in response)
            print(f"\n \n FIND POKEMON {pokemon} \n RESPONSE: {response} \n \n")
            best_card, highest_score, best_card_url, template, card_id = self.find_best_match_for_pokemon(entry, response)

            if best_card is not None: 
                print(f"Best match for {pokemon} (HP {hp}): Score = {highest_score}, Url: {best_card_url}")
                entry["best_card_url"] = best_card_url
                entry["template_card"] = template
                entry["id"] = card_id
                entry["missing_url"] = flag_url_missing
                
                plt.imshow(template)
          
            else:
                print(f"No match found for {pokemon} (HP {hp})")

            print("\n")
        return matched_pokemon
        
    def get_pricing(self, matched_pokemon): 
        '''
        Updates pokemon list with pricing information.
        '''
        for entry in matched_pokemon: 
            url = f"https://api.tcgdex.net/v2/{self.language}/cards/{entry['id']}"
            full_card_response = requests.get(url).json()
            entry["full_info"] = full_card_response
            #print("\n \n----------------------------------FULLCARDRESPONSE:",full_card_response)
        return matched_pokemon