# FashionMate AI 👗✨

**Your Personal AI-Powered Fashion Assistant**

## Project Overview

The **FashionMate AI** is an intelligent web application designed to revolutionize the way users find and select clothing. Leveraging the power of Google Gemini AI, it provides personalized outfit recommendations based on user preferences, occasions, and budget. The application enhances the shopping experience by offering not just styling ideas, but concrete product suggestions with links from a curated database, making fashion advice both inspiring and actionable.

This project was developed as an academic exercise, demonstrating the practical application of Large Language Models (LLMs), Retrieval Augmented Generation (RAG), and Structured Output techniques.

## Features

*   **Personalized Recommendations:** Get outfit suggestions tailored to your specific needs, including occasion, preferred style, budget, gender, and color.
*   **"Full Outfit" Mode:** Request a complete styling where AI composes an entire ensemble, ensuring the total cost stays within your budget.
*   **AI-Powered Tagging:** Products in the database are intelligently tagged with style and occasion keywords by Gemini AI, enabling more relevant search and filtering.
*   **Context-Aware Generation (RAG):** Gemini AI suggests products that actually exist in the application's database, eliminating generic or unavailable recommendations.
*   **Structured Output:** Gemini's responses are parsed from a structured JSON format, allowing for precise display of styling proposals and product details.
*   **Visual Product Display:** See images of recommended products, along with their prices and direct (simulated) purchase links.
*   **Intuitive User Interface:** Built with Streamlit for a simple yet interactive web experience.

## Technologies Used

*   **AI/LLM:** Google Gemini 2.5 Flash API
*   **Data Processing:** `pandas`
*   **Web Framework:** `Streamlit`
*   **Environment Management:** `python-dotenv`
*   **Data Storage:** JSON files

## Setup and Installation

Follow these steps to get your AI Style Advisor running locally:

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Obtain Google Gemini API Key

### 5. Configure API Key

Create a file named .env in the root directory of your project (where app.py is located). Add your Gemini API key to this file:

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

### 6. Prepare the Product Database

This step processes raw fashion data and filters it for apparel, then generates intelligent tags using Gemini AI.

#### a. Download Raw Data

Download the `styles.csv` and `images.csv` files from the [Fashion Product Images Dataset on Kaggle](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset). Place both files in your project's root directory.

#### b. Run Data Preparation Script

First, run `prepare_data.py` to filter the dataset for apparel and structure it.

```bash
python prepare_data.py
```

This will generate fashion_products.json, containing only apparel items with initial (empty) tag fields.

#### c. Generate Tags with Gemini AI

```bash
python generate_tags_with_gemini.py
```

This will generate fashion_products_tagged.json, which is the database used by the main application. You might need to run this script over several days if you want to tag a large portion of the dataset, given the daily API limits.

### 7. Create requirements.txt

```bash
pip freeze > requirements.txt
```

### 8. Run the Application

```bash
streamlit run app.py
```

## How to Use the Application

### 1. Fill out the form with your preferences

### 2. Click "Find me an outfit!"

### 3. Wait for the AI's response

### 4. Explore AI's Recommendations
