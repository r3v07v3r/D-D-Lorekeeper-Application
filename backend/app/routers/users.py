"""User registry for the profile-select login screen.

GET /users has no session-token requirement (there's no token to have yet at
this point in the flow), but it - like POST /users and POST /auth/login - is
still gated by require_network_access: now that the backend can be reached
from other machines on a LAN (not just the GM's own PC), "no token required"
must not mean "no gate at all". See app.auth.require_network_access.

POST /users (registering a new player/GM profile) has one special case: the
very first account (bootstrapping the GM on first run) is allowed without a
session token, since no session can exist yet - but still requires passing
require_network_access, which restricts that bootstrap window to the GM's
own machine until a passphrase is set. Once a GM account exists, creating
further accounts additionally requires an authenticated GM session.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, get_session_store, require_network_access
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic], dependencies=[Depends(require_network_access)])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.get("/presence")
def get_presence(
    request: Request,
    db: Session = Depends(get_db),
    _current: SessionRecord = Depends(get_current_user),
) -> dict[int, bool]:
    """Which users currently have a live Lorekeeper session - see
    SessionStore.connected_user_ids(). This is app-level connectivity, not
    Discord voice presence (there is no bot-side hook for that yet), and
    powers the sidebar's grey/lit party avatars.
    """
    connected = get_session_store(request).connected_user_ids()
    return {user.id: user.id in connected for user in db.query(User).all()}


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_network_access)],
)
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
