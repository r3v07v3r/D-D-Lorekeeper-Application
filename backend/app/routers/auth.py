"""Login/logout for the profile-select screen.

POST /auth/login is the only place a client-supplied user_id is trusted: it
is how the user identifies *themselves* at the point of login (there is no
per-user password - see project spec Section 3). From that point on, the
resulting token - not the user_id - is what every other endpoint uses to
establish identity and role.

Now that the backend can be reached from other machines on a LAN (players
connecting to the GM's instance), trusting a bare user_id with no further
check would let anyone who can reach the port log in as anyone. That gap is
closed by require_network_access: a campaign passphrase (set by the GM in
Settings) gates this endpoint once the backend is reachable beyond the GM's
own machine - see app.auth for the full reasoning.
"""
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import SessionRecord, get_current_user, get_session_store, require_network_access
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(require_network_access)])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such user")

    store = get_session_store(request)
    session = store.create(user_id=user.id, username=user.username, role=user.role)
    return LoginResponse(token=session.token, user=UserPublic.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current: SessionRecord = Depends(get_current_user),
) -> None:
    store = get_session_store(request)
    record = store.delete(current.token)
    if record is not None:
        # Checkpoints this session's connected time onto the user's running
        # total (see User.total_seconds_active) - a session that never
        # cleanly logs out (app crash, force-quit) simply doesn't get this
        # checkpoint, the same acceptable v1 limitation as other
        # best-effort-on-clean-shutdown behavior in this app.
        user = db.get(User, record.user_id)
        if user is not None:
            elapsed = max(0.0, time.monotonic() - record.created_at)
            user.total_seconds_active += round(elapsed)
            db.commit()


@router.get("/me", response_model=UserPublic)
def me(db: Session = Depends(get_db), current: SessionRecord = Depends(get_current_user)) -> UserPublic:
    user = db.get(User, current.user_id)
    if user is None:
        # The user backing this session was deleted after the token was issued.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User no longer exists")
    return UserPublic.model_validate(user)
