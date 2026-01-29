import pandas as pd
import psycopg

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

MOOD_ID = 7  # "joy"
ALGO_VERSION = "joy_hybrid_v1"
TOP_K = 50

# weights
W_ANN = 0.6
W_AUD = 0.4

W_ENERGY = 0.35
W_DANCE = 0.35
W_HAPPY = 0.20
W_TEMPO = 0.10


def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


with psycopg.connect(DB_DSN) as conn:
    # 1) Read data from DB into pandas
    tracks = pd.read_sql(
        "SELECT id AS track_id, title, artist, genre FROM Tracks;", conn
    )

    ann = pd.read_sql(
        """
        SELECT track_id, joyful_activation
        FROM Annotations;
        """,
        conn,
    )

    af = pd.read_sql(
        """
        SELECT track_id, energy, danceability, happiness, tempo
        FROM Audio_Features;
        """,
        conn,
    )

    moods = pd.read_sql(
        "SELECT id AS mood_id, mood FROM Moods WHERE id = %s;",
        conn,
        params=(MOOD_ID,),
    )
    if moods.empty:
        raise ValueError(f"Mood '{MOOD_ID}' not found in Moods table.")
    mood_id = int(moods.iloc[0]["mood_id"])


# 2) Annotation score per track (joy probability)
ann_score = ann.groupby("track_id", as_index=False).agg(
    joy_count=("joyful_activation", "sum"), n=("joyful_activation", "count")
)
ann_score["annotation_score"] = ann_score["joy_count"] / ann_score["n"]

# 3) Normalize audio features and compute audio score
af = af.copy()
af["energy_n"] = minmax(af["energy"])
af["dance_n"] = minmax(af["danceability"])
af["happy_n"] = minmax(af["happiness"])
af["tempo_n"] = minmax(af["tempo"])

af["audio_score"] = (
    W_ENERGY * af["energy_n"]
    + W_DANCE * af["dance_n"]
    + W_HAPPY * af["happy_n"]
    + W_TEMPO * af["tempo_n"]
)

audio_score = af[["track_id", "audio_score"]]

# 4) Combine tracks + scores
df = tracks.merge(audio_score, on="track_id", how="inner").merge(
    ann_score[["track_id", "annotation_score"]], on="track_id", how="left"
)

df["annotation_score"] = df["annotation_score"].fillna(0.0)

df["final_score"] = W_ANN * df["annotation_score"] + W_AUD * df["audio_score"]

# 5) Take top K
recs = df.sort_values("final_score", ascending=False).head(TOP_K).copy()

# 6) Build the output table structure
out = recs[["track_id", "audio_score", "annotation_score", "final_score"]].copy()
out["mood_id"] = mood_id
out["algorithm_version"] = ALGO_VERSION

# 7) Save to file (for transparency / debugging)
out_file = "recommendations_joy.csv"
out.to_csv(out_file, index=False)

print("Saved:", out_file)
print(out.head(10))


# Insert into DB row-by-row
with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        # Clear previous run for the same mood/version
        cur.execute(
            "DELETE FROM Recommendations WHERE mood_id = %s AND algorithm_version = %s;",
            (MOOD_ID, ALGO_VERSION),
        )

        for _, row in out.iterrows():
            cur.execute(
                """
                INSERT INTO Recommendations
                    (track_id, mood_id, audio_score, annotation_score, final_score, algorithm_version)
                VALUES
                    (%s, %s, %s, %s, %s, %s);
                """,
                (
                    int(row["track_id"]),
                    int(row["mood_id"]),
                    float(row["audio_score"]),
                    float(row["annotation_score"]),
                    float(row["final_score"]),
                    str(row["algorithm_version"]),
                ),
            )

    conn.commit()

print(f"Inserted {len(out)} joy recommendations (mood_id={MOOD_ID}).")
