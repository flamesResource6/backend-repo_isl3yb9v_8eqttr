import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

from database import db, create_document, get_documents

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Voxell DLC API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Schemas --------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    avatar_url: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    nickname: str
    avatar_url: Optional[str] = None
    roles: list[str] = ["player"]

# -------------------- Helpers --------------------

def get_user_by_email(email: str) -> Optional[dict]:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["playeruser"].find_one({"email": email})
    return doc

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def user_to_profile(doc: dict) -> ProfileResponse:
    return ProfileResponse(
        id=str(doc.get("_id")),
        email=doc.get("email"),
        nickname=doc.get("nickname"),
        avatar_url=doc.get("avatar_url"),
        roles=doc.get("roles", ["player"]),
    )

# -------------------- Routes --------------------
@app.get("/")
def read_root():
    return {"message": "Voxell DLC API ready"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

@app.post("/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest):
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Почта уже зарегистрирована")

    user_doc = {
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "nickname": payload.nickname,
        "avatar_url": payload.avatar_url,
        "roles": ["player"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    db["playeruser"].insert_one(user_doc)

    token = create_access_token({"sub": payload.email})
    return TokenResponse(access_token=token)

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Неверные данные для входа")

    token = create_access_token({"sub": payload.email})
    return TokenResponse(access_token=token)

# Note: For a real production app you would verify JWT on each request.
# Here we accept token and read subject (email) to fetch profile.

class TokenPayload(BaseModel):
    token: str

@app.post("/me", response_model=ProfileResponse)
def me(payload: TokenPayload):
    try:
        decoded = jwt.decode(payload.token, SECRET_KEY, algorithms=[ALGORITHM])
        email = decoded.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user_to_profile(user)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
