from sqlalchemy import Column, String, Integer, DateTime, func, Text
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Tokens can be long, so we use the Text type
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True) # Refresh token is optional
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())