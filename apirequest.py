import requests
import os
import roboflow
from pprint import pprint
# API endpoint
url = "https://api.tcgdex.net/v2/en/cards?name=meganium"

url = f"https://api.tcgdex.net/v2/de/cards?name=rufklingel"

# Fetch JSON data
response = requests.get(url)
response.raise_for_status()
data = response.json()

pprint(data)
