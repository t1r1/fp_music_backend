import os
import csv
import psycopg

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"
CSV_PATH = "./datasets/musicemotions.csv"

# mapping of Emotify+ feeling to Moods
FEELING_TO_MOOD = {
    "happy": "happy",
    "joyful": "joy",
    "relaxing": "relaxed",
    "sad": "sad",
    "anxious": "tense",
    "annoying": "tense",
    "energizing": "strong",
    "dreamy": "sentimental",
    "amusing": "joy",
    "neutral": "relaxed",
}


# converts 'pop/1.mp3' to 'pop_1' (emotify_id)
def filename_to_emotify_id(file_name: str) -> str:
    file_name = file_name.strip().lower()
    genre, filename = file_name.split("/", 1)
    track_num = os.path.splitext(os.path.basename(filename))[0]
    return f"{genre}_{track_num}"


with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        inserted = 0
        skipped_missing_track = 0
        skipped_missing_mood = 0
        skipped_missing_mapping = 0

        with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for item in reader:
                raw_feeling = item["Feeling"].strip().lower()

                mapped_mood_name = FEELING_TO_MOOD.get(raw_feeling)
                if not mapped_mood_name:
                    print(f"Skipping unknown feeling: {raw_feeling}")
                    skipped_missing_mapping += 1
                    continue

                file_name = item["fileName"].strip()
                emotify_id = filename_to_emotify_id(file_name)

                cur.execute(
                    "select id from tracks where emotify_id = %s",
                    (emotify_id,),
                )
                track_row = cur.fetchone()

                if not track_row:
                    print(f"Track not found for {file_name} - {emotify_id}")
                    skipped_missing_track += 1
                    continue

                track_id = track_row[0]

                cur.execute(
                    "select id from moods where mood = %s",
                    (mapped_mood_name,),
                )
                mood_row = cur.fetchone()

                if not mood_row:
                    print(f"Mood not found in moods table: {mapped_mood_name}")
                    skipped_missing_mood += 1
                    continue

                mapped_mood_id = mood_row[0]

                user_id = int(item["UserID"])
                gender = item["Gender"].strip() if item["Gender"] else None
                rating = int(item["Rating"])

                cur.execute(
                    """
                    insert INTO emotional_annotations
                        (track_id, mapped_mood_id, raw_feeling, user_id, gender, rating)
                    values
                        (%s, %s, %s, %s, %s, %s)
                    ON conflict (track_id, user_id, raw_feeling) DO NOTHING
                    """,
                    (
                        track_id,
                        mapped_mood_id,
                        raw_feeling,
                        user_id,
                        gender,
                        rating,
                    ),
                )

                inserted += 1

        print(f"Inserted rows: {inserted}")
        print(f"Skipped missing track: {skipped_missing_track}")
        print(f"Skipped missing mood: {skipped_missing_mood}")
        print(f"Skipped missing mapping: {skipped_missing_mapping}")
