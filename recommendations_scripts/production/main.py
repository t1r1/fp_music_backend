import pandas as pd
import psycopg

DB_DSN = "dbname=music user=t1r1 password=31337 host=localhost port=5432"
TOP_K = 50

# per-mood setup: what we trust more (annotations vs audio) + how we score audio
#
# direction rules:
# - "high": use the normalised feature as-is
# - "low": flip it (1 - x)
# - "mid": prefer the middle (peaks at 0.5). handy when "too slow" and "too fast" both feel wrong
#
# hybrid rule:
# final_score = w_ann * annotation_score + (1 - w_ann) * audio_score
#
# versions change log:
# - v1: quick prototype, starter weights
# - v2: adjusted weights based on the papers we cited
# - v3: tuned "inspired" after listening feedback (it sounded too sad / melancholic)
# - v4: tuned "sad" and "happy" after offline metric calculation and listening feedback. increased annotation weight for "sad". decreased "annotation" weight for "happy"
RUN_TAG = "v4"

MOOD_CONFIG = {
    # 1 happy (amazement / wonder)
    1: {
        "algo_version": f"happy_amazement_hybrid_{RUN_TAG}",
        "W_ANN": 0.65,
        "audio_features": {
            "happiness": (0.45, "high"),
            "energy": (0.30, "high"),
            "tempo": (0.20, "mid"),
            "acousticness": (0.05, "mid"),  # also varies
        },
    },
    # 2 inspired (solemnity) - tuned to feel less sad/melancholic
    2: {
        "algo_version": f"inspired_hybrid_{RUN_TAG}",
        "W_ANN": 0.55,  # let audio pull it away from "sad solemn"
        "audio_features": {
            "happiness": (0.45, "high"),
            "tempo": (0.25, "mid"),
            "energy": (0.20, "mid"),
            "acousticness": (0.10, "mid"),
        },
    },
    # 3 loving (tenderness)
    3: {
        "algo_version": f"loving_tender_hybrid_{RUN_TAG}",
        "W_ANN": 0.70,
        "audio_features": {
            "energy": (0.30, "low"),
            "tempo": (0.20, "mid"),  # low/mid
            "acousticness": (0.30, "high"),
            "happiness": (0.20, "high"),  # high/mid
        },
    },
    # 4 sentimental (nostalgia)
    4: {
        "algo_version": f"sentimental_nostalgia_hybrid_{RUN_TAG}",
        "W_ANN": 0.80,
        "audio_features": {
            "tempo": (0.30, "mid"),
            "energy": (0.30, "mid"),
            "happiness": (0.20, "mid"),  # bittersweet / mixed
            "acousticness": (0.20, "high"),
        },
    },
    # 5 relaxed (calmness)
    5: {
        "algo_version": f"relaxed_calm_hybrid_{RUN_TAG}",
        "W_ANN": 0.55,
        "audio_features": {
            "energy": (0.35, "low"),
            "tempo": (0.30, "low"),
            "acousticness": (0.20, "high"),
            "happiness": (0.15, "high"),  # mid/high
        },
    },
    # 6 strong (power)
    6: {
        "algo_version": f"strong_power_hybrid_{RUN_TAG}",
        "W_ANN": 0.45,
        "audio_features": {
            "energy": (0.45, "high"),
            "tempo": (0.30, "high"),
            "acousticness": (0.15, "low"),
            "happiness": (0.10, "mid"),  # can go either way (aggressive vs triumphant)
        },
    },
    # 7 joy (joyful activation)
    7: {
        "algo_version": f"joy_hybrid_{RUN_TAG}",
        "W_ANN": 0.50,
        "audio_features": {
            "energy": (0.30, "high"),
            "danceability": (0.30, "high"),
            "happiness": (0.20, "high"),
            "tempo": (0.15, "high"),
            "acousticness": (0.05, "low"),  # small nudge away from very acoustic tracks
        },
    },
    # 8 tense (tension)
    8: {
        "algo_version": f"tense_hybrid_{RUN_TAG}",
        "W_ANN": 0.40,
        "audio_features": {
            "energy": (0.40, "high"),
            "tempo": (0.30, "high"),
            "happiness": (0.20, "low"),
            "acousticness": (0.10, "low"),
        },
    },
    # 9 sad (sadness)
    9: {
        "algo_version": f"sad_hybrid_{RUN_TAG}",
        "W_ANN": 0.6,
        "audio_features": {
            "energy": (0.40, "low"),
            "tempo": (0.40, "low"),
            "happiness": (0.1, "low"),
            "acousticness": (0.1, "high"),
        },
    },
}


def minmax(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn)


