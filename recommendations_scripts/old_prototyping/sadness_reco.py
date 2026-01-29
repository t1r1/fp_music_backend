import pandas as pd
import psycopg

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

MOOD_ID = 9
ALGO_VERSION = "sad_hybrid_v1"
TOP_K = 50

# weights
W_ANN = 0.6
W_AUD = 0.4


def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


# 1) Read required tables into pandas
with psycopg.connect(DB_DSN) as conn:
    tracks = pd.read_sql(
        "SELECT id AS track_id, title, artist, genre FROM Tracks;", conn
    )

    ann = pd.read_sql("SELECT track_id, sadness FROM Annotations;", conn)

    af = pd.read_sql(
        """
        SELECT track_id, energy, happiness, acousticness, tempo
        FROM Audio_Features;
        """,
        conn,
    )

# 2) Compute annotation_score per track: P(sadness | track)
ann_score = ann.groupby("track_id", as_index=False).agg(
    sad_count=("sadness", "sum"), n=("sadness", "count")
)
ann_score["annotation_score"] = ann_score["sad_count"] / ann_score["n"]

# 3) Normalize audio features and compute audio sadness score
af = af.copy()
af["energy_n"] = minmax(af["energy"])
af["happy_n"] = minmax(af["happiness"])
af["tempo_n"] = minmax(af["tempo"])
af["acoustic_n"] = minmax(af["acousticness"])

# Sadness profile:
# - higher when energy is low, happiness is low, tempo is low, acousticness is high
af["audio_score"] = (
    0.30 * (1 - af["energy_n"])
    + 0.35 * (1 - af["happy_n"])
    + 0.20 * (1 - af["tempo_n"])
    + 0.15 * af["acoustic_n"]
)

audio_score = af[["track_id", "audio_score"]]

# 4) Combine track data + scores
df = tracks.merge(audio_score, on="track_id", how="inner").merge(
    ann_score[["track_id", "annotation_score"]], on="track_id", how="left"
)

df["annotation_score"] = df["annotation_score"].fillna(0.0)

df["final_score"] = W_ANN * df["annotation_score"] + W_AUD * df["audio_score"]

# 5) Top-K recommendations
out = df.sort_values("final_score", ascending=False).head(TOP_K).copy()
out = out[["track_id", "audio_score", "annotation_score", "final_score"]]
out["mood_id"] = MOOD_ID
out["algorithm_version"] = ALGO_VERSION

# 6) Save to CSV (transparent debugging)
csv_file = "recommendations_sad.csv"
out.to_csv(csv_file, index=False)
print("Saved:", csv_file)
print(out.head(10))

# 7) Insert into DB row-by-row
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

print(f"Inserted {len(out)} sadness recommendations (mood_id={MOOD_ID}).")
