from fastapi import FastAPI, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import random
from passlib.context import CryptContext

Base = declarative_base()
app = FastAPI()

DATABASE_URL = "postgresql+psycopg2://postgres:virat@localhost:5432/classdata"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

def get_db_data():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= Register Table ==================
class Register(Base):
    __tablename__ = "UserRegister"
    user_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    otp = Column(Integer, nullable=True)



class RegisterA(BaseModel):
    name: str
    email: EmailStr
    password: str

@app.post("/register")
def Add_user(user_in: RegisterA, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=404, detail=f"User {user_in.email} already exists")
    user = Register(name=user_in.name, email=user_in.email, password=user_in.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"Message": "Your register successfully", "success": True, "Status_Code": 200, "user": user}

class GetData(BaseModel):
    user_id: int
    name: str
    email: str
    password: str
    class Config:
        orm_mode = True

@app.get("/get_all", response_model=List[GetData])
def get_data(db: Session = Depends(get_db_data)):
    user_get = db.query(Register).all()
    if not user_get:
        raise HTTPException(status_code=404, detail="No data found")
    return user_get

class RegisterB(BaseModel):
    email: str
    password: str

@app.post("/login", response_model=GetData)
def loding_data(user_in: RegisterB, db: Session = Depends(get_db_data)):
    user_email = db.query(Register).filter(Register.email == user_in.email, Register.password == user_in.password).first()
    if not user_email:
        raise HTTPException(status_code=404, detail="Invalid email or password")
    return user_email

class Change_password(BaseModel):
    new_password: str
    old_password: str

