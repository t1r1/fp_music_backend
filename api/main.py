import logging
import os
from fastapi import FastAPI
from typing import Optional, List, Annotated
from fastapi import Query
from enum import Enum, auto

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from api.sessions import set_session_id, SessionID
from api.models import (
    ListMoodsResponse,
    RecommendationsResponse,
    EvaluationResponse,
    EvaluationRequest,
)
from api.db import (
    fetch_moods,
    fetch_recommended_tracks,
    insert_or_update_evaluation,
    fetch_evaluations,
)


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)

app = FastAPI(root_path="/api")

# serve everything in ./media under /media in dev mode
if os.path.exists("media"):
    app.mount("/media", StaticFiles(directory="media"), name="media")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BaseHTTPMiddleware, dispatch=set_session_id)


class AlgoVersion(Enum):
    v2 = "v2"
    v3 = "v3"
    v4 = "v4"


@app.get("/moods")
async def list_moods() -> ListMoodsResponse:
    moods = fetch_moods()
    return ListMoodsResponse(moods=moods)


@app.get("/recommendations/{mood_id}")
async def list_tracks(
    sid: SessionID,
    mood_id: int,
    genre: Optional[List[str]] = Query(default=None),
    algo: Annotated[AlgoVersion, Query()] = AlgoVersion.v4,
) -> RecommendationsResponse:
    tracks = fetch_recommended_tracks(mood_id, algo.value, genre, sid)
    return RecommendationsResponse(mood_id=mood_id, tracks=tracks)


@app.post("/evaluations")
async def create_evaluation(
    sid: SessionID, body: EvaluationRequest
) -> EvaluationResponse:
    result = insert_or_update_evaluation(sid, body.recommendation_id, body.liked)
    print(result)
    return result


@app.get("/evaluations", response_model=List[EvaluationResponse])
async def list_evaluations(sid: SessionID) -> list[EvaluationResponse]:
    rows = fetch_evaluations(sid)
    return rows
