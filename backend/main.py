from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend import models  # noqa: F401  (registers tables on Base)

from backend.routes.auth import router as auth_router
from backend.routes.ai_trends import router as ai_trends_router
from backend.routes.content import router as content_router
from backend.routes.trending import router as trending_router
from backend.routes.recent_content import router as recent_content_router


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
    allow_origins=["http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://politicaltea-fy2f0rke8-prempandey812743gmailcoms-projects.vercel.app",],
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
DEFAULT_STATES = [
    {"id": 1, "name": "Uttar Pradesh"},
    {"id": 2, "name": "Delhi"},
    {"id": 3, "name": "Maharashtra"},
    {"id": 4, "name": "Rajasthan"},
    {"id": 5, "name": "Bihar"},
    {"id": 6, "name": "Jharkhand"},
    {"id": 7, "name": "Madhya Pradesh"},
    {"id": 8, "name": "West Bengal"},
    {"id": 9, "name": "Tamil Nadu"},
    {"id": 10, "name": "Karnataka"},
    {"id": 11, "name": "Gujarat"},
    {"id": 12, "name": "Haryana"},
]


def seed_states():
    db = Session(bind=engine)

    try:
        for state_data in DEFAULT_STATES:
            existing_state = db.query(State).filter(
                State.id == state_data["id"]
            ).first()

            if not existing_state:
                db.add(
                    State(
                        id=state_data["id"],
                        name=state_data["name"]
                    )
                )

        db.commit()

    finally:
        db.close()


seed_states()

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
