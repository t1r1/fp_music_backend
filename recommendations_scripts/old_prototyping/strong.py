import pandas as pd
import psycopg

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

MOOD_ID = 6  # strong / power
ALGO_VERSION = "power_hybrid_v1"
TOP_K = 50

# relative weights between annotations and audio features
W_ANN = 0.6
W_AUD = 0.4


# safe min-max normalisation to [0, 1]
def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        # all values equal or empty series -> return zeros
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with psycopg.connect(DB_DSN) as conn:
        tracks = pd.read_sql(
            "SELECT id AS track_id, title, artist, genre, filepath FROM Tracks;",
            conn,
        )

        ann = pd.read_sql(
            """
            SELECT
                id,
                track_id,
                amazement,
                solemnity,
                tenderness,
                nostalgia,
                calmness,
                power,
                joyful_activation,
                tension,
                sadness,
                mood,
                genre
            FROM Annotations;
            """,
            conn,
        )

        af = pd.read_sql(
            """
            SELECT
                track_id,
                energy,
                happiness,
                acousticness,
                tempo
            FROM Audio_Features;
            """,
            conn,
        )

    return tracks, ann, af


# Uses:
#         power (primary)
#         joyful_activation (energy / drive)
#         tension (intensity)
#         sadness, calmness (penalise)


def build_power_annotation_scores(ann: pd.DataFrame) -> pd.DataFrame:
    # aggregate multiple annotation rows per track by mean
    ann_agg = ann.groupby("track_id", as_index=False).mean(numeric_only=True)

    # weighted combination for "strong / power" mood
    ann_agg["ann_power_score_raw"] = (
        0.45 * ann_agg["power"]
        + 0.30 * ann_agg["joyful_activation"]
        + 0.15 * ann_agg["tension"]
        - 0.10 * ann_agg["sadness"]
        - 0.05 * ann_agg["calmness"]
    )

    ann_agg["ann_power_score"] = minmax(ann_agg["ann_power_score_raw"])
    return ann_agg[["track_id", "ann_power_score"]]


# Uses:
#         energy (high)
#         tempo (high)
#         acousticness (low)
def build_power_audio_scores(af: pd.DataFrame) -> pd.DataFrame:
    af = af.copy()

    af["energy_n"] = minmax(af["energy"])
    af["tempo_n"] = minmax(af["tempo"])

    # low acousticness -> higher score
    af["acoustic_inv"] = 1 - minmax(af["acousticness"])

    af["audio_power_score_raw"] = (
        0.5 * af["energy_n"] + 0.3 * af["tempo_n"] + 0.2 * af["acoustic_inv"]
    )

    af["audio_power_score"] = minmax(af["audio_power_score_raw"])
    return af[["track_id", "audio_power_score"]]


def build_power_recommendations(
    tracks: pd.DataFrame,
    ann: pd.DataFrame,
    af: pd.DataFrame,
    top_k: int = TOP_K,
) -> pd.DataFrame:
    ann_scores = build_power_annotation_scores(ann)
    aud_scores = build_power_audio_scores(af)

    # combine annotation + audio scores
    scores = ann_scores.merge(aud_scores, on="track_id", how="inner")

    scores["final_score"] = (
        W_ANN * scores["ann_power_score"] + W_AUD * scores["audio_power_score"]
    )

    # join back to tracks, sort, and select top K
    recs = (
        scores.merge(tracks, on="track_id", how="left")
        .sort_values("final_score", ascending=False)
        .head(top_k)
    )

    recs = recs[["track_id", "title", "artist", "genre", "filepath", "final_score"]]

    return recs


def main():
    tracks, ann, af = load_data()
    recs = build_power_recommendations(tracks, ann, af, top_k=TOP_K)

    print(f"Top {TOP_K} recommendations for mood {MOOD_ID} (strong / power)")
    print(f"Algorithm version: {ALGO_VERSION}\n")
    print(recs.to_string(index=False))


if __name__ == "__main__":
    main()
