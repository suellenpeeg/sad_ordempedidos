import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fpdf import FPDF

# --- Configuração da Página ---
st.set_page_config(
    page_title="SAD Fábrica de Tecidos",
    layout="wide"
)

st.title("SAD Fábrica de Tecidos - Gestão e Prioridade de Pedidos")

# --------------------------
# Controle de acesso
# --------------------------
st.sidebar.header("Login")
usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")

# Usuários e datas de acesso
usuarios_validos = {
    "admin": {"senha": "1234", "acesso_ate": datetime(2025, 12, 31)},
    "usuario1": {"senha": "abcd", "acesso_ate": datetime(2025, 11, 30)}
}

acesso_autorizado = False
if usuario in usuarios_validos:
    if senha == usuarios_validos[usuario]["senha"]:
        if datetime.today() <= usuarios_validos[usuario]["acesso_ate"]:
            acesso_autorizado = True
        else:
            st.sidebar.error("⛔ Acesso expirado para este usuário.")
    else:
        st.sidebar.error("Senha incorreta.")

if not acesso_autorizado:
    st.stop()

# --------------------------
# Configuração da capacidade da fábrica
# --------------------------
NUM_MAQUINAS = 5
HORAS_POR_DIA = 8
DIAS_POR_SEMANA = 5
CAPACIDADE_SEMANAL = NUM_MAQUINAS * HORAS_POR_DIA * DIAS_POR_SEMANA  # 200 horas

# --------------------------
# Dados dos produtos e tempo de produção (horas)
# --------------------------
tempo_producao_produto = {
    "Camiseta de Malha": 2,
    "Camiseta UV": 3,
    "Shorts de Malha": 2,
    "Calças de Malha": 4
}

# --------------------------
# Session State para pedidos
# --------------------------
if "pedidos" not in st.session_state:
    st.session_state.pedidos = pd.DataFrame(columns=[
        "Pedido", "Produto", "Urgência", "Custo", "Tempo de Produção", "Pontuação", "Prazo", "Status"
    ])

# --------------------------
# Formulário para adicionar pedido
# --------------------------
st.sidebar.header("Adicionar Novo Pedido")
with st.sidebar.form("form_novo_pedido", clear_on_submit=True):
    nome = st.text_input("Nome do Pedido")
    produto = st.selectbox("Tipo de Produto", list(tempo_producao_produto.keys()))
    urgencia = st.slider("Urgência (1-10)", 1, 10, 5)
    custo = st.slider("Custo (1-10)", 1, 10, 5)
    prazo = st.date_input("Prazo de entrega", datetime.today() + timedelta(days=7))
    submit = st.form_submit_button("Adicionar Pedido")
    
    if submit and nome:
        tempo = tempo_producao_produto[produto]
        # Pontuação ponderada: urgência (40%), tempo de produção (30%), custo (30%)
        pontuacao = (urgencia*0.4 + (10 - tempo)*0.3 + (10 - custo)*0.3)
        novo_pedido = pd.DataFrame([{
            "Pedido": nome,
            "Produto": produto,
            "Urgência": urgencia,
            "Custo": custo,
            "Tempo de Produção": tempo,
            "Pontuação": pontuacao,
            "Prazo": prazo,
            "Status": "Aberto"
        }])
        st.session_state.pedidos = pd.concat([st.session_state.pedidos, novo_pedido], ignore_index=True)
        st.success(f"Pedido '{nome}' adicionado com sucesso!")

# --------------------------
# Dashboard Principal
# --------------------------
st.header("Dashboard de Pedidos")

pedidos_abertos = st.session_state.pedidos[st.session_state.pedidos["Status"]=="Aberto"]

if not pedidos_abertos.empty:
    pedidos_abertos = pedidos_abertos.sort_values(by="Pontuação", ascending=False)

    # Contagem de pedidos
    num_abertos = pedidos_abertos.shape[0]
    num_concluidos = st.session_state.pedidos[st.session_state.pedidos["Status"]=="Concluído"].shape[0]
    st.subheader(f"Pedidos Abertos: {num_abertos} | Pedidos Concluídos: {num_concluidos}")

    # Tabela de pedidos abertos
    st.dataframe(pedidos_abertos)

    # Marcar pedidos como concluídos
    st.subheader("Marcar Pedidos como Concluídos")
    for idx, row in pedidos_abertos.iterrows():
        if st.checkbox(f"Concluir Pedido: {row['Pedido']}", key=f"chk_{idx}"):
            st.session_state.pedidos.at[idx, "Status"] = "Concluído"
            st.experimental_rerun()

    # Gráfico de Prioridade
    st.subheader("Gráfico de Prioridade")
    fig1 = px.bar(pedidos_abertos, x="Pedido", y="Pontuação", color="Urgência",
                  title="Prioridade dos Pedidos (Maior = mais urgente)")
    st.plotly_chart(fig1)

    # Gráfico de Capacidade
    st.subheader("Capacidade Semanal")
    horas_totais = pedidos_abertos["Tempo de Produção"].sum()
    df_capacidade = pd.DataFrame({
        "Tipo": ["Horas Planejadas", "Capacidade Total"],
        "Horas": [horas_totais, CAPACIDADE_SEMANAL]
    })
    fig2 = px.bar(df_capacidade, x="Tipo", y="Horas", color="Tipo", text="Horas")
    st.plotly_chart(fig2)

    # Alertas de prazo (3 dias antes)
    st.subheader("Alertas de Prazo")
    hoje = datetime.today().date()
    proximos_alerta = pedidos_abertos[(pedidos_abertos["Prazo"] - timedelta(days=3)) <= hoje]
    if not proximos_alerta.empty:
        st.warning(f"⏰ Pedidos próximos do prazo (menos de 3 dias): {', '.join(proximos_alerta['Pedido'].tolist())}")

    # Exportar PDF
    st.subheader("Exportar PDF da Ordem de Produção")
    if st.button("Gerar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Ordem de Produção - Pedidos Abertos", ln=True, align="C")
        pdf.ln(10)
        for idx, row in pedidos_abertos.iterrows():
            pdf.cell(0, 10, txt=f"Pedido: {row['Pedido']}, Produto: {row['Produto']}, Urgência: {row['Urgência']}, Tempo: {row['Tempo de Produção']}h, Custo: {row['Custo']}, Prazo: {row['Prazo']}", ln=True)
        pdf_file = "ordem_producao.pdf"
        pdf.output(pdf_file)
        with open(pdf_file, "rb") as f:
            st.download_button("Download PDF", f, file_name=pdf_file)

else:
    st.info("Nenhum pedido aberto no momento.")

st.caption("SAD Profissional para fábrica de tecidos com controle de capacidade, prioridade, alertas e PDF.")
