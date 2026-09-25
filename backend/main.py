from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend import models  # noqa: F401  (registers tables on Base)

from backend.routes.auth import router as auth_router
from backend.routes.ai_trends import router as ai_trends_router
from backend.routes.content import router as content_router
from backend.routes.trending import router as trending_router
from backend.routes.recent_content import router as recent_content_router
from backend.database import SessionLocal
from backend.models import State

DEFAULT_STATES = [
    (1, "Uttar Pradesh"),
    (2, "Delhi"),
    (3, "Maharashtra"),
    (4, "Rajasthan"),
    (5, "Bihar"),
    (6, "Jharkhand"),
    (7, "Madhya Pradesh"),
    (8, "West Bengal"),
    (9, "Tamil Nadu"),
    (10, "Karnataka"),
    (11, "Gujarat"),
    (12, "Haryana"),
]

def seed_states():
    db = SessionLocal()
    try:
        for state_id, name in DEFAULT_STATES:
            exists = db.query(State).filter(
                State.id == state_id
            ).first()

            if not exists:
                db.add(State(id=state_id, name=name))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

app = FastAPI(
    title="Political Tea API",
    description=(
        "State-wise political news and public voice platform"
    ),
    version="1.0.0",
)


Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://politicaltea-fy2f0rke8-prempandey812743gmailcoms-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# ROUTES
# =========================================

app.include_router(auth_router)
app.include_router(ai_trends_router)
app.include_router(content_router)
app.include_router(trending_router)
app.include_router(recent_content_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