def transform_direction(x: pd.Series, direction: str) -> pd.Series:
    if direction == "high":
        return x
    if direction == "low":
        return 1.0 - x
    if direction == "mid":
        # peaks at 0.5, fades to 0 at 0 and 1
        return (1.0 - (2.0 * (x - 0.5).abs())).clip(0.0, 1.0)
    raise ValueError(f"unknown direction: {direction}")


def validate_config() -> None:
    for mood_id, cfg in MOOD_CONFIG.items():
        w_ann = float(cfg["W_ANN"])
        if not (0.0 <= w_ann <= 1.0):
            raise ValueError(f"w_ann out of range for mood_id={mood_id}: {w_ann}")

        audio_sum = sum(w for (w, _) in cfg["audio_features"].values())
        if abs(audio_sum - 1.0) > 1e-6:
            raise ValueError(
                f"audio weights must sum to 1.0 for mood_id={mood_id}; got {audio_sum}"
            )


def main() -> None:
    validate_config()

    # decide which audio columns we actually need
    needed_af_cols: set[str] = set()
    for cfg in MOOD_CONFIG.values():
        needed_af_cols.update(cfg["audio_features"].keys())

    with psycopg.connect(DB_DSN) as conn:
        tracks = pd.read_sql(
            "select id as track_id, title, artist, genre from tracks;",
            conn,
        )

        moods = pd.read_sql(
            "select id as mood_id, mood, annotation from moods order by id;",
            conn,
        )

        # pull the annotation columns listed in moods.annotation
        ann_cols = sorted(set(moods["annotation"].tolist()))
        ann_select = ", ".join(["track_id"] + ann_cols)
        ann = pd.read_sql(f"select {ann_select} from annotations;", conn)

        # pull all audio feature columns we need
        af_select = ", ".join(["track_id"] + sorted(needed_af_cols))
        af = pd.read_sql(f"select {af_select} from audio_features;", conn)

    # normalize all audio columns once (so each mood can reuse them)
    af_n = af.copy()
    for feat in sorted(needed_af_cols):
        af_n[f"{feat}_n"] = minmax(af_n[feat])

    with psycopg.connect(DB_DSN) as write_conn:
        with write_conn.cursor() as cur:
            for _, mrow in moods.iterrows():
                mood_id = int(mrow["mood_id"])
                mood_name = str(mrow["mood"])
                ann_col = str(mrow["annotation"])

                if mood_id not in MOOD_CONFIG:
                    print(f"skipping mood_id={mood_id} ({mood_name}) - no config found")
                    continue

                cfg = MOOD_CONFIG[mood_id]
                algo_version = cfg["algo_version"]
                w_ann = float(cfg["W_ANN"])
                w_aud = 1.0 - w_ann

                # annotation_score: average of the annotation column per track
                ann_score = ann.groupby("track_id", as_index=False).agg(
                    annotation_score=(ann_col, "mean")
                )

                # audio_score: weighted sum of chosen features (after direction transform)
                score = pd.Series(0.0, index=af_n.index)
                for feat, (w, direction) in cfg["audio_features"].items():
                    x = af_n[f"{feat}_n"]
                    score = score + float(w) * transform_direction(x, direction)

                audio_score = af_n[["track_id"]].copy()
                audio_score["audio_score"] = score

                # merge (keep only tracks that have audio features)
                df = tracks.merge(audio_score, on="track_id", how="inner").merge(
                    ann_score, on="track_id", how="left"
                )
                df["annotation_score"] = df["annotation_score"].fillna(0.0)

                # final hybrid score
                df["final_score"] = (
                    w_ann * df["annotation_score"] + w_aud * df["audio_score"]
                )

                # top k results
                recs = df.sort_values("final_score", ascending=False).head(TOP_K).copy()

                out = recs[
                    ["track_id", "audio_score", "annotation_score", "final_score"]
                ].copy()
                out["mood_id"] = mood_id
                out["algorithm_version"] = algo_version

                # save per mood (handy for debugging + report screenshots)
                out_file = f"recommendations_{mood_name}.csv"
                out.to_csv(out_file, index=False)
                print(f"saved: {out_file} | mood_id={mood_id} | algo={algo_version}")

                # clear previous rows for this mood/version, then insert fresh ones
                cur.execute(
                    "delete from recommendations where mood_id = %s and algorithm_version = %s;",
                    (mood_id, algo_version),
                )

                for _, row in out.iterrows():
                    cur.execute(
                        """
                        insert into recommendations
                            (track_id, mood_id, audio_score, annotation_score, final_score, algorithm_version)
                        values
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

            write_conn.commit()

    print("inserted recos for all configured moods")


if __name__ == "__main__":
    main()
