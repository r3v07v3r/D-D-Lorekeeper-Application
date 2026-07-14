"""Login/logout for the local profile-select screen.

POST /auth/login is the only place a client-supplied user_id is trusted: it
is how the user identifies *themselves* at the point of login (there is no
password - see project spec Section 3, this is a single-machine app). From
that point on, the resulting token - not the user_id - is what every other
endpoint uses to establish identity and role.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, get_session_store
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such user")

    store = get_session_store(request)
    session = store.create(user_id=user.id, username=user.username, role=user.role)
    return LoginResponse(token=session.token, user=UserPublic.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, current: SessionRecord = Depends(get_current_user)) -> None:
    store = get_session_store(request)
    store.delete(current.token)


@router.get("/me", response_model=UserPublic)
def me(db: Session = Depends(get_db), current: SessionRecord = Depends(get_current_user)) -> UserPublic:
    user = db.get(User, current.user_id)
    if user is None:
        # The user backing this session was deleted after the token was issued.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User no longer exists")
    return UserPublic.model_validate(user)
