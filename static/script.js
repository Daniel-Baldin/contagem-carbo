function logout() {
    // Se você usa JWT em cookie, aqui pode só redirecionar:
    window.location.href = "/logout";
}

function calcular() {
    const glicemia = Number(document.getElementById("glicemia").value);
    const carbo = Number(document.getElementById("carbo").value);
    const sens = Number(document.getElementById("sensibilidade").value);
    const rel = Number(document.getElementById("relacao").value);

    if (!glicemia || !carbo || !sens || !rel) {
        alert("Preencha todos os campos.");
        return;
    }

    const insCarbo = carbo / rel;
    const insCorr = glicemia > 120 ? (glicemia - 120) / sens : 0;
    const total = insCarbo + insCorr;

    document.getElementById("resultado").innerHTML = `
        <h3>Resultado</h3>
        <p>Insulina por carboidrato: <b>${insCarbo.toFixed(1)}</b></p>
        <p>Insulina por correção: <b>${insCorr.toFixed(1)}</b></p>
        <p>Total recomendado: <b>${total.toFixed(1)}</b></p>
    `;
}

// Dashboard simples: espera uma rota /api/historico que devolve JSON
function carregarDashboard() {
    fetch("/api/historico")
        .then(r => r.json())
        .then(dados => {
            const labels = dados.map(x => x.data_hora_formatada || x.data_hora);
            const glicemias = dados.map(x => x.glicemia);
            const carbos = dados.map(x => x.carbo_total);
            const insulinas = dados.map(x => x.insulina_total);

            criarGrafico("chartGlicemia", "Glicemia (mg/dL)", labels, glicemias, "#38bdf8");
            criarGrafico("chartCarbo", "Carboidratos (g)", labels, carbos, "#a855f7");
            criarGrafico("chartInsulina", "Insulina (U)", labels, insulinas, "#22c55e");
        })
        .catch(() => {
            console.warn("Não foi possível carregar o dashboard.");
        });
}

function criarGrafico(id, label, labels, data, color) {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label,
                data,
                borderColor: color,
                backgroundColor: color + "33",
                tension: 0.35,
                fill: true,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            plugins: {
                legend: { labels: { color: "#e5e7eb" } }
            },
            scales: {
                x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
                y: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } }
            }
        }
    });
}

// Placeholders para admin (você liga isso nas suas rotas depois)
function abrirCadastroAssinante() {
    alert("Aqui você pode abrir um modal ou redirecionar para um formulário de cadastro.");
}

function editarAssinante(id) {
    alert("Editar assinante ID: " + id);
}

function excluirAssinante(id) {
    if (confirm("Tem certeza que deseja excluir este assinante?")) {
        alert("Aqui você chamaria a API para excluir o assinante ID: " + id);
    }
}
