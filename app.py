import streamlit as st
import json
import google.generativeai as genai
import os
import random
from dotenv import load_dotenv
import re  # We'll need this for parsing Gemini's JSON output

# --- Load environment variables from .env file ---
load_dotenv()

# --- 1. Google Gemini API Configuration ---
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(layout="wide", page_title="AI Style Advisor")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("Error: Google Gemini API key not configured.")
    st.warning("Ensure you have a `.env` file in the project root with `GOOGLE_API_KEY=YOUR_GEMINI_API_KEY`.")
    st.stop()

model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. Loading Product Data ---
DATA_FILE = 'fashion_products_tagged.json'  # Loading the tagged file
products_data = []
try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        products_data = json.load(f)
except FileNotFoundError:
    st.error(f"Error: Data file '{DATA_FILE}' not found. Please run `generate_tags_with_gemini.py` first.")
    st.stop()
except json.JSONDecodeError:
    st.error(f"Error: Failed to load '{DATA_FILE}'. Check if it's a valid JSON.")
    st.stop()


# --- 3. Helper function for finding products (now using generated tags) ---
def find_products_by_criteria(criteria, num_results=20):
    """
    Finds a pool of potential products based on criteria, leveraging occasion_tags and style_tags.
    Returns a shuffled list of products.
    """
    found_products = []
    for product in products_data:
        match = True

        # Filter by gender
        if 'gender' in criteria and criteria['gender'] and criteria['gender'].lower() != 'any' and product[
            'gender'].lower() != criteria['gender'].lower():
            match = False

        # Filter by category (if not 'Full outfit' or 'Any')
        if 'category' in criteria and criteria['category'] and criteria['category'].lower() != 'any' and criteria[
            'category'].lower() != 'full outfit':
            if product['category'].lower() != criteria['category'].lower():
                match = False

        # Filter by price (max_price for individual items)
        if 'max_price' in criteria and product['price'] > criteria['max_price']:
            match = False

        # Filter by color (simple text match)
        if 'color' in criteria and criteria['color'] and criteria['color'].lower() != 'any':
            if criteria['color'].lower() not in product['color'].lower():
                match = False

        # Filter by occasion tags (now using the generated tags!)
        if 'occasion_tags' in criteria and criteria['occasion_tags']:
            if not any(tag.lower() in [ot.lower() for ot in product.get('occasion_tags', [])] for tag in
                       criteria['occasion_tags']):
                match = False

        # Filter by style tags (now using the generated tags!)
        if 'style_tags' in criteria and criteria['style_tags']:
            if not any(tag.lower() in [st.lower() for st in product.get('style_tags', [])] for tag in
                       criteria['style_tags']):
                match = False

        if match:
            found_products.append(product)

    # Shuffle and return a limited number of results to pass to Gemini
    random.shuffle(found_products)
    return found_products[:min(len(found_products), num_results)]


# --- 4. Streamlit Interface ---

st.title("👗 AI Style Advisor")
st.markdown("Your personal fashion assistant. Tell me what you need, and I'll find the perfect outfit!")

col1, col2 = st.columns(2)

with col1:
    st.header("Tell me about your needs")
    user_occasion = st.text_input("What's the occasion?", "")
    user_style = st.text_input("What style do you prefer?", "")
    user_budget = st.slider("What's your budget (PLN)?", 50, 2000, 500)

    gender_options = ['Any'] + sorted(
        list(set([p['gender'] for p in products_data if p['gender'] != 'unspecified gender'])))
    user_gender = st.selectbox("For whom?", gender_options)

    category_options = ['Full outfit', 'Any'] + sorted(
        list(set([p['category'] for p in products_data if p['category'] != 'unspecified category'])))
    user_category = st.selectbox("What type of clothing are you looking for?", category_options)

