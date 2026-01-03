import sqlite3 
import datetime
import os
import requests

class PokemonDatabase:

    def __init__(self, db_name:str = 'portfolio.db', language: str = "de"): 
        self.db_name = db_name
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.language = language


    def create_tables(self):
        '''
        Initializes the DB tables.
        '''
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_cards (
            card_id TEXT PRIMARY KEY,
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
            cost TEXT,
            effect TEXT,
            damage TEXT,
            FOREIGN KEY (card_id) REFERENCES pokemon_cards (id)
        )
        ''')

        # Create the table for pricing information
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_pricing (
            card_id TEXT PRIMARY KEY NOT NULL,
            source TEXT NOT NULL,
            avg_price REAL,
            low_price REAL,
            trend REAL,
            updated TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (card_id) REFERENCES pokemon_cards (id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_value (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       timestamp DATETIME NOT NULL,
                       total_value REAL NOT NULL,
                       total_cards INTEGER,
                       total_unique_cards INTEGER)
        ''')


        cursor.execute('''CREATE TABLE IF NOT EXISTS set_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        set_id TEXT NOT NULL,
                        set_name TEXT NOT NULL, 
                        card_id TEXT NOT NULL,
                        card_name TEXT NOT NULL,
                        image_url TEXT,
                        UNIQUE(set_id, card_id))        --prevents duplicates
                       ''')
        # Commit changes and close connection
        conn.commit()
        conn.close()


    def insert_card_data(self, matched_cards:list, db_name: str):
        '''
        Populates the DBs with information from a list (matched_cards).
        :param self: 
        :param matched_cards: Description
        '''
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        for card_data in matched_cards:
            card_id = card_data['id']
            # Select to retrieve data from table (pokemon_cards) where id matches (placeholder)
            cursor.execute('''
            SELECT quantity FROM pokemon_cards WHERE card_id = ?
            ''', (card_id,))
            existing_card = cursor.fetchone()
            
            if existing_card: 
                new_quantity = existing_card[0] + 1
                #Update to modify existing entries in Table
                cursor.execute('''
                UPDATE pokemon_cards
                SET quantity = ?
                WHERE card_id = ?
                ''', (new_quantity, card_id))
                
            else:
                # Insert the Pokémon card details into the pokemon_cards table
                # Insert into Table (pokemon_cards) into columns (id, name) the values (placeholders followed by actual values)
                cursor.execute('''
                INSERT OR REPLACE INTO pokemon_cards (
                    card_id, name, rarity, set_name, set_id, hp, illustrator, image_url, type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_data['id'], card_data["full_info"]['name'], card_data["full_info"]['rarity'],
                    card_data["full_info"]['set']["name"], card_data["full_info"]["set"]['id'], card_data['hp'],
                    card_data["full_info"]['illustrator'], card_data['best_card_url'], ', '.join(card_data["full_info"]["types"])
                )) 

                    # Insert attack data
                for attack in card_data["full_info"]['attacks']:
                    effect = attack.get('effect', None)  # Default to None if missing
                    damage = attack.get('damage', None)  
                    cost = attack.get('cost', None)
                    cursor.execute('''
                    INSERT OR REPLACE INTO pokemon_attacks (card_id, name, cost, effect, damage)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        card_data['id'], attack['name'], 
                        cost if cost is None else ', '.join(cost),
                        effect, damage
                    ))

                # Insert pricing data
            pricing = card_data["full_info"]['pricing']
            if pricing.get("cardmarket"):
                source = "cardmarket"
                pricing_info = pricing["cardmarket"]
            else: 
                source = "tcgplayer"
                pricing_info = pricing["tcgplayer"]
            
            if pricing_info is None: 
                pricing_info = {}
            
            cursor.execute('''
            INSERT INTO pokemon_pricing (card_id, source, avg_price, low_price, trend, updated) 
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET
            avg_price = excluded.avg_price,
            low_price = excluded.low_price,
            trend = excluded.trend,
            updated = excluded.updated
            ''', (
                card_data['id'], source, pricing_info.get('avg1', None),
                pricing_info.get('low', None), pricing_info.get('trend', None),
                f"{datetime.datetime.now().replace(second=0, microsecond=0)}" #pricing_info.get('updated', None)
            ))

            response = requests.get(f'https://api.tcgdex.net/v2/{self.language}/sets/{card_data["full_info"]["set"]["id"]}').json()
            for entry in response["cards"]: 
                try: 
                    image = f"{entry['image']}/low.jpg"
                except KeyError: 
                    image = None
                cursor.execute('''
                                INSERT OR IGNORE INTO set_info (set_id, set_name, card_id, card_name, image_url)
                                VALUES (?,?,?,?,?)
                                ''', (card_data["full_info"]["set"]["id"], card_data["full_info"]['set']["name"], 
                                    entry["id"], entry["name"], image 
                ))


        # Commit changes and close connection
        conn.commit()
        conn.close()
        self.fill_portfolio_values() #Update Portfolio as last step

    def fill_portfolio_values(self): 
        '''
        Populates the portfolio_value table with columns timestamp, total_value, total_cards, total_unique_cards.
        By iterating through the pokemon_cards table. 
        :param self: 
        '''
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT card_id, quantity FROM pokemon_cards")
        cards = cursor.fetchall()

        full_portfolio_value = 0
        total_cards = 0
        unique_cards = 0
        for card_id, quantity in cards: 
            response = requests.get(f"https://api.tcgdex.net/v2/{self.language}/cards/{card_id}").json()
            unique_cards+=1
            total_cards+=quantity
            pricing = response.get("pricing", {})
            cardmarket = pricing.get("cardmarket")
            
            if cardmarket is None:   
                cardmarket = pricing.get("tcgplayer")  # no price, try other marketplcae else skip value calculation
            try:
                avg_price = cardmarket.get("avg1")
            except: 
                continue
            if avg_price is None:
                continue

            full_portfolio_value += quantity * avg_price
        
        cursor.execute('''
                    INSERT INTO portfolio_value (timestamp, total_value, total_cards, total_unique_cards)  
                       VALUES (?,?,?,?) 
                    ''',(
                        datetime.datetime.now().replace(second=0, microsecond=0), round(full_portfolio_value,2), total_cards, unique_cards 
                    ))
        conn.commit()
        conn.close()
        print("Portfolio values updated")

