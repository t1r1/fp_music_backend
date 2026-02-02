import psycopg
from typing import Optional
from api.models import Mood, Track, EvaluationResponse
from psycopg.rows import dict_row

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"


def fetch_moods() -> list[Mood]:
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, mood, annotation FROM Moods;")
            moods = cur.fetchall()
            return list(
                map(lambda val: Mood(id=val[0], mood=val[1], annotation=val[2]), moods)
            )


def fetch_recommended_tracks(
    mood_id: int, algo_version: str, genre: Optional[list[str]], sid: str
) -> list[Track]:

    query = (
        "SELECT r.id, t.title, t.artist, t.genre, t.emotify_id "
        "FROM Tracks AS t "
        "INNER JOIN Recommendations AS r ON t.id = r.track_id "
        "WHERE r.mood_id = %s "
        "AND r.algorithm_version LIKE %s"
    )
    params = [f"{mood_id}", f"%{algo_version}%"]

    if genre:
        query += " AND t.genre = ANY(%s)"
        params.append(genre)

    query += " ORDER BY r.final_score DESC"

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            tracks = cur.fetchall()

            def mapper(val) -> Track:
                filename = val[4].split("_")[1]
                return Track(
                    id=val[0],
                    title=val[1],
                    artist=val[2],
                    genre=val[3],
                    filepath=f"/api/media/{val[3]}/{filename}.mp3",
                )

            return list(map(mapper, tracks))


def insert_or_update_evaluation(sid: str, recommendation_id: int, liked: int):
    if liked not in (1, -1):
        raise ValueError("Liked must be 1 or -1")

    sql = """
    INSERT INTO evaluations (user_session_id, recommendation_id, liked)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_session_id, recommendation_id)
    DO UPDATE SET
      liked = EXCLUDED.liked,
      created_at = now()
    RETURNING id, user_session_id, recommendation_id, liked, created_at;
    """

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sid, recommendation_id, liked))
            row = cur.fetchone()
        conn.commit()

    return EvaluationResponse(recommendation_id=recommendation_id, liked=liked)


def fetch_evaluations(sid: str):
    sql = """
    SELECT * from Evaluations where user_session_id = %s 
    """
    with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sid,))
            rows = cur.fetchall()
            print("DB rows:", rows)
            return rows
