from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, JSON, DateTime, Integer, func, ForeignKey
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass

class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    station_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), nullable=True)

class Station(Base):
    __tablename__ = "stations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), nullable=True)

class Node(Base):
    __tablename__ = "nodes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    station_id: Mapped[str] = mapped_column(String, ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    transcript_count: Mapped[int] = mapped_column(Integer, default=0)

class Transcript(Base):
    __tablename__ = "transcripts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    station_id: Mapped[str] = mapped_column(String, ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    
    received_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    duration_seconds: Mapped[float] = mapped_column(Float)
    raw_text: Mapped[str] = mapped_column(String)
    segments_json: Mapped[str] = mapped_column(JSON)
    audio_path: Mapped[str] = mapped_column(String)
    
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
