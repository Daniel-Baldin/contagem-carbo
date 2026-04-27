# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
import pandas as pd

from database import SessionLocal, User, Historico
from auth import criar_senha_hash, verificar_senha, criar_token, obter_usuario

# ---------------------------------------------------------
# INICIALIZA FASTAPI
# ---------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# CRIA ADMIN PADRÃO SE NÃO EXISTIR
# ---------------------------------------------------------
db = SessionLocal()
if not db.query(User).filter(User.email == "admin@email.com").first():
    admin = User(
        nome="Admin",
        email="admin@email.com",
        senha_hash=criar_senha_hash("admin123"),
        tipo="admin"
    )
    db.add(admin)
    db.commit()
db.close()

# ---------------------------------------------------------
# CARREGA TACO
# ---------------------------------------------------------
taco = pd.read_excel("taco.xlsx")  # ou taco.xls

# ---------------------------------------------------------
# MODELOS Pydantic
# ---------------------------------------------------------
class Alimento(BaseModel):
    nome: str
    quantidade: float

class Refeicao(BaseModel):
    glicemia: float
    alvo: float
    fator_sensibilidade: float
    fator_carbo: float
    alimentos: List[Alimento]

class UsuarioCadastro(BaseModel):
    nome: str
    email: str
    senha: str

class EditarUsuario(BaseModel):
    tipo: str  # "admin" ou "user"

# ---------------------------------------------------------
# ENDPOINT: CADASTRAR USUÁRIO (APENAS ADMIN)
# ---------------------------------------------------------
@app.post("/register")
def register(dados: UsuarioCadastro, admin: User = Depends(obter_usuario)):
    if admin.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem cadastrar usuários")

    db = SessionLocal()
    if db.query(User).filter(User.email == dados.email).first():
        db.close()
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user = User(
        nome=dados.nome,
        email=dados.email,
        senha_hash=criar_senha_hash(dados.senha),
        tipo="user"
    )
    db.add(user)
    db.commit()
    db.close()

    return {"message": "Usuário cadastrado com sucesso"}

# ---------------------------------------------------------
# ENDPOINT: LOGIN
# ---------------------------------------------------------
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verificar_senha(form_data.password, user.senha_hash):
        db.close()
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = criar_token(user.email)
    db.close()

    return {
        "access_token": token,
        "token_type": "bearer",
        "tipo": user.tipo
    }

# ---------------------------------------------------------
# ENDPOINT: LISTAR ALIMENTOS
# ---------------------------------------------------------
@app.get("/alimentos")
def listar_alimentos():
    return taco["alimento"].tolist()

# ---------------------------------------------------------
# FUNÇÃO: CALCULAR CARBO POR ALIMENTO
# ---------------------------------------------------------
def carbo_alimento(nome, quantidade):
    linha = taco[taco["alimento"] == nome]
    if linha.empty:
        return 0
    carbo_100g = float(linha["carbo_100g"].values[0])
    return (carbo_100g / 100) * quantidade

# ---------------------------------------------------------
# ENDPOINT: CALCULAR DOSE + SALVAR HISTÓRICO
# ---------------------------------------------------------
@app.post("/calcular")
def calcular(refeicao: Refeicao, user: User = Depends(obter_usuario)):
    VG = refeicao.glicemia
    AG = refeicao.alvo
    FSI = refeicao.fator_sensibilidade

    correcao = max((VG - AG) / FSI, 0)

    FC = refeicao.fator_carbo

    carbo_total = sum(carbo_alimento(item.nome, item.quantidade) for item in refeicao.alimentos)

    insulina_carbo = carbo_total / FC
    dose_total = correcao + insulina_carbo

    db = SessionLocal()
    registro = Historico(
        user_id=user.id,
        glicemia=VG,
        carbo_total=carbo_total,
        insulina_carbo=insulina_carbo,
        insulina_correcao=correcao,
        insulina_total=dose_total
    )
    db.add(registro)
    db.commit()
    db.close()

    return {
        "carbo_total": carbo_total,
        "insulina_carbo": insulina_carbo,
        "correcao": correcao,
        "dose_total": dose_total
    }

# ---------------------------------------------------------
# ENDPOINT: HISTÓRICO DO USUÁRIO LOGADO
# ---------------------------------------------------------
@app.get("/historico")
def historico(user: User = Depends(obter_usuario)):
    db = SessionLocal()
    registros = db.query(Historico).filter(Historico.user_id == user.id).order_by(Historico.data_hora.desc()).all()
    db.close()

    return [
        {
            "glicemia": r.glicemia,
            "carbo_total": r.carbo_total,
            "insulina_carbo": r.insulina_carbo,
            "insulina_correcao": r.insulina_correcao,
            "insulina_total": r.insulina_total,
            "data_hora": r.data_hora.isoformat()
        }
        for r in registros
    ]

# ---------------------------------------------------------
# ENDPOINT: LISTAR USUÁRIOS (APENAS ADMIN)
# ---------------------------------------------------------
@app.get("/usuarios")
def listar_usuarios(admin: User = Depends(obter_usuario)):
    if admin.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver usuários")

    db = SessionLocal()
    users = db.query(User).all()
    db.close()

    return [
        {"id": u.id, "nome": u.nome, "email": u.email, "tipo": u.tipo}
        for u in users
    ]

# ---------------------------------------------------------
# ENDPOINT: EDITAR USUÁRIO (APENAS ADMIN)
# ---------------------------------------------------------
@app.put("/usuarios/{user_id}")
def editar_usuario(user_id: int, dados: EditarUsuario, admin: User = Depends(obter_usuario)):
    if admin.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem editar usuários")

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.tipo = dados.tipo
    db.commit()
    db.close()

    return {"message": "Usuário atualizado com sucesso"}
