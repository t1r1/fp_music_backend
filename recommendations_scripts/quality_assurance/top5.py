import pandas as pd
import psycopg

DB_CREDENTIALS = "dbname=music user=t1r1 password=31337 host=localhost port=5432"

with psycopg.connect(DB_CREDENTIALS) as conn:
    recommendations = pd.read_sql_query(
        """
        select track_id, mood_id, final_score, algorithm_version from recommendations
        """,
        conn,
    )

    emotional_annotations = pd.read_sql_query(
        """
        select track_id, mapped_mood_id AS mood_id, rating_normalized
        from emotional_annotations
        """,
        conn,
    )

    moods = pd.read_sql_query(
        """
        select id AS mood_id, mood FROM moods
        """,
        conn,
    )

# calculate an average external score for each (track, mood)
external_scores = (
    emotional_annotations.groupby(["track_id", "mood_id"], as_index=False)[
        "rating_normalized"
    ]
    .mean()
    .rename(columns={"rating_normalized": "external_mood_score"})
)

# take top 5 recommendations for each algorithm and mood
top5 = (
    recommendations.sort_values(
        ["algorithm_version", "mood_id", "final_score"], ascending=[True, True, False]
    )
    .groupby(["algorithm_version", "mood_id"], as_index=False)
    .head(5)
)

# join with Emotify+ external scores
top5_with_scores = top5.merge(external_scores, on=["track_id", "mood_id"], how="left")

# if no external score exists, count it as 0
top5_with_scores["external_mood_score"] = top5_with_scores[
    "external_mood_score"
].fillna(0)

# compute MoodMatch@5
results = (
    top5_with_scores.groupby(["algorithm_version", "mood_id"], as_index=False)
    .agg(
        mood_match_at_5=("external_mood_score", "mean"),
        avg_final_score_top5=("final_score", "mean"),
        tracks_count=("track_id", "count"),
    )
    .merge(moods, on="mood_id", how="left")
    .sort_values(["algorithm_version", "mood_id"])
)

print(
    results[
        [
            "algorithm_version",
            "mood",
            "mood_match_at_5",
            "avg_final_score_top5",
            "tracks_count",
        ]
    ]
)


overall = (
    results.groupby("algorithm_version", as_index=False)["mood_match_at_5"]
    .mean()
    .rename(columns={"mood_match_at_5": "overall_mood_match_at_5"})
)

print("\nOverall:")
print(overall)
