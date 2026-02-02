import logging
from uuid import uuid4
from typing import Annotated
from fastapi.requests import Request
from fastapi import Depends

SESSION_ID_COOKIE = "__mood_music_session_id"


async def set_session_id(request: Request, call_next):
    session_id_changed = False
    session_id = request.cookies.get(SESSION_ID_COOKIE)

    if session_id is None:
        session_id = str(uuid4())
        session_id_changed = True
        logging.debug("created new session_id '%s'", session_id)
    else:
        logging.debug("using existing session '%s'", session_id)

    request.state.session_id = session_id

    response = await call_next(request)

    if session_id_changed:
        logging.debug("setting session_id cookie to '%s'", session_id)
        response.set_cookie(SESSION_ID_COOKIE, session_id)

    return response


async def get_session_id(request: Request) -> str:
    return request.state.session_id


SessionID = Annotated[str, Depends(get_session_id)]
