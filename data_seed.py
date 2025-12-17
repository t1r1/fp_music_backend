import os
import csv
import psycopg
import pandas as pd

# INSERT INTO color (color_id, color_name)
# VALUES (2, 'Green');

with psycopg.connect(
    "dbname=music user=t1r1 password=31337 host=localhost port=5432"
) as conn:
    with conn.cursor() as cur:
        with open("metadata.csv") as f:
            reader = csv.DictReader(f)

            for item in reader:
                print(f'{item["genre"]}_{item["id"]}')

                cur.execute(
                    "INSERT INTO Tracks (emotify_id, title, artist, genre) VALUES (%s, %s, %s, %s)",
                    (
                        f'{item["genre"]}_{item["id"]}',
                        item["title"],
                        item["artist"],
                        item["genre"],
                    ),
                )


# df = pd.read_csv("annotations.csv")
# df.columns = df.columns.str.strip()  # optional, cleans " gender" -> "gender"

# df["track id"] = pd.to_numeric(df["track id"], errors="raise")
# df["track id"] = ((df["track id"] - 1) % 100) + 1

# df.to_csv("annotations_updated2.csv", index=False)


with psycopg.connect(
    "dbname=music user=t1r1 password=31337 host=localhost port=5432"
) as conn:
    with conn.cursor() as cur:
        with open("annotations_updated2.csv") as f:
            reader = csv.DictReader(f)

            for item in reader:
                # print(item)
                genre = item["genre"]
                emotify_id = f'{genre}_{item["track id"]}'
                print(item["track id"])
                # print(emotify_id)
                amazement = item["amazement"]
                solemnity = item["solemnity"]
                tenderness = item["tenderness"]
                nostalgia = item["nostalgia"]
                calmness = item["calmness"]
                power = item["power"]
                joyful_activation = item["joyful_activation"]
                tension = item["tension"]
                sadness = item["sadness"]
                mood = item["mood"]

                cur.execute("SELECT * FROM Tracks WHERE emotify_id = %s", (emotify_id,))
                row_result = cur.fetchone()
                print(row_result)
                track_id = row_result[0]

                cur.execute(
                    "Insert into Annotations (track_id, amazement, solemnity, tenderness, nostalgia, calmness, power, joyful_activation, tension, sadness, mood, genre) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
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
                        genre,
                    ),
                )


# create table Tracks (
# id int generated always as identity,
# title varchar(255) not null,
# artist varchar (100) not null,
# genre varchar (25) not null,
# emotify_id varchar(25) not null,
# primary key(id)
# );


# create table Audio_Features (
# id int generated always as identity,
# primary key(id),
# track_id int references Tracks(id),
# energy int,
# happiness int,
# liveness int,
# danceability int,
# acousticness int,
# tempo int
# );


# create table Moods (
#     id int generated always as identity,
# primary key(id),
# mood varchar(50),
# annotation varchar(50)
# );

# create table Recommendations (
# id int generated always as identity,
# primary key(id),
# track_id int references Tracks(id),
# mood_id int references Moods(id),
#   annotation_score DOUBLE PRECISION NOT NULL,
#   audio_score DOUBLE PRECISION NOT NULL,
#   final_score DOUBLE PRECISION NOT NULL,
#   algorithm_version int
# );


# create table Annotations (
# id int generated always as identity,
# primary key(id),
# track_id int references Tracks(id),
# amazement int,
# solemnity int,
# tenderness int,
# nostalgia int,
# calmness int,
# power int,
# joyful_activation int,
# tension int,
# sadness int,
# mood int,
# genre varchar(25)
# );
