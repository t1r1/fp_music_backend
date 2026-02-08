import requests
import os
import csv
import json
from time import sleep

API_URI = "https://track-analysis.p.rapidapi.com/pktx/analysis"
OUTPUT_DIR_NAME = "rapidapi_json_data"

headers = {
    "x-rapidapi-key": "187b34d13bmsh0045d05cfffd71dp103e2ejsnb35eaf3424ca",  # TODO: revoke for security before publishing repo
    "x-rapidapi-host": "track-analysis.p.rapidapi.com",
}


def main():
    os.makedirs(OUTPUT_DIR_NAME, exist_ok=True)

    with open("metadata.csv") as f:
        reader = csv.DictReader(f)
        for item in reader:

            print(item)
            params = {"song": item["title"], "artist": item["artist"]}
            genre = item["genre"]
            id = item["id"]
            filename = os.path.join(OUTPUT_DIR_NAME, f"{genre}_{id}.json")
            if os.path.exists(filename):
                continue

            response = requests.get(API_URI, params=params, headers=headers)

            try:
                data = response.json()
                print(data)
            except:
                print(response.text)
                raise

            with open(filename, "w") as jsonf:
                json.dump({**data, "id": id, "genre": genre}, jsonf)

            sleep(2)  # follow the rate limits of the service


if __name__ == "__main__":
    main()
