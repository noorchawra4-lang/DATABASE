from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import random
from passlib.context import CryptContext

# ================ Base setup ================
Base = declarative_base()
app = FastAPI()

DATABASE_URL = "postgresql+psycopg2://postgres:virat@localhost:5432/classdata"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

def get_db_data():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================ Models ================
class Register(Base):
    __tablename__ = "UserRegister"
    user_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    otp = Column(Integer, nullable=True)


# ================ Schemas ================
class RegisterA(BaseModel):
    name: str
    email: EmailStr
    password: str

class RegisterB(BaseModel):
    email: EmailStr
    password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class Forget(BaseModel):
    otp: int
    new_password: str

class OTP(BaseModel):
    email: EmailStr

class GetData(BaseModel):
    user_id: int
    name: str
    email: str
    class Config:
        orm_mode = True


# ================ Hash helpers ================
def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ================ Register ===================
@app.post("/register", response_model=GetData)
def add_user(user_in: RegisterA, db: Session = Depends(get_db_data)):
    existing = db.query(Register).filter(Register.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_pwd = hash_password(user_in.password)
    new_user = Register(name=user_in.name, email=user_in.email, password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ================ Login ======================
@app.post("/login", response_model=GetData)
def login_user(data: RegisterB, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid email or password")
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    return user


# ================ Change Password ==================
@app.patch("/update/{user_id}")
def update_password(user_id: int, data: ChangePassword, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Old password incorrect")

    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)
    return {"message": "Password updated successfully"}


# ================ Send OTP ==================
@app.post("/sendotp")
def send_otp(data: OTP, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    otp_value = random.randint(1000, 9999)
    user.otp = otp_value
    db.commit()
    return {"message": "OTP generated successfully", "otp": otp_value}  # (For testing only)


# ================ Forget / Reset Password ==================
@app.patch("/forget/{email}")
def forget_password(email: str, data: Forget, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.password = hash_password(data.new_password)
    user.otp = None
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successfully"}


# ================ Get All Users ==================
@app.get("/get_all", response_model=List[GetData])
def get_all_users(db: Session = Depends(get_db_data)):
    users = db.query(Register).all()
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    return users


# ================ Get By ID ==================
@app.get("/user/{user_id}", response_model=GetData)
def get_user_by_id(user_id: int, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
