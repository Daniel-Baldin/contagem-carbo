from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import SessionLocal, User, Historico
from auth import criar_senha_hash, verificar_senha, criar_token, obter_usuario

# ---------------------------------------------------------
# INICIALIZA FASTAPI
# ---------------------------------------------------------
app = FastAPI()

# ---------------------------------------------------------
# STATIC E TEMPLATES
# ---------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------
# ROTA RAIZ -> INDEX.HTML (LOGIN / SPA ANTIGA)
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

# ---------------------------------------------------------
# TELAS HTML NOVAS (PROTEGIDAS POR LOGIN)
# ---------------------------------------------------------
@app.get("/welcome", response_class=HTMLResponse)
def pagina_welcome(request: Request, user: User = Depends(obter_usuario)):
    is_admin = user.tipo == "admin"
    return templates.TemplateResponse(
        "welcome.html",
        {"request": request, "user": user, "is_admin": is_admin}
    )

@app.get("/calculo", response_class=HTMLResponse)
def pagina_calculo(request: Request, user: User = Depends(obter_usuario)):
    return templates.TemplateResponse(
        "calculo.html",
        {"request": request, "user": user}
    )

@app.get("/historico", response_class=HTMLResponse)
def pagina_historico(request: Request, user: User = Depends(obter_usuario)):
    db = SessionLocal()
    registros = (
        db.query(Historico)
        .filter(Historico.user_id == user.id)
        .order_by(Historico.data_hora.desc())
        .all()
    )
    db.close()
    return templates.TemplateResponse(
        "historico.html",
        {"request": request, "user": user, "historico": registros}
    )

@app.get("/dashboard", response_class=HTMLResponse)
def pagina_dashboard(request: Request, user: User = Depends(obter_usuario)):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )

@app.get("/assinantes", response_class=HTMLResponse)
def pagina_assinantes(request: Request, user: User = Depends(obter_usuario)):
    if user.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores")
    db = SessionLocal()
    assinantes = db.query(User).all()
    db.close()
    return templates.TemplateResponse(
        "assinantes.html",
        {"request": request, "user": user, "assinantes": assinantes}
    )

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# FORÇA APAGAR BANCO CORROMPIDO NO RENDER (AGORA NA PASTA DATA)
# ---------------------------------------------------------
if os.path.exists("data/carbo.db"):
    os.remove("data/carbo.db")

# ---------------------------------------------------------
# CRIA ADMIN PADRÃO SE NÃO EXISTIR
# ---------------------------------------------------------
db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    admin = User(
        nome="Admin",
        username="admin",
        senha_hash=criar_senha_hash("admin123"),
        tipo="admin"
    )
    db.add(admin)
    db.commit()
db.close()

# ---------------------------------------------------------
# CARREGA TACO
# ---------------------------------------------------------
taco = pd.read_excel("taco.xlsx")

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
    username: str
    senha: str
    tipo: str = "user"

class EditarUsuario(BaseModel):
    tipo: str

# ---------------------------------------------------------
# ENDPOINTS ADMIN USUÁRIOS
# ---------------------------------------------------------
@app.post("/admin/usuarios")
def criar_usuario(dados: UsuarioCadastro, admin: User = Depends(obter_usuario)):
    if admin.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem cadastrar usuários")

    db = SessionLocal()
    if db.query(User).filter(User.username == dados.username).first():
        db.close()
        raise HTTPException(status_code=400, detail="Usuário já existe")

    user = User(
        nome=dados.nome,
        username=dados.username,
        senha_hash=criar_senha_hash(dados.senha),
        tipo=dados.tipo
    )
    db.add(user)
    db.commit()
    db.close()

    return {"message": "Usuário criado com sucesso"}

@app.get("/admin/usuarios")
def listar_usuarios(admin: User = Depends(obter_usuario)):
    if admin.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver usuários")

    db = SessionLocal()
    users = db.query(User).all()
    db.close()

    return [
        {"id": u.id, "nome": u.nome, "username": u.username, "tipo": u.tipo}
        for u in users
    ]

@app.put("/admin/usuarios/{user_id}")
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

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verificar_senha(form_data.password, user.senha_hash):
        db.close()
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = criar_token(user.username)
    db.close()

    return {
        "access_token": token,
        "token_type": "bearer",
        "tipo": user.tipo
    }

# ---------------------------------------------------------
# ALIMENTOS / CÁLCULO
# ---------------------------------------------------------
@app.get("/alimentos")
def listar_alimentos():
    return taco["alimento"].tolist()

def carbo_alimento(nome, quantidade):
    linha = taco[taco["alimento"] == nome]
    if linha.empty:
        return 0
    carbo_100g = float(linha["carbo_100g"].values[0])
    return (carbo_100g / 100) * quantidade

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
# HISTÓRICO JSON (PARA DASHBOARD / FRONT)
# ---------------------------------------------------------
@app.get("/api/historico")
def historico_api(user: User = Depends(obter_usuario)):
    db = SessionLocal()
    registros = (
        db.query(Historico)
        .filter(Historico.user_id == user.id)
        .order_by(Historico.data_hora.desc())
        .all()
    )
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
