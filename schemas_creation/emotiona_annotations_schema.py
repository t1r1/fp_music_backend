# CREATE TABLE emotional_annotations (
#     id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
#     track_id INT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
#     mapped_mood_id INT NOT NULL REFERENCES moods(id),
#     raw_feeling VARCHAR(30) NOT NULL,
#     user_id INT NOT NULL,
#     gender VARCHAR(10),
#     rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
#     rating_normalized DOUBLE PRECISION GENERATED ALWAYS AS (rating::DOUBLE PRECISION / 5.0) STORED,

#     UNIQUE (track_id, user_id, raw_feeling)
# );

# CREATE INDEX idx_emotional_annotations_track_id
#     ON emotional_annotations(track_id);

# CREATE INDEX idx_emotional_annotations_mapped_mood_id
#     ON emotional_annotations(mapped_mood_id);

# CREATE INDEX idx_emotional_annotations_track_mood
#     ON emotional_annotations(track_id, mapped_mood_id);


# ALTER TABLE emotional_annotations
# DROP CONSTRAINT emotional_annotations_rating_check;

# ALTER TABLE emotional_annotations
# ADD CONSTRAINT emotional_annotations_rating_check
# CHECK (rating BETWEEN 0 AND 5);
