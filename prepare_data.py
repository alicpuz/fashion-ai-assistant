import pandas as pd
import numpy as np
import random
import json
import re

# --- Konfiguracja ścieżek i nazw plików ---
INPUT_STYLES_CSV_FILE = 'styles.csv'
INPUT_IMAGES_CSV_FILE = 'images.csv'  # Nowy plik do wczytania
OUTPUT_JSON_FILE = 'fashion_products.json'

# --- Parametry generowania danych fikcyjnych ---
MIN_PRICE = 49.00
MAX_PRICE = 999.00
CURRENCY = "PLN"

OCCASION_TAGS = [
    "casual", "elegant", "party", "business", "sporty",
    "date_night", "wedding", "beach", "travel", "everyday",
    "formal", "semi-formal", "night_out", "festive", "work", "leisure"
]
STYLE_TAGS = [
    "minimalist", "boho", "vintage", "modern", "classic",
    "streetwear", "glamorous", "romantic", "punk", "preppy",
    "gothic", "hippie", "retro", "chic", "comfort"
]


def clean_product_name_for_url(name):
    """Czyści nazwę produktu, aby nadawała się do użycia w URL."""
    if pd.isna(name):
        return "unnamed-product"
    name = str(name).lower()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'\s+', '-', name)
    name = name.strip('-')
    return name if name else "unnamed-product"


