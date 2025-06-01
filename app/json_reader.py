import json
import csv
import os

def convert_json_to_csv(json_file_path, csv_file_path):
    """
    Reads data from a JSON file, updates the 'label' key's value
    (truncating it before ';https://' if present), and then converts
    the data into a CSV file.

    Assumes the JSON file contains either:
    1. A list of JSON objects, where each object is a row.
    2. A single JSON object (which will be treated as a single row).

    Args:
        json_file_path (str): The path to the input JSON file.
        csv_file_path (str): The path to the output CSV file.
    """
    try:
        # Check if the JSON file exists
        if not os.path.exists(json_file_path):
            print(f"Error: JSON file not found at '{json_file_path}'")
            return

        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        # Ensure data is a list for consistent processing
        if not isinstance(data, list):
            data = [data] # Wrap single JSON object in a list

        if not data:
            print("Warning: JSON file is empty or contains no objects to convert.")
            return

        # --- New Logic: Update 'label' key ---
        for item in data:
            if isinstance(item, dict) and "label" in item and isinstance(item["label"], str):
                label_value = item["label"]
                separator = ";https://"
                if separator in label_value:
                    item["label"] = label_value.split(separator, 1)[0]
                    print(f"Updated label: '{label_value}' -> '{item['label']}'")
        # --- End New Logic ---

        # Extract all unique headers (keys) from all objects
        headers = []
        for item in data:
            if isinstance(item, dict):
                for key in item.keys():
                    if key not in headers:
                        headers.append(key)
            else:
                print(f"Warning: Skipping non-dictionary item in JSON data: {item}")

        if not headers:
            print("Warning: No valid dictionary objects found in JSON data to extract headers.")
            return

        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)

            # Write the header row
            writer.writeheader()

            # Write the data rows
            for item in data:
                if isinstance(item, dict):
                    writer.writerow(item)
                # Non-dictionary items are already warned about above, no need to re-warn

        print(f"Successfully converted '{json_file_path}' to '{csv_file_path}'")

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_file_path}'. Please check its format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

json_file_path = "all_news_q1_2025.json"
csv_file_path = "newsdata1.csv"
convert_json_to_csv(json_file_path, csv_file_path) 