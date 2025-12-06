import sqlite3 
import datetime
import os
class PokemonDatabase:

    def __init__(self, db_name='portfolio.db'): 
        self.db_name = db_name
        self.conn = None
        self.cursor = None

        if not os.path.isfile("portfolio.db"): 
            self.create_tables()
            print("Tables created!")


    def create_tables(self):
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_cards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            set_name TEXT NOT NULL,
            set_id TEXT NOT NULL,
            hp INTEGER,
            illustrator TEXT,
            image_url TEXT,
            type TEXT,
            quantity INTEGER DEFAULT 1
        )
        ''')

        # Create the table for card attacks
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            name TEXT NOT NULL,
            cost TEXT NOT NULL,
            effect TEXT,
            damage TEXT,
            FOREIGN KEY (card_id) REFERENCES pokemon_cards (id)
        )
        ''')

        # Create the table for pricing information
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_pricing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            source TEXT NOT NULL,
            avg_price REAL,
            low_price REAL,
            trend REAL,
            updated TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (card_id) REFERENCES pokemon_cards (id)
        )
        ''')

        # Commit changes and close connection
        conn.commit()
        conn.close()


    def insert_card_data(self, matched_cards):
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()

        for card_data in matched_cards:
            card_id = card_data['id']
            # Select to retrieve data from table (pokemon_cards) where id matches (placeholder)
            cursor.execute('''
            SELECT quantity FROM pokemon_cards WHERE id = ?
            ''', (card_id,))
            existing_card = cursor.fetchone()
            
            if existing_card: 
                print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> \n \n", existing_card[0])
                new_quantity = existing_card[0] + 1
                #Update to modify existing entries in Table
                cursor.execute('''
                UPDATE pokemon_cards
                SET quantity = ?
                WHERE id = ?
                ''', (new_quantity, card_id))
                
            else:
                # Insert the Pokémon card details into the pokemon_cards table
                # Insert into Table (pokemon_cards) into columns (id, name) the values (placeholders followed by actual values)
                cursor.execute('''
                INSERT OR REPLACE INTO pokemon_cards (
                    id, name, rarity, set_name, set_id, hp, illustrator, image_url, type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_data['id'], card_data["full_info"]['name'], card_data["full_info"]['rarity'],
                    card_data["full_info"]['set']["name"], card_data["full_info"]["set"]['id'], card_data['hp'],
                    card_data["full_info"]['illustrator'], card_data['template_card'], ', '.join(card_data["full_info"]["types"])
                )) #TODO Check Template_card in database/add actual url instead of array/add base64 string (less memory)

                    # Insert attack data
                for attack in card_data["full_info"]['attacks']:
                    effect = attack.get('effect', None)  # Default to None if 'effect' is missing
                    damage = attack.get('damage', None)  # Default to None if 'damage' is missing
                    cursor.execute('''
                    INSERT OR REPLACE INTO pokemon_attacks (card_id, name, cost, effect, damage)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        card_data['id'], attack['name'], ', '.join(attack['cost']),
                        effect, damage
                    ))
#TODO only get cardmarket data except when theres only tcg data
                # Insert pricing data
            for source, pricing_info in card_data["full_info"]['pricing'].items():
                if pricing_info:
                    cursor.execute('''
                    INSERT INTO pokemon_pricing (card_id, source, avg_price, low_price, trend, updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        card_data['id'], source, pricing_info.get('avg', None),
                        pricing_info.get('low', None), pricing_info.get('trend', None),
                        f"_{datetime.datetime.now()}" #pricing_info.get('updated', None)
                    ))

        # Commit changes and close connection
        conn.commit()
        conn.close()

# card_data = {
#     'category': 'Pokemon',
#     'id': 'sv02-242',
#     'illustrator': 'PLANETA Hiiragi',
#     'image': 'https://assets.tcgdex.net/en/sv/sv02/242',
#     'localId': '242',
#     'name': 'Annihilape ex',
#     'rarity': 'Ultra Rare',
#     'set': {
#         'cardCount': {'official': 193, 'total': 279},
#         'id': 'sv02',
#         'logo': 'https://assets.tcgdex.net/en/sv/sv02/logo',
#         'name': 'Paldea Evolved',
#         'symbol': 'https://assets.tcgdex.net/univ/sv/sv02/symbol'
#     },
#     'variants': {'firstEdition': False, 'holo': True, 'normal': False, 'reverse': False, 'wPromo': False},
#     'variants_detailed': [{'type': 'holo', 'size': 'standard'}],
#     'dexId': [979],
#     'hp': 320,
#     'types': ['Fighting'],
#     'stage': 'Stage2',
#     'attacks': [
#         {'cost': ['Fighting'], 'name': 'Angry Grudge', 'effect': 'Put up to 12 damage counters on this Pokémon. This attack does 20 damage for each damage counter you placed in this way.', 'damage': '20×'},
#         {'cost': ['Fighting', 'Colorless'], 'name': 'Seismic Toss', 'damage': 150}
#     ],
#     'retreat': 2,
#     'regulationMark': 'G',
#     'legal': {'standard': True, 'expanded': True},
#     'updated': '2025-08-16T20:39:55Z',
#     'pricing': {
#         'cardmarket': {'updated': '2025-11-14T01:47:56.000Z', 'unit': 'EUR', 'avg': 2.76, 'low': 0.05, 'trend': 2.9},
#         'tcgplayer': None
#     }
# }