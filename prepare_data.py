import pandas as pd
import numpy as np
import json
import re

INPUT_STYLES_CSV_FILE = 'styles.csv'
INPUT_IMAGES_CSV_FILE = 'images.csv'
OUTPUT_JSON_FILE = 'fashion_products.json'

MIN_PRICE = 49.00
MAX_PRICE = 399.00
CURRENCY = "PLN"


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
    if pd.isna(filename):
        return None
    return str(filename).split('.')[0]


def prepare_fashion_data(input_styles_path, input_images_path, output_json_path):
    try:
        print(f"Loading styles data from: {input_styles_path}")
        df_styles = pd.read_csv(input_styles_path, on_bad_lines='skip', dtype={'id': str})

        print(f"Loading images data from: {input_images_path}")
        df_images = pd.read_csv(input_images_path, on_bad_lines='skip', dtype={'filename': str, 'link': str})

        df_images['product_id'] = df_images['filename'].apply(extract_id_from_filename)
        df_images = df_images.rename(columns={'link': 'image_url'})

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

        initial_num_products = len(df_styles)
        df_styles = df_styles[df_styles['master_category'].str.lower() == 'apparel']
        print(f"Originally {initial_num_products} products, after filtering for apparel: {len(df_styles)}.")

        desired_styles_columns = [
            'id',
            'product_name', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'collection_year', 'season', 'usage_type'
        ]
        df_styles = df_styles[desired_styles_columns]

        for col in ['product_name', 'category', 'sub_category', 'master_category',
                    'gender', 'color', 'collection_year', 'season', 'usage_type']:
            df_styles[col] = df_styles[col].fillna(
                f'unspecified {col.replace("_", " ")}')

        df_styles['collection_year'] = pd.to_numeric(df_styles['collection_year'], errors='coerce').fillna(2020).astype(
            int)

        df_images_unique = df_images.drop_duplicates(subset=['product_id'], keep='first')

        print("Merging styles data with images...")
        df_merged = pd.merge(df_styles, df_images_unique[['product_id', 'image_url']], left_on='id',
                             right_on='product_id', how='left')

        df_merged['image_url'] = df_merged['image_url'].fillna('https://via.placeholder.com/150?text=No+Image')

        df_merged.drop(columns=['id', 'product_id'], inplace=True)

        print("Generating dummy prices, store links, and tags...")

        df_merged['price'] = np.random.uniform(low=MIN_PRICE, high=MAX_PRICE, size=len(df_merged)).round(2)
        df_merged['currency'] = CURRENCY

        df_merged['brand'] = "Unknown Brand"

        df_merged['product_slug'] = df_merged['product_name'].apply(clean_product_name_for_url)
        df_merged['purchase_link'] = df_merged.apply(
            lambda
                row: f"https://yourboutique.com/{row['master_category'].lower().replace(' ', '-')}/{row['category'].lower().replace(' ', '-')}/{row['product_slug']}",
            axis=1
        )

        df_merged['occasion_tags'] = [[] for _ in range(len(df_merged))]
        df_merged['style_tags'] = [[] for _ in range(len(df_merged))]

        df_merged['description'] = df_merged.apply(
            lambda
                row: f"{row['product_name']} in {row['color']} from {row['brand']}, intended for {row['gender']}. Category: {row['category']}, subcategory: {row['sub_category']}. Usage type: {row['usage_type']}. Collection year: {row['collection_year']}.",
            axis=1
        )

        final_columns = [
            'product_name', 'description', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'brand', 'collection_year', 'season', 'usage_type',
            'price', 'currency', 'purchase_link', 'image_url', 'occasion_tags', 'style_tags'
        ]
        df_final = df_merged[final_columns]

        df_final.drop_duplicates(subset=['product_name', 'category', 'color'], inplace=True)

        products_list = df_final.to_dict(orient='records')

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