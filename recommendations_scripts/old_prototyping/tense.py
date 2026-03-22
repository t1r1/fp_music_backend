# Tense when:

# energy is high
# tempo is high
# happiness is low
# acousticness is low (more electric/harsh)

# So audio_score is a weighted mix of:
# + energy_n
# + tempo_n
# + (1 - happy_n)
# + (1 - acoustic_n)


import pandas as pd
import psycopg
import os

DB_PASSWD = os.getenv("DB_PASSWD", "31337")
DB_DSN = f"dbname=music user=t1r1 password={DB_PASSWD} host=localhost port=5432"

MOOD_ID = 8  # "tense"
ALGO_VERSION = "tense_hybrid_v1"
TOP_K = 50

# hybrid weights: annotations vs audio
W_ANN = 0.6
W_AUD = 0.4

# audio feature weights for "tense"
W_ENERGY = 0.35
W_TEMPO = 0.30
W_HAPPY = 0.20  # will be applied as (1 - happy_n)
W_ACOUSTIC = 0.15  # will be applied as (1 - acoustic_n)


def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


# 1. read required tables into pandas
with psycopg.connect(DB_DSN) as conn:
    # Tracks
    tracks = pd.read_sql(
        "SELECT id AS track_id, title, artist, genre FROM Tracks;",
        conn,
    )

    # annotations: tension
    ann = pd.read_sql(
        """
        SELECT track_id, tension
        FROM Annotations;
        """,
        conn,
    )

    # audio features
    af = pd.read_sql(
        """
        SELECT track_id, energy, happiness, tempo, acousticness
        FROM Audio_Features;
        """,
        conn,
    )

    # make sure mood exists
    moods = pd.read_sql(
        "SELECT id AS mood_id, mood FROM Moods WHERE id = %s;",
        conn,
        params=(MOOD_ID,),
    )
    if moods.empty:
        raise ValueError(f"Mood '{MOOD_ID}' not found in Moods table.")
    mood_id = int(moods.iloc[0]["mood_id"])


# 2. Annotation score per track: P(tense | track)
ann_score = ann.groupby("track_id", as_index=False).agg(
    tense_count=("tension", "sum"),
    n=("tension", "count"),
)
ann_score["annotation_score"] = ann_score["tense_count"] / ann_score["n"]

# 3) normalize audio features + compute audio tension score
af = af.copy()
af["energy_n"] = minmax(af["energy"])
af["happy_n"] = minmax(af["happiness"])
af["tempo_n"] = minmax(af["tempo"])
af["acoustic_n"] = minmax(af["acousticness"])

# Tension profile:
# - higher when energy is high
# - higher when tempo is high
# - higher when happiness is low
# - higher when acousticness is low (more electric/harsh)
af["audio_score"] = (
    W_ENERGY * af["energy_n"]
    + W_TEMPO * af["tempo_n"]
    + W_HAPPY * (1 - af["happy_n"])
    + W_ACOUSTIC * (1 - af["acoustic_n"])
)

audio_score = af[["track_id", "audio_score"]]

# 4. combine tracks + scores
df = tracks.merge(audio_score, on="track_id", how="inner").merge(
    ann_score[["track_id", "annotation_score"]],
    on="track_id",
    how="left",
)

# if we have no annotations for a track, treat annotation_score as 0
df["annotation_score"] = df["annotation_score"].fillna(0.0)

# 5) final hybrid score
df["final_score"] = W_ANN * df["annotation_score"] + W_AUD * df["audio_score"]

# 6) take Top-K recommendations
recs = df.sort_values("final_score", ascending=False).head(TOP_K).copy()

# 7) build output table
out = recs[["track_id", "audio_score", "annotation_score", "final_score"]].copy()
out["mood_id"] = mood_id
out["algorithm_version"] = ALGO_VERSION

# 8) to CSV (DEBUG)
csv_file = "recommendations_tense.csv"
out.to_csv(csv_file, index=False)
print("Saved:", csv_file)
print(out.head(10))

# 9) insert into DB
with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        # clear previous run for same mood/version
        cur.execute(
            """
            DELETE FROM Recommendations
            WHERE mood_id = %s AND algorithm_version = %s;
            """,
            (MOOD_ID, ALGO_VERSION),
        )

        for _, row in out.iterrows():
            cur.execute(
                """
                INSERT INTO Recommendations
                    (track_id, mood_id,
                     audio_score, annotation_score, final_score,
                     algorithm_version)
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

print(f"inserted {len(out)} tense recommendations (mood_id={MOOD_ID}).")
