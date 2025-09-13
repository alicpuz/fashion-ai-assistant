import google.generativeai as genai
import json
import os
import time
from dotenv import load_dotenv
import re

# --- Load environment variables from .env file ---
load_dotenv()

# --- 1. Google Gemini API Configuration ---
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    print("Error: Google Gemini API key not configured.")
    print("Ensure you have a `.env` file in the project root with `GOOGLE_API_KEY=YOUR_GEMINI_API_KEY`.")
    exit()

# Initialize Gemini model
# We are sticking with gemini-2.5-flash as it's the only available model.
model = genai.GenerativeModel('gemini-2.5-flash')

# --- File Paths ---
INPUT_JSON_FILE = 'fashion_products.json'  # Load the filtered file
OUTPUT_JSON_FILE_TAGGED = 'fashion_products_tagged.json'  # Save new file with tags

# --- Processing Parameters ---
# DAILY LIMIT: 250 requests.
# PER-MINUTE LIMIT: 10 requests.

MAX_PRODUCTS_TO_PROCESS = 240  # Set to slightly less than daily limit to be safe.
BATCH_SIZE = 5  # Process very small batches to avoid hitting per-minute limit.
DELAY_BETWEEN_BATCHES = 30  # Wait 30 seconds after each batch of 5 products.


def generate_tags_for_product(product_info):
    """
    Creates a prompt for Gemini and extracts style and occasion tags.
    """
    prompt = f"""
    Based on the following product description, generate a list of style tags and a list of occasion tags.
    Tags should be relevant, concise (one or two words), and represent the character of the product.
    Use English language.

    **Product Description:**
    Name: {product_info['product_name']}
    Category: {product_info['category']} ({product_info['sub_category']})
    Gender: {product_info['gender']}
    Color: {product_info['color']}
    Usage Type: {product_info['usage_type']}
    Full description: {product_info['description']}

    **Instructions for Tags:**
    - Style Tags: Describe the aesthetic, e.g., elegant, casual, boho, minimalist, streetwear, sporty, retro, glamorous, classic, modern.
    - Occasion Tags: Describe for which events the product is suitable, e.g., date night, office, party, beach, travel, everyday, wedding, formal, casual.
    - Each list should contain between 2 and 5 tags.

    **Response Format (JSON):**
    ```json
    {{
      "occasion_tags": ["tag1", "tag2"],
      "style_tags": ["tag1", "tag2"]
    }}
    ```
    """

    try:
        response = model.generate_content(prompt)
        text_response = response.text

        json_match = re.search(r'```json\n({.*?})\n```', text_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            parsed_data = json.loads(json_str)
            return parsed_data.get('occasion_tags', []), parsed_data.get('style_tags', [])
        else:
            print(
                f"Warning: Failed to parse JSON from Gemini's response for product: {product_info['product_name']}. Response: {text_response[:100]}...")
            return [], []
    except Exception as e:
        print(f"Gemini API Error for product '{product_info['product_name']}': {e}")
        return [], []


def process_products_for_tags(input_file, output_file, max_products_to_process, batch_size, delay):
    """
    Loads products, generates tags using Gemini, and saves updated products.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            products = json.load(f)

        print(f"Loaded {len(products)} products from '{input_file}'.")

        products_to_process = products[:min(len(products), max_products_to_process)]
        print(f"Processing a maximum of {len(products_to_process)} products for tags.")

        updated_products = []
        for i, product in enumerate(products_to_process):
            print(f"Processing product {i + 1}/{len(products_to_process)}: {product['product_name']}")

            occasion_tags, style_tags = generate_tags_for_product(product)

            product['occasion_tags'] = list(set(occasion_tags))
            product['style_tags'] = list(set(style_tags))

            updated_products.append(product)

            if (i + 1) % batch_size == 0:
                print(f"Batch {i + 1} reached. Waiting {delay} seconds before the next batch...")
                time.sleep(delay)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updated_products, f, ensure_ascii=False, indent=2)

        print(f"Processing finished. Updated products saved to '{output_file}'.")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    process_products_for_tags(INPUT_JSON_FILE, OUTPUT_JSON_FILE_TAGGED, MAX_PRODUCTS_TO_PROCESS, BATCH_SIZE,
                              DELAY_BETWEEN_BATCHES)