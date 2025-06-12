from sqlalchemy import Column, String, Integer, DateTime, func, Text, Float, ForeignKey
from sqlalchemy.orm import relationship 
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

    steps = relationship("Steps", back_populates="user", cascade="all, delete-orphan")
    heart_rates = relationship("HeartRate", back_populates="user", cascade="all, delete-orphan")
    sleep = relationship("Sleep", back_populates="user", cascade="all, delete-orphan")
    blood_pressures = relationship("BloodPressure", back_populates="user", cascade="all, delete-orphan")
    oxygen_saturations = relationship("OxygenSaturation", back_populates="user", cascade="all, delete-orphan")

class Steps(Base):
    __tablename__ = "steps"
    # Settings for TimescaleDB (optional in SQLAlchemy, but good practice)
    __table_args__ = (
        {"timescaledb_hypertable": {
            "time_column_name": "timestamp"
        }}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Integer, nullable=False)
    
    user = relationship("User", back_populates="steps")

class HeartRate(Base):
    __tablename__ = "heart_rate"
    __table_args__ = (
        {"timescaledb_hypertable": {
            "time_column_name": "timestamp"
        }}
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False) # Heart rate can be a floating point value (average)

    user = relationship("User", back_populates="heart_rates")

class Sleep(Base):
    __tablename__ = "sleep"
    __table_args__ = ({"timescaledb_hypertable": {"time_column_name": "end_time"}})
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False, index=True)
    # Value is the sleep category according to Google Fit: 1-Awake, 2-Sleep, 3-OutOfBed, 4-Light, 5-Deep, 6-REM
    value = Column(Integer, nullable=False) 
    
    user = relationship("User", back_populates="sleep")

class BloodPressure(Base):
    __tablename__ = "blood_pressure"
    __table_args__ = ({"timescaledb_hypertable": {"time_column_name": "timestamp"}})
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    systolic = Column(Float, nullable=False)
    diastolic = Column(Float, nullable=False)
    
    user = relationship("User", back_populates="blood_pressures")

class OxygenSaturation(Base):
    __tablename__ = "oxygen_saturation"
    __table_args__ = ({"timescaledb_hypertable": {"time_column_name": "timestamp"}})
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)
    
    user = relationship("User", back_populates="oxygen_saturations")