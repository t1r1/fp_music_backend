from tinytag import TinyTag
import os
import csv

genres = [
    "classical",
    "rock",
    "electronic",
    "pop",
]

with open("metadata.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "genre", "title", "artist"])

    for genre in genres:
        path = os.path.join("../emotifymusic", genre)
        print(path)
        for filename in os.listdir(path):
            full_filename = os.path.join(path, filename)
            track_number = filename.split(".")[0]
            tag = TinyTag.get(full_filename)
            writer.writerow([int(track_number), genre, tag.title, tag.artist])
