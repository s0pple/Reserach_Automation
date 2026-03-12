from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Use the data directory for the SQLite database
DB_PATH = "sqlite:///data/research.db"
Base = declarative_base()

class ResearchRun(Base):
    __tablename__ = 'research_runs'
    
    id = Column(Integer, primary_key=True)
    domain = Column(String)
    date_run = Column(DateTime, default=datetime.utcnow)
    total_claims_extracted = Column(Integer)
    top_opportunity_score = Column(Float)
    status = Column(String)
    
    opportunities = relationship("Opportunity", back_populates="run")

class Opportunity(Base):
    __tablename__ = 'opportunities'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('research_runs.id'))
    title = Column(String)
    score = Column(Float)
    rationale = Column(Text)
    memo_markdown = Column(Text)
    
    run = relationship("ResearchRun", back_populates="opportunities")

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    # Ensure the data directory exists
    os.makedirs("data", exist_ok=True)
    
    engine = create_engine(DB_PATH)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Returns a new SQLAlchemy session."""
    engine = create_engine(DB_PATH)
    Session = sessionmaker(bind=engine)
    return Session()
