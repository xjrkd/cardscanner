import streamlit as st 
from database import PokemonDatabase
import sqlite3
import pandas as pd
import datetime

st.set_page_config(
    page_title="Inventory Manager",
    page_icon="",
)
st.sidebar.header("Inventory Manager")
st.markdown("# Inventory Manager")
st.write(
    """Remove cards from your inventory"""
)

st.write("Using database:", st.session_state.database.db_name)

TABLES_WITH_CARD_ID = [
    "pokemon_cards",
    "pokemon_attacks",
    "pokemon_pricing",
    "set_info",
]

def get_all_card_ids()-> list:
    """Fetches a sorted list of unique card_ids from the pokemon_cards table."""
    try:
        conn = sqlite3.connect(f"{st.session_state.database.db_name}")
        c = conn.cursor()
        c.execute("SELECT DISTINCT card_id, name, image_url, quantity FROM pokemon_cards ORDER BY card_id ASC;")
        columns = [desc[0] for desc in c.description]
        columns.append("Remove Amount")

        data = [dict(zip(columns, row + (0,))) for row in c.fetchall()]
        conn.close()
        return data
    except sqlite3.OperationalError as e:
        st.error(f"Database error: {e}. Make sure the database file and 'pokemon_cards' table exist.")
        return []
    


def process_inventory_removals(df_changes: pd.DataFrame):
    """
    Takes a dataframe of changes, updates quantities for partial removals,
    and deletes rows where quantity becomes 0.
    """
    st.write(df_changes)
    if df_changes.empty:
        return

    conn = sqlite3.connect(f"{st.session_state.database.db_name}")
    c = conn.cursor()

    # Lists to batch operations
    ids_to_full_delete = []
    partial_updates = [] # Will store tuples: (new_quantity, card_id)

    try:
       # Sort the data into "Updates" vs "Full Deletes"
        for index, row in df_changes.iterrows():
            card_id = row['card_id']
            current_qty = row['quantity']
            remove_amt = row['Remove Amount']
            
            new_qty = int(current_qty - remove_amt)

            query_pricing = """
                DELETE FROM pokemon_pricing 
                WHERE id IN (
                    SELECT id FROM pokemon_pricing 
                    WHERE card_id = ? 
                    ORDER BY updated ASC 
                    LIMIT ?
                )
            """
            c.execute(query_pricing, (card_id, remove_amt)) # Delete "remove_amt" entries from pokemon_pricing table, oldest first

            if new_qty == 0:
                # If quantity hits 0, add ID to the list for full deletion
                ids_to_full_delete.append(str(card_id))
            else:
                # Otherwise, prepare an SQL update to reduce quantity
                partial_updates.append((new_qty, card_id))

        # Execute Partial Updates (Reduce Quantity)
        if partial_updates:
            c.executemany("UPDATE pokemon_cards SET quantity = ? WHERE card_id = ?", partial_updates)
            st.info(f"Updated quantities for {len(partial_updates)} cards.")

        # Execute Full Deletes
        if ids_to_full_delete:
            placeholders = ', '.join(['?'] * len(ids_to_full_delete))
            
            # Delete from all related tables
            for table in TABLES_WITH_CARD_ID:
                query = f"DELETE FROM {table} WHERE card_id IN ({placeholders});"
                c.execute(query, ids_to_full_delete)
            
            st.warning(f"Fully deleted {len(ids_to_full_delete)} cards (quantity reached 0).")

        conn.commit()
        st.success("Inventory changes saved successfully!")

    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"An error occurred: {e}")
    finally:
        conn.close()

def update_portfolio_value(): 
    '''
    Calculates the current total value of the portfolio and records a historical snapshot.

    This function performs the following steps:
    1. Fetches all cards from the inventory (`pokemon_cards`) linked with their 
       most recent average price from the pricing history (`pokemon_pricing`).
    2. Aggregates the data to determine:
       - Total Monetary Value (Sum of Quantity * Avg Price).
       - Total Card Count (Sum of Quantities).
       - Total Unique Cards (Count of distinct Card IDs).
    3. Inserts a new timestamped row into the `portfolio_value` table with these statistics.
    '''

    conn = sqlite3.connect(f"{st.session_state.database.db_name}")
    c = conn.cursor()
    c.execute('''SELECT 
    c.card_id, 
    c.quantity, 
    p.avg_price
    FROM pokemon_cards c
    LEFT JOIN (
        -- Subquery to get only the LATEST price row for each card
        SELECT card_id, avg_price
        FROM pokemon_pricing p1
        WHERE updated = (
            SELECT MAX(updated) 
            FROM pokemon_pricing p2 
            WHERE p2.card_id = p1.card_id
        )
    ) p ON c.card_id = p.card_id;''')
    data = c.fetchall() 
    
   
    total_value = 0.0
    total_cards = 0
    total_unique_cards = len(data) # The number of rows equals unique cards
    
    for row in data:
        qty = row[1]
        price = row[2] if row[2] is not None else 0.0 
        
        total_value += (qty * price)
        total_cards += qty

    total_value = round(total_value, 2)

    current_time = datetime.datetime.now().replace(second=0, microsecond=0)

    # Insert the SINGLE new row into the history table
    try:
        c.execute("""
            INSERT INTO portfolio_value (timestamp, total_value, total_cards, total_unique_cards)
            VALUES (?, ?, ?, ?)
        """, (current_time, total_value, total_cards, total_unique_cards))
        
        conn.commit()
        st.success(f"Portfolio updated: {total_cards} cards worth {total_value} €")
        
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"Error updating portfolio value: {e}")
    finally:
        conn.close()
  

all_card_ids = get_all_card_ids()

df = pd.DataFrame(all_card_ids)
data_edit =  st.data_editor(df, disabled=["quantity", "name","card_id", "Image"], column_config={"image_url": st._column_config.ImageColumn("Image")})


if st.button(label="Delete selected Cards", type="primary"): 
        changes = data_edit.copy()
        #compare the two columns and take the minimum value row-by-row
        changes['Remove Amount'] = changes[['Remove Amount', 'quantity']].min(axis=1)

        # Filter: Get only rows where Remove Amount > 0
        changes = changes[changes['Remove Amount'] > 0]
        process_inventory_removals(changes)
        update_portfolio_value()

