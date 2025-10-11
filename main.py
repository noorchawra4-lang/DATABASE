from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Body
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, DateTime, or_, and_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------- Configuration ----------------
DATABASE_URL = "postgresql+psycopg2://postgres:virat@localhost:5432/classdata"

# ---------------- Database setup ----------------
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------- Models ----------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False) 
    title = Column(String(300), nullable=True)
    content = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True)
    followed_by = Column(Integer, nullable=False)  
    followed_to = Column(Integer, nullable=False)  
    created_at = Column(DateTime, default=datetime.utcnow)

class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True)
    block_by = Column(Integer, nullable=False)
    block_to = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    post_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ---------------- Schemas ----------------
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    class Config:
        orm_mode = True

class PostCreate(BaseModel):
    userId: int
    title: Optional[str] = None
    content: Optional[str] = None

class PostRead(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    content: Optional[str]
    created_at: datetime
    class Config:
        orm_mode = True

class FollowSchema(BaseModel):
    followed_by: int
    followed_to: int

class BlockSchema(BaseModel):
    block_by: int
    block_to: int

class LikeSchema(BaseModel):
    userId: int

class ResetPasswordSchema(BaseModel):
    email: EmailStr
    new_password: str

class ChangePasswordSchema(BaseModel):
    email: EmailStr
    new_password: str

# ---------------- App ----------------
app = FastAPI(title="Simple Instagram-like API")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# ---------------- DB dependency ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Helper functions ----------------
def user_exists(db: Session, user_id: int) -> bool:
    return db.query(User).filter(User.id == user_id).first() is not None

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

# ---------------- 1. Signup ----------------
@app.post("/signup")
def register(user: UserSignup, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(username=user.username, email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "status": 200, "msg": "User signed up", "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}}

# ---------------- 2. Login ----------------
@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    u = get_user_by_email(db, data.email)
    if not u:
        return {"success": False, "status": 404, "msg": "User not found"}
    if u["password"] != data.password:
        return {"success": False, "status": 401, "msg": "Incorrect password"}
    return {"success": True, "status": 200, "msg": "Login successful", "user": {"id": u.id, "username": u.username, "email": u.email}}

# ---------------- 3. Reset password ----------------
@app.post("/password/reset")
def reset_password(data: ResetPasswordSchema, db: Session = Depends(get_db)):
    u = get_user_by_email(db, data.email)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u["password"] = data.new_password
    db.add(u)
    db.commit()
    return {"success": True, "status": 200, "msg": "Password reset successful"}

# ---------------- 4. Change password ----------------
@app.post("/password/change")
def change_password(data: ChangePasswordSchema, db: Session = Depends(get_db)):
    u = get_user_by_email(db, data.email)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u["password"] = data.new_password
    db.add(u)
    db.commit()
    return {"success": True, "status": 200, "msg": "Password changed successfully"}

# ---------------- 5. Get all users ----------------
@app.get("/users", response_model=List[UserRead])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# ---------------- 6. Get user by id ----------------
@app.get("/users/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "status": 200, "user": {"id": u.id, "username": u.username, "email": u.email}}

# ---------------- 7. Create post ----------------
@app.post("/posts/")
def create_post(postIn: PostCreate, db: Session = Depends(get_db)):
    if not user_exists(db, postIn.userId):
        raise HTTPException(status_code=404, detail="User not found")
    new_post = Post(user_id=postIn.userId, title=postIn.title, content=postIn.content)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {"success": True, "status": 200, "msg": "Post created", "post": {"postId": new_post.id, "userId": new_post.user_id, "title": new_post.title, "content": new_post.content}}

# ---------------- 8. Get post by id ----------------
@app.get("/posts/{post_id}")
def get_post_by_id(post_id: int, db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True, "status": 200, "post": {"postId": p.id, "userId": p.user_id, "title": p.title, "content": p.content}}

# ---------------- 9. Get posts by user id ----------------
@app.get("/users/{user_id}/posts")
def get_posts_by_user(user_id: int, db: Session = Depends(get_db)):
    if not user_exists(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    posts = db.query(Post).filter(Post.user_id == user_id).order_by(Post.created_at.desc()).all()
    results = [{"postId": p.id, "userId": p.user_id, "title": p.title, "content": p.content} for p in posts]
    return {"success": True, "status": 200, "userId": user_id, "count": len(results), "posts": results}

# ---------------- 10. Follow ----------------
@app.post("/follow")
def follow_user(data: FollowSchema, db: Session = Depends(get_db)):
    if data.followed_by == data.followed_to:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    if not user_exists(db, data.followed_by) or not user_exists(db, data.followed_to):
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Follow).filter(Follow.followed_by == data.followed_by, Follow.followed_to == data.followed_to).first()
    if existing:
        return {"success": True, "status": 200, "msg": "You are already following this user."}
    block_exists = db.query(Block).filter(
        or_(
            and_(Block.block_by == data.followed_by, Block.block_to == data.followed_to),
            and_(Block.block_by == data.followed_to, Block.block_to == data.followed_by)
        )
    ).first()
    if block_exists:
        raise HTTPException(status_code=400, detail="Cannot follow due to block")
    new_follow = Follow(followed_by=data.followed_by, followed_to=data.followed_to)
    db.add(new_follow)
    db.commit()
    return {"success": True, "status": 200, "msg": "User FOLLOWED successfully."}

# ---------------- 11. Unfollow ----------------
@app.post("/unfollow")
def unfollow_user(data: FollowSchema, db: Session = Depends(get_db)):
    f = db.query(Follow).filter(Follow.followed_by == data.followed_by, Follow.followed_to == data.followed_to).first()
    if not f:
        raise HTTPException(status_code=400, detail="You are NOT FOLLOWING this user.")
    db.delete(f)
    db.commit()
    return {"success": True, "status": 200, "msg": "User UNFOLLOWED successfully."}

# ---------------- 12. Check Followers ----------------
@app.get("/followers/{user_id}")
def check_followers(user_id: int, db: Session = Depends(get_db)):
    if not user_exists(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    followers = [f.followed_by for f in db.query(Follow).filter(Follow.followed_to == user_id).all()]
    blocks = db.query(Block).filter(or_(Block.block_to == user_id, Block.block_by == user_id)).all()
    for b in blocks:
        if b.block_to in followers: followers.remove(b.block_to)
        if b.block_by in followers: followers.remove(b.block_by)
    return {"success": True, "status": 200, "total_followers": len(followers), "followers": followers}

# ---------------- 13. Check Following ----------------
@app.get("/following/{user_id}")
def check_following(user_id: int, db: Session = Depends(get_db)):
    if not user_exists(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    following = [f.followed_to for f in db.query(Follow).filter(Follow.followed_by == user_id).all()]
    blocks = db.query(Block).filter(or_(Block.block_to == user_id, Block.block_by == user_id)).all()
    for b in blocks:
        if b.block_to in following: following.remove(b.block_to)
        if b.block_by in following: following.remove(b.block_by)
    return {"success": True, "status": 200, "total_following": len(following), "following": following}

# ---------------- 14. Block ----------------
@app.post("/block")
def block_user(data: BlockSchema, db: Session = Depends(get_db)):
    if data.block_by == data.block_to:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    if not user_exists(db, data.block_by) or not user_exists(db, data.block_to):
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Block).filter(Block.block_by == data.block_by, Block.block_to == data.block_to).first()
    if existing:
        return {"success": True, "status": 200, "msg": "You have ALREADY BLOCKED this user."}
    db.query(Follow).filter(
        or_(
            and_(Follow.followed_by == data.block_by, Follow.followed_to == data.block_to),
            and_(Follow.followed_by == data.block_to, Follow.followed_to == data.block_by)
        )
    ).delete()
    new_block = Block(block_by=data.block_by, block_to=data.block_to)
    db.add(new_block)
    db.commit()
    return {"success": True, "status": 200, "msg": "User BLOCKED successfully."}

# ---------------- 15. Unblock ----------------
@app.post("/unblock")
def unblock_user(data: BlockSchema, db: Session = Depends(get_db)):
    b = db.query(Block).filter(Block.block_by == data.block_by, Block.block_to == data.block_to).first()
    if not b:
        raise HTTPException(status_code=400, detail="You have NOT BLOCKED this user.")
    db.delete(b)
    db.commit()
    return {"success": True, "status": 200, "msg": "User UNBLOCKED successfully."}

# ---------------- 16. Like post ----------------
@app.post("/posts/{post_id}/like")
def like_post(post_id: int, like: LikeSchema = Body(...), db: Session = Depends(get_db)):
    p = db.query(Post).filter(Post.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if not user_exists(db, like.userId):
        raise HTTPException(status_code=404, detail="User not found")
    block_exists = db.query(Block).filter(
        or_(
            and_(Block.block_by == like.userId, Block.block_to == p.user_id),
            and_(Block.block_by == p.user_id, Block.block_to == like.userId)
        )
    ).first()
    if block_exists:
        raise HTTPException(status_code=400, detail="Cannot like due to block")
    existing = db.query(Like).filter(Like.user_id == like.userId, Like.post_id == post_id).first()
    if existing:
        return {"success": True, "status": 200, "msg": "Already liked"}
    new_like = Like(user_id=like.userId, post_id=post_id)
    db.add(new_like)
    db.commit()
    return {"success": True, "status": 200, "msg": "Liked"}

# ---------------- 17. Dislike ----------------
@app.post("/posts/{post_id}/dislike")
def dislike_post(post_id: int, like: LikeSchema = Body(...), db: Session = Depends(get_db)):
    existing = db.query(Like).filter(Like.user_id == like.userId, Like.post_id == post_id).first()
    if not existing:
        return {"success": True, "status": 200, "msg": "Not liked"}
    db.delete(existing)
    db.commit()
    return {"success": True, "status": 200, "msg": "Like removed"}

