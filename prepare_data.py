import pandas as pd
import numpy as np
import random
import json
import re
import os

# --- Configuration for paths and file names ---
INPUT_STYLES_CSV_FILE = 'styles.csv'
INPUT_IMAGES_CSV_FILE = 'images.csv'
OUTPUT_JSON_FILE = 'fashion_products.json'  # This file will now contain only apparel

# --- Parameters for generating dummy data ---
MIN_PRICE = 49.00
MAX_PRICE = 399.00
CURRENCY = "PLN"  # Keeping PLN as currency code


def clean_product_name_for_url(name):
    """Cleans product name to be suitable for URL."""
    if pd.isna(name):
        return "unnamed-product"
    name = str(name).lower()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'\s+', '-', name)
    name = name.strip('-')
    return name if name else "unnamed-product"


def extract_id_from_filename(filename):
    """Extracts product ID from filename (e.g., '15970.jpg' -> '15970')."""
    if pd.isna(filename):
        return None
    return str(filename).split('.')[0]


def prepare_fashion_data(input_styles_path, input_images_path, output_json_path):
    """
    Loads data from CSV files (styles and images), processes it,
    FILTERS ONLY FOR APPAREL, adds dummy prices, links,
    and initially empty occasion/style tags (to be overwritten by Gemini),
    then saves to a JSON file.
    """
    try:
        # 1. Load styles data
        print(f"Loading styles data from: {input_styles_path}")
        df_styles = pd.read_csv(input_styles_path, on_bad_lines='skip', dtype={'id': str})

        # Load images data
        print(f"Loading images data from: {input_images_path}")
        df_images = pd.read_csv(input_images_path, on_bad_lines='skip', dtype={'filename': str, 'link': str})

        # Extract product_id from filename column in df_images
        df_images['product_id'] = df_images['filename'].apply(extract_id_from_filename)
        df_images = df_images.rename(columns={'link': 'image_url'})

        # Initial cleaning and standardization of column names for styles
        df_styles.columns = df_styles.columns.str.strip()
        df_styles = df_styles.rename(columns={
            'productDisplayName': 'product_name',
            'articleType': 'category',
            'baseColour': 'color',
            'subCategory': 'sub_category',
            'masterCategory': 'master_category',
            'gender': 'gender',
            'year': 'collection_year',
            'season': 'season',
            'usage': 'usage_type',
        })

        # --- FILTERING ONLY FOR APPAREL ---
        # The 'master_category' column contains general categories. "Apparel" means clothing.
        initial_num_products = len(df_styles)
        df_styles = df_styles[df_styles['master_category'].str.lower() == 'apparel']
        print(f"Originally {initial_num_products} products, after filtering for apparel: {len(df_styles)}.")

        # Columns to retain in the final dataset from df_styles
        desired_styles_columns = [
            'id',  # Must keep 'id' for merging with df_images
            'product_name', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'collection_year', 'season', 'usage_type'
        ]
        df_styles = df_styles[desired_styles_columns]

        # Fill missing values in df_styles
        for col in ['product_name', 'category', 'sub_category', 'master_category',
                    'gender', 'color', 'collection_year', 'season', 'usage_type']:
            df_styles[col] = df_styles[col].fillna(
                f'unspecified {col.replace("_", " ")}')  # Changed to English placeholder

        # Convert 'collection_year' to int, fill errors
        df_styles['collection_year'] = pd.to_numeric(df_styles['collection_year'], errors='coerce').fillna(2020).astype(
            int)

        # Merge styles data with image data
        df_images_unique = df_images.drop_duplicates(subset=['product_id'], keep='first')

        print("Merging styles data with images...")
        df_merged = pd.merge(df_styles, df_images_unique[['product_id', 'image_url']], left_on='id',
                             right_on='product_id', how='left')

        # Fill missing image links
        df_merged['image_url'] = df_merged['image_url'].fillna('https://via.placeholder.com/150?text=No+Image')

        df_merged.drop(columns=['id', 'product_id'], inplace=True)

        # 2. Generate dummy data (prices, store links, tags)
        print("Generating dummy prices, store links, and tags...")

        df_merged['price'] = np.random.uniform(low=MIN_PRICE, high=MAX_PRICE, size=len(df_merged)).round(2)
        df_merged['currency'] = CURRENCY

        df_merged['brand'] = "Unknown Brand"

        df_merged['product_slug'] = df_merged['product_name'].apply(clean_product_name_for_url)
        df_merged['purchase_link'] = df_merged.apply(
            lambda
                row: f"https://yourboutique.com/{row['master_category'].lower().replace(' ', '-')}/{row['category'].lower().replace(' ', '-')}/{row['product_slug']}",
            # Changed URL base
            axis=1
        )

        # Tags will be added by generate_tags_with_gemini.py, so we don't initialize them here
        df_merged['occasion_tags'] = [[] for _ in range(len(df_merged))]
        df_merged['style_tags'] = [[] for _ in range(len(df_merged))]

        # Generate a brief product description (for use by Gemini)
        df_merged['description'] = df_merged.apply(
            lambda
                row: f"{row['product_name']} in {row['color']} from {row['brand']}, intended for {row['gender']}. Category: {row['category']}, subcategory: {row['sub_category']}. Usage type: {row['usage_type']}. Collection year: {row['collection_year']}.",
            axis=1
        )

        # 3. Final cleaning and selection of columns to save
        final_columns = [
            'product_name', 'description', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'brand', 'collection_year', 'season', 'usage_type',
            'price', 'currency', 'purchase_link', 'image_url', 'occasion_tags', 'style_tags'  # Include tags here
        ]
        df_final = df_merged[final_columns]

        df_final.drop_duplicates(subset=['product_name', 'category', 'color'], inplace=True)

        products_list = df_final.to_dict(orient='records')

        # 4. Save data to JSON file
        print(f"Saving processed data to: {output_json_path}")
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(products_list, f, ensure_ascii=False, indent=2)

        print(
            f"Data successfully processed and saved to {output_json_path}. Number of unique products: {len(products_list)}")

    except FileNotFoundError as fnf_error:
        print(
            f"Error: {fnf_error}. Ensure that '{input_styles_path}' and '{input_images_path}' files are in the same directory as the script.")
    except Exception as e:
        print(f"An error occurred during data processing: {e}")


if __name__ == "__main__":
    prepare_fashion_data(INPUT_STYLES_CSV_FILE, INPUT_IMAGES_CSV_FILE, OUTPUT_JSON_FILE)