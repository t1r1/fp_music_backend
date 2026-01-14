import asyncio
import psycopg
from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

app = FastAPI(root_path="/api")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # set False as I don't use cookies/auth
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/recommendations/{mood_id}")
def read_item(mood_id: str, q: Union[str, None] = None):
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select t.title, t.artist, t.genre, t.emotify_id from Tracks as t inner join Recommendations as r on t.id=r.track_id where r.mood_id=%s order by r.final_score desc;",
                (mood_id,),
            )
            tracks = cur.fetchall()
            print(tracks)
            tracks_output = []

            for track in tracks:
                genre = track[2]
                dict = {}
                dict["title"] = track[0]
                dict["artist"] = track[1]
                dict["genre"] = genre
                filename = track[3].split("_")[1]
                dict["filepath"] = f"/mp3/{genre}/{filename}.mp3"
                tracks_output.append(dict)

    return {
        "mood_id": mood_id,
        "tracks": tracks_output,
    }
