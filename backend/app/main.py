from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, UserRole
from app.auth import hash_password
from app.routers import auth, items, pending

app = FastAPI(title="Shop Inventory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend's exact domain once deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(pending.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    # Seed a first admin account if none exists yet, so there's always a way in.
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == UserRole.admin).first():
            admin = User(
                username=settings.first_admin_username,
                email=settings.first_admin_email,
                password_hash=hash_password(settings.first_admin_password),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
