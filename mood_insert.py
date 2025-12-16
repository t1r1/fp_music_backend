import psycopg

MOODS = {
    "happy": "amazement",
    "inspired": "solemnity",
    "loving": "tenderness",
    "sentimental": "nostalgia",
    "relaxed": "calmness",
    "strong": "power",
    "joy": "joyful_activation",
    "tense": "tension",
    "sad": "sadness",
}

with psycopg.connect(
    "dbname=music user=t1r1 password=31337 host=localhost port=5432"
) as conn:
    with conn.cursor() as cur:
        for key in MOODS:
            cur.execute(
                "INSERT INTO Moods (mood, annotation) VALUES (%s, %s)",
                (key, MOODS[key]),
            )
