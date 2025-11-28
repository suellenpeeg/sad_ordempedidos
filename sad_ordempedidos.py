import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fpdf import FPDF
import os

# =========================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================
st.set_page_config(
    page_title="SAD - Sistema de Apoio à Decisão",
    layout="wide"
)

PRIMARY_COLOR = "#0A3D91"
SECOND_COLOR = "#E53935"

st.markdown(
    f"""
    <style>
        .sidebar .sidebar-content {{
            background-color: {PRIMARY_COLOR};
        }}
        .stButton>button {{
            background-color:{SECOND_COLOR};
            color: white;
            font-weight:bold;
            border-radius:5px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 SAD Fábrica de Tecidos – Gestão e Priorização")

# =========================================
# CARREGAR DADOS (PERSISTÊNCIA)
# =========================================
if os.path.exists("produtos.csv"):
    st.session_state.produtos = pd.read_csv("produtos.csv")
else:
    st.session_state.produtos = pd.DataFrame(columns=["Produto", "Tempo"])

if os.path.exists("pedidos.csv"):
    st.session_state.pedidos = pd.read_csv(
        "pedidos.csv", parse_dates=["Prazo", "Data Entrada", "Data Conclusão"]
    )
else:
    st.session_state.pedidos = pd.DataFrame(columns=[
        "Pedido", "Produto", "Urgência", "Custo(R$)", "Tempo Produção",
        "Pontuação", "Prazo", "Data Entrada", "Data Conclusão", "Status"
    ])


# =========================================
# FUNÇÃO PARA GERAR PDF
# =========================================
def gerar_pdf(pedidos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    hoje = datetime.today().strftime("%d/%m/%Y")
    pdf.cell(200, 10, txt=f"Ordem de Serviço - {hoje}", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    for _, row in pedidos.iterrows():
        texto = (
            f"Pedido: {row['Pedido']} | Produto: {row['Produto']} | "
            f"Urgência: {row['Urgência']} | Custo: R${row['Custo(R$)']:.2f} | "
            f"Tempo: {row['Tempo Produção']}h | Prazo: {row['Prazo'].strftime('%d/%m/%Y')}"
        )
        pdf.multi_cell(0, 8, txt=texto)
        pdf.ln(2)

    filename = "ordem_servico.pdf"
    pdf.output(filename)
    return filename


# =========================================
# ABAS
# =========================================
aba1, aba2, aba3 = st.tabs([
    "📌 Priorização de Pedidos",
    "🧵 Cadastro de Produtos",
    "📈 Gráficos e Indicadores"
])


# ============================================================
# ABA 1 – PRIORIZAÇÃO DE PEDIDOS
# ============================================================
with aba1:
    st.header("📌 Priorização de Pedidos")

    with st.form("novo_pedido"):
        st.subheader("➕ Adicionar Pedido")

        nome = st.text_input("Nome do Pedido")
        prazo = st.date_input("Prazo de entrega", datetime.today() + timedelta(days=7))

        if len(st.session_state.produtos) == 0:
            st.warning("Cadastre produtos na aba **Cadastro de Produtos**.")
        produto = st.selectbox("Tipo de Produto", st.session_state.produtos["Produto"])

        urgencia = st.slider("Urgência (1 a 10)", 1, 10, 5)
        custo = st.number_input("Custo (R$ 0 a 2000)", 0, 2000, 500)

        enviar = st.form_submit_button("Adicionar Pedido")

        if enviar and nome:
            tempo = st.session_state.produtos.loc[
                st.session_state.produtos["Produto"] == produto, "Tempo"
            ].iloc[0]

            pontuacao = (urgencia * 0.4) + ((10 - tempo) * 0.3) + ((2000 - custo) / 2000 * 10 * 0.3)

            novo = pd.DataFrame([{
                "Pedido": nome,
                "Produto": produto,
                "Urgência": urgencia,
                "Custo(R$)": custo,
                "Tempo Produção": tempo,
                "Pontuação": pontuacao,
                "Prazo": prazo,
                "Data Entrada": datetime.today(),
                "Data Conclusão": None,
                "Status": "Aberto"
            }])

            st.session_state.pedidos = pd.concat([st.session_state.pedidos, novo], ignore_index=True)
            st.session_state.pedidos.to_csv("pedidos.csv", index=False)
            st.success("Pedido adicionado!")

    # ---------- ORDENAÇÃO ----------
    pedidos_abertos = st.session_state.pedidos[st.session_state.pedidos["Status"] == "Aberto"]
    pedidos_abertos = pedidos_abertos.sort_values(by="Pontuação", ascending=False)

    st.subheader("📄 Ordem de Produção")
    st.dataframe(pedidos_abertos)

    # ---------- MARCAR CONCLUÍDO ----------
    st.subheader("✔ Marcar como concluído")
    for idx, row in pedidos_abertos.iterrows():
        if st.checkbox(f"Concluir pedido: {row['Pedido']}", key=f"chk_{idx}"):
            st.session_state.pedidos.at[idx, "Status"] = "Concluído"
            st.session_state.pedidos.at[idx, "Data Conclusão"] = datetime.today()
            st.session_state.pedidos.to_csv("pedidos.csv", index=False)
            st.success(f"Pedido {row['Pedido']} concluído.")

    # ---------- PDF ----------
    if st.button("📥 Gerar PDF da Ordem de Serviço"):
        pdf_path = gerar_pdf(pedidos_abertos)
        with open(pdf_path, "rb") as f:
            st.download_button("Download do PDF", f, file_name=pdf_path)


# ============================================================
# ABA 2 – CADASTRO DE PRODUTOS
# ============================================================
with aba2:
    st.header("🧵 Cadastro de Produtos")

    with st.form("cad_produto"):
        st.subheader("➕ Adicionar Produto")
        nome_prod = st.text_input("Nome do Produto")
        tempo_prod = st.number_input("Tempo médio de produção (horas)", 1, 48, 2)

        add_prod = st.form_submit_button("Salvar")

        if add_prod and nome_prod:
            novo_prod = pd.DataFrame([{
                "Produto": nome_prod,
                "Tempo": tempo_prod
            }])
            st.session_state.produtos = pd.concat([st.session_state.produtos, novo_prod], ignore_index=True)
            st.session_state.produtos.to_csv("produtos.csv", index=False)
            st.success("Produto cadastrado!")
            st.rerun()

    st.subheader("📄 Produtos cadastrados")
    st.dataframe(st.session_state.produtos)

    # ---------- EDIÇÃO E EXCLUSÃO ----------
    st.subheader("✏ Editar / 🗑 Excluir Produtos")
    for idx, row in st.session_state.produtos.iterrows():
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{row['Produto']}** – {row['Tempo']}h")
        with col2:
            if st.button("Editar", key=f"edit{idx}"):
                novo_nome = st.text_input("Novo nome", row['Produto'], key=f"novo_nome{idx}")
                novo_tempo = st.number_input("Novo tempo", 1, 48, row['Tempo'], key=f"novo_tempo{idx}")
                if st.button("Salvar alterações", key=f"save{idx}"):
                    st.session_state.produtos.at[idx, "Produto"] = novo_nome
                    st.session_state.produtos.at[idx, "Tempo"] = novo_tempo
                    st.session_state.produtos.to_csv("produtos.csv", index=False)
                    st.rerun()
        with col3:
            if st.button("Excluir", key=f"del{idx}"):
                st.session_state.produtos = st.session_state.produtos.drop(idx).reset_index(drop=True)
                st.session_state.produtos.to_csv("produtos.csv", index=False)
                st.rerun()


# ============================================================
# ABA 3 – GRÁFICOS E INDICADORES
# ============================================================
with aba3:
    st.header("📈 Gráficos e Indicadores")

    pedidos = st.session_state.pedidos.copy()

    if pedidos.empty:
        st.info("Nenhum pedido cadastrado ainda.")
    else:
        hoje = datetime.today()
        pedidos["Prazo"] = pd.to_datetime(pedidos["Prazo"], errors="coerce")
        pedidos["Atrasado"] = (pedidos["Status"] == "Aberto") & (pedidos["Prazo"] < hoje)

        resumo = pd.DataFrame({
            "Status": ["Abertos", "Atrasados", "Concluídos"],
            "Quantidade": [
                sum(pedidos["Status"] == "Aberto"),
                sum(pedidos["Atrasado"]),
                sum(pedidos["Status"] == "Concluído"),
            ]
        })

        st.subheader("📊 Situação dos Pedidos")
        fig = px.bar(resumo, x="Status", y="Quantidade", color="Status",
                     color_discrete_map={
                         "Abertos": PRIMARY_COLOR,
                         "Atrasados": SECOND_COLOR,
                         "Concluídos": "#2E7D32"
                     })
        st.plotly_chart(fig)

        # Tempo entre entrada e conclusão em horas
        concluídos = pedidos[pedidos["Status"] == "Concluído"].copy()
        if not concluídos.empty:
            concluídos["Data Entrada"] = pd.to_datetime(concluídos["Data Entrada"], errors="coerce")
            concluídos["Data Conclusão"] = pd.to_datetime(concluídos["Data Conclusão"], errors="coerce")

            # 🔥 Tempo em horas
            concluídos["Horas"] = (
                concluídos["Data Conclusão"] - concluídos["Data Entrada"]
            ).dt.total_seconds() / 3600

            st.subheader("⏱ Tempo total para concluir cada pedido (horas)")
            fig2 = px.bar(
                concluídos,
                x="Pedido",
                y="Horas",
                color="Horas",
                color_continuous_scale="Bluered"
            )
            st.plotly_chart(fig2)










