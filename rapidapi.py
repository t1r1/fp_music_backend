import requests
import os
import csv
import json
from time import sleep

# api endpoint for track analysis
API_URI = "https://track-analysis.p.rapidapi.com/pktx/analysis"

# directory where raw json responses will be stored
OUTPUT_DIR_NAME = "rapidapi_json_data"

# request headers for rapidapi authentication
headers = {
    "x-rapidapi-key": "REVOKED",
    "x-rapidapi-host": "track-analysis.p.rapidapi.com",
}


def main():
    # create the output directory if it does not exist yet
    os.makedirs(OUTPUT_DIR_NAME, exist_ok=True)

    # read input song metadata from CSV
    with open("metadata.csv") as f:
        reader = csv.DictReader(f)
        for item in reader:
            print(item)

            # build query parameters from song title and artist
            params = {"song": item["title"], "artist": item["artist"]}

            # extract fields used for output naming and saved metadata
            genre = item["genre"]
            id = item["id"]

            # build the destination filename for this track
            filename = os.path.join(OUTPUT_DIR_NAME, f"{genre}_{id}.json")

            # skip tracks that were already downloaded earlier
            if os.path.exists(filename):
                continue

            # request analysis data from the api
            response = requests.get(API_URI, params=params, headers=headers)

            try:
                # parse the json response body
                data = response.json()

                print(data)
            except:
                print(response.text)
                raise

            # save the api response together with local id and genre
            with open(filename, "w") as jsonf:
                json.dump({**data, "id": id, "genre": genre}, jsonf)

            # wait between requests to respect api rate limits
            sleep(2)


if __name__ == "__main__":
    main()
