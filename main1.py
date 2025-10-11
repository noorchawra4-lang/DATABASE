from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ------------------- DATABASE SETUP -------------------
Base = declarative_base()
DATABASE_URL = "postgresql+psycopg2://postgres:virat@localhost:5432/classdata"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------- MODELS -------------------
class Register(Base):
    __tablename__ = "UserRegister"
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password = Column(String(100), nullable=False)

# ------------------- SCHEMAS -------------------
class Signup(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class ResponseModel(BaseModel):
    success: bool
    status: int
    msg: str
    model_config = {"from_attributes": True}

class GetData(BaseModel):
    user_id: int
    name: str
    email: str
    model_config = {"from_attributes": True}

class UpdateUser(BaseModel):
    name: str
    email: EmailStr
    new_password: str
    model_config = {"from_attributes": True}

# ------------------- USER ROUTES -------------------
#1
@app.post("/register", response_model=GetData)
def register_user(user_in: Signup, db: Session = Depends(get_db)):
    user = db.query(Register).filter(Register.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail=f"User with email '{user_in.email}' already exists")
    
    new_user = Register(name=user_in.name, email=user_in.email, password=user_in.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
#2
@app.get("/get_all", response_model=List[GetData])
def get_all(db: Session = Depends(get_db)):
    users = db.query(Register).all()
    return users
#3
@app.post("/login")
def login(user: LoginSchema, db: Session = Depends(get_db)):
    db_user = db.query(Register).filter(Register.email == user.email, Register.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "status": 200, "msg": "Login successful", "data": GetData.from_orm(db_user)}

#4
@app.put("/update/{user_id}")
def update_user(user_id: int, user: UpdateUser, db: Session = Depends(get_db)):
    # Fetch user from DB
    db_user = db.query(Register).filter(Register.user_id == user_id).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    
    db_user["name"] = user.name
    db_user["email"] = user.email
    db_user["password"] = user.new_password

    db.commit()
    db.refresh(db_user)

    return {
        "success": True,
        "status": 200,
        "msg": "User updated successfully",
        "data": {
            "user_id": db_user.user_id,
            "name": db_user.name,
            "email": db_user.email
        }
    }
#5
@app.get("/user_get_id/{user_id}")
def get_user_by_user_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(Register).filter(Register.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User ID not found")
    return {"success": True, "status": 200, "msg": "User retrieved successfully", "data": GetData.from_orm(user)}
