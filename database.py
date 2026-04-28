# database.py
import os
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# ---------------------------------------------------------
# GARANTE QUE A PASTA DO BANCO EXISTE (Render precisa disso)
# ---------------------------------------------------------
os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------
# BANCO DE DADOS (AGORA EM UMA PASTA GRAVÁVEL)
# ---------------------------------------------------------
engine = create_engine("sqlite:////./data/carbo.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

# ---------------------------------------------------------
# MODELO DE USUÁRIO
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    tipo = Column(String, default="user")

    historicos = relationship("Historico", back_populates="user")

# ---------------------------------------------------------
# MODELO DE HISTÓRICO
# ---------------------------------------------------------
class Historico(Base):
    __tablename__ = "historico"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    glicemia = Column(Float)
    carbo_total = Column(Float)
    insulina_carbo = Column(Float)
    insulina_correcao = Column(Float)
    insulina_total = Column(Float)
    data_hora = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="historicos")

# ---------------------------------------------------------
# CRIA AS TABELAS
# ---------------------------------------------------------
Base.metadata.create_all(bind=engine)