def prepare_fashion_data(input_styles_path, input_images_path, output_json_path):
    """
    Wczytuje dane z plików CSV (styles i images), przetwarza je,
    dodaje fikcyjne ceny, linki oraz tagi okazji i stylu,
    a następnie zapisuje do pliku JSON.
    """
    try:
        # 1. Wczytanie danych stylów
        print(f"Wczytywanie danych stylów z: {input_styles_path}")
        df_styles = pd.read_csv(input_styles_path, on_bad_lines='skip', dtype={'id': str})

        # Wczytanie danych obrazków
        print(f"Wczytywanie danych obrazków z: {input_images_path}")
        df_images = pd.read_csv(input_images_path, on_bad_lines='skip', dtype={'id': str})

        # Zmiana nazwy kolumny 'filename' na 'image_id' (dla jasności) i 'link' na 'image_url'
        # 'id' w df_images odpowiada 'id' produktu ze styles.csv
        df_images = df_images.rename(columns={'id': 'product_id', 'link': 'image_url'})

        # Wstępne czyszczenie i standaryzacja nazw kolumn dla stylów
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
            # 'designer': 'brand' # USUNIĘTO - tej kolumny nie ma w styles.csv
        })

        # Kolumny, które chcemy zachować w finalnym zbiorze z df_styles
        desired_styles_columns = [
            'id',  # Musimy zachować 'id' do połączenia z df_images
            'product_name', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'collection_year', 'season', 'usage_type'
            # 'brand' # USUNIĘTO - tej kolumny nie ma
        ]
        df_styles = df_styles[desired_styles_columns]

        # Wypełniamy brakujące wartości dla 'brand' fikcyjną wartością, jeśli to jest wymagane
        # Na razie 'brand' nie jest używane, więc pominęliśmy. Jeśli będziesz chciała dodać "fikcyjne marki",
        # to można dodać kolumnę df_styles['brand'] = "Unknown Brand" tutaj.

        # Uzupełnianie brakujących wartości w df_styles
        for col in ['product_name', 'category', 'sub_category', 'master_category',
                    'gender', 'color', 'collection_year', 'season', 'usage_type']:  # 'brand' usunięte
            df_styles[col] = df_styles[col].fillna(f'unspecified_{col.replace("_", " ")}')

        # Konwersja 'collection_year' na int, uzupełnienie błędów
        df_styles['collection_year'] = pd.to_numeric(df_styles['collection_year'], errors='coerce').fillna(2020).astype(
            int)

        # Połączenie danych stylów z danymi obrazków
        # Upewniamy się, że mamy tylko jeden obrazek na ID produktu, aby uniknąć duplikacji produktów
        df_images_unique = df_images.drop_duplicates(subset=['product_id'], keep='first')

        # Połączenie DataFrame'ów na podstawie kolumny 'id' (z styles) i 'product_id' (z images)
        print("Łączenie danych stylów z obrazkami...")
        df_merged = pd.merge(df_styles, df_images_unique, left_on='id', right_on='product_id', how='left')

        # Uzupełnienie brakujących linków do obrazków (dla produktów bez obrazka)
        df_merged['image_url'] = df_merged['image_url'].fillna(
            'https://via.placeholder.com/150?text=No+Image')  # Placeholder obrazka

        # Usuwamy kolumnę 'id' i 'product_id' po scaleniu
        df_merged.drop(columns=['id', 'product_id'], inplace=True)

        # 2. Generowanie fikcyjnych danych (ceny, linki do sklepu, tagi)
        print("Generowanie fikcyjnych cen, linków do sklepu i tagów...")

        # Generowanie losowych cen
        df_merged['price'] = np.random.uniform(low=MIN_PRICE, high=MAX_PRICE, size=len(df_merged)).round(2)
        df_merged['currency'] = CURRENCY

        # Dodajemy fikcyjną kolumnę brand, bo nie ma jej w oryginalnym styles.csv, ale jest przydatna w opisie
        df_merged['brand'] = "Unknown Brand"  # Lub można tu wygenerować losowe nazwy marek

        # Generowanie fikcyjnych linków do sklepu
        df_merged['product_slug'] = df_merged['product_name'].apply(clean_product_name_for_url)
        df_merged['purchase_link'] = df_merged.apply(
            lambda
                row: f"https://twojbutik.pl/{row['master_category'].lower().replace(' ', '-')}/{row['category'].lower().replace(' ', '-')}/{row['product_slug']}",
            axis=1
        )

        # Generowanie losowych tagów okazji i stylu
        df_merged['occasion_tags'] = df_merged.apply(lambda x: random.sample(OCCASION_TAGS, random.randint(1, 3)),
                                                     axis=1)
        df_merged['style_tags'] = df_merged.apply(lambda x: random.sample(STYLE_TAGS, random.randint(1, 3)), axis=1)

        # Generowanie krótkiego opisu produktu
        df_merged['description'] = df_merged.apply(
            lambda
                row: f"{row['product_name']} w kolorze {row['color']} od {row['brand']}, idealny na okazje typu {', '.join(row['occasion_tags'])}. Dostępny w sezonie {row['season']}.",
            axis=1
        )

        # 3. Finalne czyszczenie i wybór kolumn do zapisu
        final_columns = [
            'product_name', 'description', 'category', 'sub_category', 'master_category',
            'gender', 'color', 'brand', 'collection_year', 'season', 'usage_type',
            'price', 'currency', 'purchase_link', 'image_url', 'occasion_tags', 'style_tags'
        ]
        df_final = df_merged[final_columns]

        # Usunięcie duplikatów na podstawie kluczowych cech produktu
        df_final.drop_duplicates(subset=['product_name', 'category', 'color'],
                                 inplace=True)  # Usunąłem 'brand' z subsetu

        # Konwersja DataFrame do listy słowników
        products_list = df_final.to_dict(orient='records')

        # 4. Zapisanie danych do pliku JSON
        print(f"Zapisywanie przetworzonych danych do: {output_json_path}")
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(products_list, f, ensure_ascii=False, indent=2)

        print(
            f"Dane zostały pomyślnie przetworzone i zapisane w {output_json_path}. Liczba unikalnych produktów: {len(products_list)}")


    except FileNotFoundError as fnf_error:
        print(
            f"Błąd: {fnf_error}. Upewnij się, że pliki '{input_styles_path}' i '{input_images_path}' są w tym samym katalogu co skrypt.")
    except Exception as e:
        print(f"Wystąpił błąd podczas przetwarzania danych: {e}")


if __name__ == "__main__":
    prepare_fashion_data(INPUT_STYLES_CSV_FILE, INPUT_IMAGES_CSV_FILE, OUTPUT_JSON_FILE)