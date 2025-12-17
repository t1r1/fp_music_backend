import asyncio
import psycopg
from typing import Union
from fastapi import FastAPI

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

app = FastAPI(root_path="/api")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/recommendations/{mood_id}")
def read_item(mood_id: str, q: Union[str, None] = None):
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT track_id FROM Recommendations WHERE mood_id = %s order by final_score desc",
                (mood_id,),
            )
            result = cur.fetchall()
            ids = []
            for item in result:
                ids.append(item[0])

            cur.execute(
                "SELECT * FROM Tracks WHERE id = ANY(%s)",
                (ids,),
            )

            tracks = cur.fetchall()
            tracks_output = []

            for track in tracks:
                dict = {}
                dict["id"] = track[0]
                dict["title"] = track[1]
                dict["artist"] = track[2]
                dict["genre"] = track[3]
                dict["filename"] = track[4].split("_")[1]
                tracks_output.append(dict)

    return {
        "mood_id": mood_id,
        "track_ids": ids,
        "tracks": tracks_output,
    }
