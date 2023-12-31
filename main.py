#!/usr/bin/env python3

import os
import shutil
import cv2
from PIL import Image
import pytesseract
from typing import Dict
import pandas as pd

import evadb

MENU_PATH = os.path.join("evadb_data", "tmp", "menu.csv")
FOOD_PATH = os.path.join("evadb_data", "tmp", "food.csv")

def cleanup():
    """Removes any temporary file / directory created by EvaDB."""
    if os.path.exists("evadb_data"):
        shutil.rmtree("evadb_data")

if __name__ == "__main__":
    cursor = evadb.connect().cursor()
    api_key = str(input("🔑 Enter your OpenAI key: "))
    os.environ["OPENAI_KEY"] = api_key
    img_file = input("Path to image: ")
    if os.path.exists(img_file):
        img = Image.open(img_file)
        ocr_result = pytesseract.image_to_string(img)
        content = [{"text": ocr_result}]    
        df = pd.DataFrame(content)
        df.to_csv(MENU_PATH)
    else:
        raise FileNotFoundError

    cursor.drop_table("Menu", if_exists=True).execute()
    cursor.query(
        """CREATE TABLE IF NOT EXISTS Menu (text TEXT(50));"""
    ).execute()
    cursor.load(MENU_PATH, "Menu", "csv").execute()

    question = f""" Give me a list of words that appear on the given text and are food.
    No repeated items. Present in comma separated form.
    """

    if len(cursor.table("Menu").select("text").df()["menu.text"]) == 1:
        response = (cursor.table("Menu")
            .select(f"ChatGPT('{question}', text)")
            .df()["chatgpt.response"][0]).split(',')
    
    food = {}

    for item in response:

        instruction = f"""Explain what this is to someone trying to order at the restaurant in one sentence.
        In second sentence, list a few dishes that are made from this food.
        """

        content = [{"text": item}]    
        df = pd.DataFrame(content)
        df.to_csv(FOOD_PATH)

        cursor.drop_table("Food", if_exists=True).execute()
        cursor.query(
            """CREATE TABLE IF NOT EXISTS Food (text TEXT(50));"""
        ).execute()
        cursor.load(FOOD_PATH, "Food", "csv").execute()

        if len(cursor.table("Food").select("text").df()["food.text"]) == 1:
            print("")
            explanation = (cursor.table("Food")
                .select(f"ChatGPT('{instruction}', text)")
                .df()["chatgpt.response"][0])
            print(explanation)
        
        food[item] = explanation

    cleanup()

    print("Session ended")
