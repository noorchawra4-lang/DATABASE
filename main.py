# main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# -------------------- Database URL --------------------

DATABASE_URL = "postgresql+psycopg2://postgres:virat@localhost:5432/classdata"


# -------------------- SQLAlchemy Setup --------------------
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# -------------------- Models --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, nullable=False)


# -------------------- Schema -----------------------
class UserSchema(BaseModel):
    name: str
    email: str

class get_user (BaseModel):
    id : int
    name:str
    email: str



# -------------------- FastAPI App --------------------
app = FastAPI()


# -------------------- Create Tables on Startup --------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# -------------------- DB Dependency --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Routes --------------------
@app.post("/user")
def add_user(userData: UserSchema, db: Session = Depends(get_db)):
   
    existing_user = db.query(User).filter(User.email == userData.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=f"Email {userData.email} already exists")

    new_user = User(name=userData.name, email=userData.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "name": new_user.name, "email": new_user.email}

@app.get("/user")
def get_users(db: Session = Depends(get_db)):
    users = db.query(get_user).all()
    return users



