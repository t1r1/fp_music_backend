import os
import json
from pathlib import Path
import psycopg
import logging

logging.basicConfig(level=logging.DEBUG)


GENRES = ["classical", "electronic", "pop", "rock"]
TRACKS_NUMBER_BY_GENRE = 100

with psycopg.connect(
    "dbname=music user=t1r1 password=31337 host=localhost port=5432"
) as conn:
    for genre in GENRES:
        for i in range(1, TRACKS_NUMBER_BY_GENRE + 1):
            filename = f"{genre}_{i}.json"
            # build the path to the json file on disk
            full_filename = os.path.join("rapidapi_json_data", filename)

            with open(full_filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # build the same external id format used in the tracks table
                emotify_id = f'{data["genre"]}_{data["id"]}'

                try:
                    # extract the audio feature fields we want to store
                    tone = data["mode"]
                    danceability = data["danceability"]
                    happiness = data["happiness"]
                    energy = data["energy"]
                    liveness = data["liveness"]
                    acousticness = data["acousticness"]
                    tempo = data["tempo"]
                except:
                    logging.error(f"Exception: not enough data for file {filename}")

                with conn.cursor() as cur:
                    # find the track row that matches this json record
                    cur.execute(
                        "SELECT id FROM Tracks WHERE emotify_id = %s",
                        (emotify_id,),
                    )
                    row_result = cur.fetchone()
                    track_id = row_result[0]
                    logging.debug("track_id=%d", track_id)
                    cur.execute(
                        "Insert into Audio_Features "
                        "(track_id, tone, danceability, happiness, energy, liveness, acousticness, tempo) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            track_id,
                            tone,
                            danceability,
                            happiness,
                            energy,
                            liveness,
                            acousticness,
                            tempo,
                        ),
                    )
