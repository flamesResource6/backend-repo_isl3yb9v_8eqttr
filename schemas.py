"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List

class Playeruser(BaseModel):
    """
    Voxell DLC players collection schema
    Collection name: "playeruser" (lowercase of class name)
    """
    email: EmailStr = Field(..., description="Уникальная почта игрока")
    password_hash: str = Field(..., description="Хэш пароля (bcrypt)")
    nickname: str = Field(..., min_length=3, max_length=32, description="Никнейм игрока")
    avatar_url: Optional[HttpUrl] = Field(None, description="URL аватара")
    roles: List[str] = Field(default_factory=lambda: ["player"], description="Роли пользователя (player, moderator, admin)")
    is_active: bool = Field(True, description="Аккаунт активен")