with col2:
    st.header("Additional preferences")
    user_color = st.text_input("Preferred color?", "")
    user_keywords = st.text_area("Other keywords / details?", "")

    all_occasion_tags = sorted(
        list(set([tag for p in products_data for tag in p.get('occasion_tags', []) if p.get('occasion_tags')])))
    selected_occasion_tags = st.multiselect("Filter by occasion tags:", all_occasion_tags)

    all_style_tags = sorted(
        list(set([tag for p in products_data for tag in p.get('style_tags', []) if p.get('style_tags')])))
    selected_style_tags = st.multiselect("Filter by style tags:", all_style_tags)

if st.button("Find me an outfit!"):
    with st.spinner("AI is analyzing your preferences and searching for the ideal styling..."):

        # --- Krok 1: Wstępne wyszukiwanie produktów (Retrieval) ---
        # Znajdź pulę potencjalnych produktów z naszej bazy, które pasują do ogólnych kryteriów
        retrieval_criteria = {
            'gender': user_gender if user_gender != 'Any' else None,
            'max_price': user_budget,  # Początkowo limit na pojedynczy produkt, Gemini skoryguje to dla Full outfit
            'category': user_category if user_category != 'Full outfit' and user_category != 'Any' else None,
            'color': user_color if user_color else None,
            'occasion_tags': selected_occasion_tags,
            'style_tags': selected_style_tags
        }

        potential_products = find_products_by_criteria(retrieval_criteria,
                                                       num_results=30)  # Pobierz np. 30 potencjalnych produktów

        if not potential_products:
            st.warning(
                "No potential products found in our database matching your initial criteria. Try broadening your search.")
            st.stop()

        # Sformatuj potencjalne produkty do przekazania Gemini jako kontekst
        products_context = ""
        for i, prod in enumerate(potential_products):
            products_context += f"""
            Product {i + 1}:
            - Name: {prod['product_name']}
            - Description: {prod['description']}
            - Category: {prod['category']}
            - Subcategory: {prod['sub_category']}
            - Color: {prod['color']}
            - Brand: {prod['brand']}
            - Price: {prod['price']} {prod['currency']}
            - Image URL: {prod['image_url']}
            - Purchase Link: {prod['purchase_link']}
            - Occasion Tags: {', '.join(prod.get('occasion_tags', []))}
            - Style Tags: {', '.join(prod.get('style_tags', []))}
            """

        # --- Krok 2: Ulepszony Prompt dla Gemini (Augmented Generation + Structured Output) ---
        budget_instruction = ""
        if user_category == "Full outfit":
            budget_instruction = f"The suggested products should form a complete outfit, and their TOTAL price MUST NOT EXCEED {user_budget} PLN. Select 3-5 distinct products."
        else:
            budget_instruction = f"The approximate price of each suggested product should be within the budget of up to {user_budget} PLN. Select 1 specific product matching the category '{user_category}'."

        prompt = f"""
        You are an advanced AI Style Advisor. Your task is to propose personalized stylings based on user preferences and a provided list of available products.
        Your response must be creative, practical, and entirely in English.

        **User Preferences:**
        - Occasion: {user_occasion}
        - Style: {user_style}
        - Budget: Up to {user_budget} PLN
        - Gender: {user_gender}
        - Clothing Type/Outfit Type: {user_category}
        - Color: {user_color}
        - Additional Keywords: {user_keywords}
        - Preferred Occasion Tags: {', '.join(selected_occasion_tags) if selected_occasion_tags else 'none'}
        - Preferred Style Tags: {', '.join(selected_style_tags) if selected_style_tags else 'none'}

        **Available Products (Choose ONLY from this list to suggest to the user):**
        {products_context}

        **Instructions for You (Gemini):**
        1.  Based on the **User Preferences** and the **Available Products** list, propose a complete styling.
        2.  Describe why you chose this styling and what elements it consists of.
        3.  **Crucially, select 3-5 specific products from the "Available Products" list (or 1 product if "Clothing Type" is specific).**
        4.  For "Full outfit", ensure the total price of selected products does not exceed the user's budget.
        5.  For each selected product, provide its exact details **as they appear in the "Available Products" list (especially 'Name', 'Image URL', 'Purchase Link', 'Price')**.

        **Response Format (very important - MUST be a valid JSON object):**
        ```json
        {{
          "overall_styling_proposal": "[Here, the styling description]",
          "suggested_products": [
            {{
              "name": "[Product Name 1, EXACTLY from available products]",
              "description": "[Brief description, you can generate this or use from available products]",
              "color": "[Color, EXACTLY from available products]",
              "category": "[Category, EXACTLY from available products]",
              "price": [Price in PLN, EXACTLY from available products],
              "image_url": "[Image URL, EXACTLY from available products]",
              "purchase_link": "[Purchase Link, EXACTLY from available products]"
            }},
            {{
              "name": "[Product Name 2, EXACTLY from available products]",
              "description": "[Brief description, you can generate this or use from available products]",
              "color": "[Color, EXACTLY from available products]",
              "category": "[Category, EXACTLY from available products]",
              "price": [Price in PLN, EXACTLY from available products],
              "image_url": "[Image URL, EXACTLY from available products]",
              "purchase_link": "[Purchase Link, EXACTLY from available products]"
            }}
            // ... up to 5 products
          ]
        }}
        ```
        Ensure the JSON is valid and only includes products from the provided "Available Products" list.
        """

        try:
            response = model.generate_content(prompt)
            ai_raw_response = response.text

            # --- Krok 3: Parsowanie Structured Output z Gemini ---
            json_match = re.search(r'```json\n({.*?})\n```', ai_raw_response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                parsed_data = json.loads(json_str)

                overall_styling_proposal = parsed_data.get("overall_styling_proposal", "No styling proposal provided.")
                suggested_products_from_ai = parsed_data.get("suggested_products", [])

                st.subheader("Proposal from Your AI Style Advisor:")
                st.markdown(overall_styling_proposal)

                st.subheader("Selected products from our database:")

                total_cost_ai_suggested = 0.0
                display_products = []

                # Verify if the products suggested by AI actually exist in our pool (safety check)
                # and collect their details including image_url and purchase_link
                for ai_prod in suggested_products_from_ai:
                    found_in_db = next((p for p in potential_products if
                                        p['product_name'] == ai_prod['name'] and p['category'] == ai_prod['category']),
                                       None)
                    if found_in_db:
                        # Use details from our database for safety/consistency
                        display_products.append(found_in_db)
                        total_cost_ai_suggested += found_in_db['price']
                    else:
                        st.warning(
                            f"AI suggested product '{ai_prod['name']}' not found in the initial pool. This might indicate an issue with AI's adherence to instructions.")

                if user_category == "Full outfit" and display_products:
                    st.success(
                        f"Total cost of AI suggested products: {total_cost_ai_suggested:.2f} {products_data[0]['currency']}")
                    if total_cost_ai_suggested > user_budget:
                        st.warning(
                            f"Warning: The total cost of the AI-suggested outfit ({total_cost_ai_suggested:.2f} PLN) exceeds your budget of {user_budget} PLN.")

                if display_products:
                    for product in display_products:
                        st.write(f"**{product['product_name']}**")
                        st.image(product['image_url'], caption=product['product_name'], width=200)
                        st.write(
                            f"Category: {product['category']}, Color: {product['color']}")
                        st.write(f"Price: {product['price']} {product['currency']}")
                        st.markdown(f"**[Buy now]({product['purchase_link']})**")
                        st.markdown("---")
                else:
                    st.info(
                        "AI could not suggest specific products from the available pool for your criteria. Try changing your query or broadening the search.")

            else:
                st.error("AI did not return the response in the expected JSON format. Raw response from AI:")
                st.markdown(f"```\n{ai_raw_response}\n```")


        except Exception as e:
            st.error(f"An error occurred during communication with Gemini API or processing: {e}")
            st.error("Please ensure your API key is correct and you have an internet connection.")