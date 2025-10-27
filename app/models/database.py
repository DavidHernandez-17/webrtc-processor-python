from sqlalchemy import create_engine, Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Inventory(Base):
    __tablename__ = 'inventories'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    spaces = relationship("Space", back_populates="inventory", cascade="all, delete-orphan")


class Space(Base):
    __tablename__ = 'spaces'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    inventory_id = Column(String, ForeignKey('inventories.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    action = Column(String, default='create')
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    inventory = relationship("Inventory", back_populates="spaces")
    elements = relationship("Element", back_populates="space", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="space", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="space", cascade="all, delete-orphan")


class Element(Base):
    __tablename__ = 'elements'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    space_id = Column(String, ForeignKey('spaces.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    amount = Column(Integer, default=1)
    action = Column(String, default='create')
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    space = relationship("Space", back_populates="elements")
    attributes = relationship("Attribute", back_populates="element", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="element", cascade="all, delete-orphan")


class Attribute(Base):
    __tablename__ = 'attributes'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    element_id = Column(String, ForeignKey('elements.id'), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    action = Column(String, default='create')
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    element = relationship("Element", back_populates="attributes")


class Image(Base):
    __tablename__ = 'images'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    space_id = Column(String, ForeignKey('spaces.id'), nullable=False)
    element_id = Column(String, ForeignKey('elements.id'), nullable=True)
    path = Column(String, nullable=True)
    path_synced = Column(String, nullable=True)
    description = Column(Text)
    action = Column(String, default='create')
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    space = relationship("Space", back_populates="images")
    element = relationship("Element", back_populates="images")
    

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_id = Column(Integer, unique=False, nullable=True)
    space_id = Column(String, ForeignKey('spaces.id'), nullable=False)
    path = Column(String, nullable=False)
    path_synced = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    synced = Column(Boolean, default=False)
    action = Column(String, default='create')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    space = relationship("Space", back_populates="videos")


class DatabaseManager:
    def __init__(self, db_path='inventory.db'):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.Session = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        return self.Session()
    
    def drop_tables(self):
        Base.metadata.drop_all(self.engine)