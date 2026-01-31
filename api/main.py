import psycopg
from fastapi import FastAPI
from typing import Optional, List
from fastapi import Query

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

app = FastAPI(root_path="/api")

# serve everything in ./media under /media
app.mount("/media", StaticFiles(directory="media"), name="media")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/moods")
def fetch_moods():
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, mood, annotation from Moods;",
                (),
            )
            moods = cur.fetchall()

            def map_function(val):
                return {"id": val[0], "mood": val[1], "annotation": val[2]}

            mapped_moods = map(map_function, moods)

        return {
            "moods": list(mapped_moods),
        }


@app.get("/recommendations/{mood_id}")
def read_item(
    mood_id: str,
    genre: Optional[List[str]] = Query(default=None),
):
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            query = """
                select r.id, t.title, t.artist, t.genre, t.emotify_id from Tracks as t inner join Recommendations as r on t.id=r.track_id where r.mood_id=%s and r.algorithm_version LIKE %s
            """
            params = [mood_id, "%v3%"]

            if genre:
                query += " and t.genre = ANY(%s)"
                params.append(genre)
            query += "order by r.final_score DESC"

            cur.execute(query, params)
            tracks = cur.fetchall()
            print(tracks)
            tracks_output = []

            for track in tracks:
                genre = track[3]
                dict = {}
                dict["id"] = track[0]
                dict["title"] = track[1]
                dict["artist"] = track[2]
                dict["genre"] = genre
                filename = track[4].split("_")[1]
                dict["filepath"] = (
                    f"http://127.0.0.1:8000/api/media/{genre}/{filename}.mp3"
                )
                tracks_output.append(dict)

    return {
        "mood_id": mood_id,
        "tracks": tracks_output,
    }
