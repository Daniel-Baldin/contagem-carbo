from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from database import SessionLocal, User

SECRET_KEY = "CHAVE_SUPER_SECRETA_TROCAR_DEPOIS"
ALGORITHM = "HS256"

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

def criar_senha_hash(senha: str) -> str:
    return pwd.hash(senha)

def verificar_senha(senha: str, hash: str) -> bool:
    return pwd.verify(senha, hash)

def criar_token(email: str) -> str:
    dados = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)

def obter_usuario(token: str = Depends(oauth2)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user