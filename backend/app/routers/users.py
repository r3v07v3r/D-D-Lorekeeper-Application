"""User registry for the profile-select login screen.

GET /users is intentionally unauthenticated: the profile-select screen needs
to list registered users *before* anyone has a session token. It only
exposes username/role/id, not anything sensitive, so this is safe.

POST /users (registering a new player/GM profile) has one special case: the
very first account (bootstrapping the GM on first run) is allowed without a
token, since no session can exist yet. Once a GM account exists, creating
further accounts requires an authenticated GM session.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_session_store
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    gm_exists = db.query(User).filter(User.role == "gm").first() is not None

    if gm_exists:
        # No more unauthenticated bootstrapping once a GM is registered -
        # require a valid GM session token for every subsequent account.
        token = authorization.split(" ", 1)[1].strip() if authorization and " " in authorization else None
        session = get_session_store(request).get(token) if token else None
        if session is None or session.role != "gm":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A GM already exists - only an authenticated GM can register new accounts",
            )

    if db.query(User).filter(User.username == payload.username).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        username=payload.username,
        role=payload.role,
        discord_id=payload.discord_id,
        dnd_beyond_character_id=payload.dnd_beyond_character_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
