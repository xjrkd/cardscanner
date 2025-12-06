import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
st.set_page_config(page_title="Portfolio", page_icon="📈")

st.sidebar.header("Portfolio")
st.markdown("# Portfolio")

def query_db() -> list: 
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()



    ###
    #     How This Query Works:
    # Common Table Expression (CTE): The WITH LatestPricing AS (...) block creates a temporary result set.
    # ROW_NUMBER(): This function is used to assign a unique rank to each row within a partition of a result set.[1][2]
    # PARTITION BY card_id: This divides the rows into groups based on the card_id. The row numbering will restart for each new card_id.[3][4]
    # ORDER BY created_at DESC: Within each group of card_ids, the rows are ordered by the created_at timestamp in descending order. This ensures that the most recent pricing entry gets the row number 1. Note: You should replace created_at with the actual name of the timestamp column in your pokemon_pricing table.
    # Final SELECT Statement:
    # We then select the necessary columns from your pokemon_cards table.
    # We JOIN this with our LatestPricing CTE on the card ID.
    # The WHERE lp.rn = 1 clause filters the results to only include the rows where the rank is 1, which corresponds to the latest pricing entry for each card.
     ###
    cursor.execute("""WITH LatestPricing AS (
    SELECT
        card_id,
        avg_price,
        -- This window function assigns a row number to each card's pricing history,
        -- with 1 being the most recent.
        ROW_NUMBER() OVER(PARTITION BY card_id ORDER BY updated DESC) as rn
    FROM
        pokemon_pricing
)
        SELECT
            pc.id,
            pc.name,
            pc.quantity,
            lp.avg_price
        FROM
            pokemon_cards pc
        JOIN
            LatestPricing lp ON pc.id = lp.card_id
        WHERE
            lp.rn = 1;
    """)
    #print(cursor)

    return cursor.fetchall()


def get_all_prices(cursor: list): 
    portfolio_value = 0
    missing_values = 0
    total_cards_quantity = 0
    for row in cursor: 
        quantity = row[2]
        price = row[3]
        total_cards_quantity+=quantity
        if price is not None: 
            portfolio_value+= quantity*price
        else: 
            missing_values+=1
    st.write(f"Current Value: {portfolio_value}, missing price for {missing_values} cards. Total cards: {total_cards_quantity}")


def generate_pie_chart(cursor: list): 
    #print(cursor)
    sorted_by_quantity = sorted(cursor, key=lambda tup: tup[2], reverse=True)
    print("Sorted by quantity",sorted_by_quantity)
    total_cards = 0
    total_cards = sum(entry[2] for entry in sorted_by_quantity)

    card_quantity = []
    labels = []
    for entry in sorted_by_quantity: 
        if entry[2]/total_cards>0.02: 
            card_quantity.append(entry[2])
            labels.append(f"{entry[1]},_{entry[0]}")
    
    fig, ax = plt.subplots()
    ax.pie(card_quantity, labels=labels, autopct='%1.1f%%', startangle=90)
    st.pyplot(fig)
    print(total_cards)

        
def generate_price_history(cursor: list): 
    pass


cursor = query_db()
get_all_prices(cursor)
generate_pie_chart(cursor) 