@app.patch("/update/{user_id}")
def chnage_password(user_id: int, data: Change_password, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Old password not match")
    user.password = data.new_password
    db.commit()
    db.refresh(user)
    return user



otp_store = {}

@app.post("/sendotp/{user_id}")
def send_otp(user_id: int, db: Session = Depends(get_db_data)):
    user = db.query(Register).filter(Register.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User_id not match")
    otp = random.randint(1000, 9999)
    user.otp= otp
    otp_store[user_id] = otp
    db.commit()
    return {"message": "OTP sent successfully", "otp_send": otp}

class Forget(BaseModel):
    otp: int
    new_password: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    class Config:
        orm_mode = True

@app.patch("/forget/{user_id}", response_model=UserResponse)
def forget_password(user_id: int, data: Forget, db: Session = Depends(get_db_data)):
    db_user = db.query(Register).filter(Register.user_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.otp!= data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    db_user.password = data.new_password
    db_user.otp = None
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/user_get_id/{user_id}", response_model=GetData)
def get_otp(user_id: int, db: Session = Depends(get_db_data)):
    user_get = db.query(Register).filter(Register.user_id == user_id).first()
    if not user_get:
        raise HTTPException(status_code=404, detail="User_id not match")
    return user_get

# ================== PostUser ===================
class PostUser(Base):
    __tablename__ = "PostUser"
    post_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(1000), nullable=False)
    content = Column(String(500), nullable=False)

class Post(BaseModel):
    user_id: int
    title: str
    content: str

class Getpost(BaseModel):
    user_id: int
    post_id: int
    title: str
    content: str
    class Config:
        orm_mode = True

@app.post("/postuser/")
def postuser(post_in: Post, db: Session = Depends(get_db_data)):
    post_user = db.query(Register).filter(Register.user_id == post_in.user_id).first()
    if not post_user:
        raise HTTPException(status_code=404, detail="User_id not match")
    user_post = PostUser(user_id=post_in.user_id, title=post_in.title, content=post_in.content)
    db.add(user_post)
    db.commit()
    db.refresh(user_post)
    return {"success": True, "message": "Post added successfully", "data": user_post}

@app.get("/getallpost", response_model=List[Getpost])
def get_all_post(db: Session = Depends(get_db_data)):
    get_post = db.query(PostUser).all()
    if not get_post:
        raise HTTPException(status_code=404, detail="No posts found")
    return get_post

@app.get("/usergetbyid/{user_id}", response_model=Getpost)
def get_by_id(user_id: int, db: Session = Depends(get_db_data)):
    get_id = db.query(PostUser).filter(PostUser.user_id == user_id).first()
    if not get_id:
        raise HTTPException(status_code=404, detail="User_id not match")
    return get_id

@app.get("/getbyuserid/{post_id}")
def getuserid(post_id: int, db: Session = Depends(get_db_data)):
    user_id = db.query(PostUser).filter(PostUser.post_id == post_id).first()
    if not user_id:
        raise HTTPException(status_code=404, detail="Post_id not found")
    return {"success": True, "message": "Post found successfully", "data": user_id}

# ================== Follow ===================
class Follow(Base):
    __tablename__ = "FollowUser"
    follow_id = Column(Integer, primary_key=True)
    follow_by = Column(Integer, nullable=False)
    follow_to = Column(Integer, nullable=False)

class Follower(BaseModel):
    follow_by: int
    follow_to: int

@app.post("/followuser")
def add_follow(follow_in: Follower, db: Session = Depends(get_db_data)):
    follow_user = db.query(Register).filter(Register.user_id == follow_in.follow_by).first()
    follow_users = db.query(Register).filter(Register.user_id == follow_in.follow_to).first()
    if not follow_user or not follow_users:
        raise HTTPException(status_code=404, detail="User not found")
    Getfollow = db.query(Follow).filter(Follow.follow_by == follow_in.follow_by, Follow.follow_to == follow_in.follow_to).first()
    if Getfollow:
        raise HTTPException(status_code=404, detail="Already following")
    folow = Follow(follow_by=follow_in.follow_by, follow_to=follow_in.follow_to)
    db.add(folow)
    db.commit()
    db.refresh(folow)
    return {"success": True, "message": "Followed successfully", "data": folow}

@app.delete("/unfollow")
def unfollow_user(data: Follower, db: Session = Depends(get_db_data)):
    follow_record = db.query(Follow).filter(Follow.follow_by == data.follow_by, Follow.follow_to == data.follow_to).first()
    if not follow_record:
        raise HTTPException(status_code=404, detail="Follow record not found")
    db.delete(follow_record)
    db.commit()
    return {"message": f"User {data.follow_by} unfollowed User {data.follow_to}"}

# ================== Block ===================
class BlockUser(Base):
    __tablename__ = "BlockUser"
    block_id = Column(Integer, primary_key=True)
    block_by = Column(Integer, nullable=False)
    block_to = Column(Integer, nullable=False)

class Block(BaseModel):
    block_by: int
    block_to: int

@app.post("/user")
def add_block(block_in: Block, db: Session = Depends(get_db_data)):
    block_user = db.query(Register).filter(Register.user_id == block_in.block_by).first()
    block_users = db.query(Register).filter(Register.user_id == block_in.block_to).first()
    if not block_user or not block_users:
        raise HTTPException(status_code=404, detail="User not found")
    Get = db.query(BlockUser).filter(BlockUser.block_by == block_in.block_by, BlockUser.block_to == block_in.block_to).first()
    if Get:
        raise HTTPException(status_code=404, detail="Already blocked")
    block = BlockUser(block_by=block_in.block_by, block_to=block_in.block_to)
    db.add(block)
    db.commit()
    db.refresh(block)
    return {"success": True, "message": "Blocked successfully", "data": block}

@app.delete("/un")
def unblock_user(data: Block, db: Session = Depends(get_db_data)):
    block_record = db.query(BlockUser).filter(BlockUser.block_by == data.block_by, BlockUser.block_to == data.block_to).first()
    if not block_record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(block_record)
    db.commit()
    return {"message": f"User {data.block_by} unblocked User {data.block_to}"}

# ================== Like ===================
class LikeUser(Base):
    __tablename__ = "LikeUser"
    like_id = Column(Integer, primary_key=True)
    like_by = Column(Integer, nullable=False)
    like_to = Column(Integer, nullable=False)

class Like(BaseModel):
    like_by: int
    like_to: int

@app.post("/likeuser")
def add_like(like_in: Like, db: Session = Depends(get_db_data)):
    like_user = db.query(Register).filter(Register.user_id == like_in.like_by).first()
    like_users = db.query(Register).filter(Register.user_id == like_in.like_to).first()
    if not like_user or not like_users:
        raise HTTPException(status_code=404, detail="User not found")
    LikeGet = db.query(LikeUser).filter(LikeUser.like_by == like_in.like_by, LikeUser.like_to == like_in.like_to).first()
    if LikeGet:
        raise HTTPException(status_code=404, detail="Already liked")
    like = LikeUser(like_by=like_in.like_by, like_to=like_in.like_to)
    db.add(like)
    db.commit()
    db.refresh(like)
    return {"success": True, "message": "Liked successfully", "data": like}

@app.delete("/unlike")
def unlike_user(data: Like, db: Session = Depends(get_db_data)):
    like_record = db.query(LikeUser).filter(LikeUser.like_by == data.like_by, LikeUser.like_to == data.like_to).first()
    if not like_record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(like_record)
    db.commit()
    return {"message": f"User {data.like_by} disliked User {data.like_to}"}


#========================otp================
class Otp(Base):
    _tablename_ = "otpdata"
    id = Column(Integer, primary_key=True)
    email=Column(String(),nullable=False)
    otp=Column(Integer,nullable=False)



#OTP

class OTP(BaseModel):
    email: str

class ResetPassword(BaseModel):
    email:str
    otp: int
    password: str



#====================== hash password ===================

@app.post("/useradd",response_model=GetData) 
def add_person(user_in:RegisterA,db:Session=Depends(get_db_data)) :
    user=db.query(Register).filter(Register.email==user_in.email).first()
    
    if  user:
        raise HTTPException (status_code=404,detail="you are already exist in this.")
    user_password=hash_password(user_in.password)
    register=Register(
        name=user_in.name,
        email=user_in.email,
        password=user_password
    )
        
    db.add(register)
    db.commit()
    db.refresh(register)
    return register      
cont_password=CryptContext(schemes=("bcrypt"))
def hash_password(plan_password:str):
    return cont_password.hash(plan_password)