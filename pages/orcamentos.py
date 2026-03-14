import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from fpdf import FPDF

# --- 1. FUNÇÃO DO PDF (REVISADA E MELHORADA) ---
def gerar_pdf_orcamento(cliente, validade, itens, total, obs, vendedor, contato, email, tel):
    pdf = FPDF()
    pdf.add_page()
    
    def clean(txt):
        if not txt: return ""
        return str(txt).replace('—', '-').replace('–', '-').replace('“', '"').replace('”', '"')

    # --- CABEÇALHO ---
    try:
        pdf.image("LOGO Fundo Branco Puro.png", x=10, y=8, w=50)
    except:
        pdf.set_font("Helvetica", "B", 15)
        pdf.text(10, 20, "FILTROS DC")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(130, 10)
    end_dc = "Filtros DC Comercio Ltda.\nCNPJ 61.696.514/0001-18\nRua Nicolau Zarvos, 161 - Jabaquara\n(11) 2592.0025 | www.masterfilter.com.br"
    pdf.multi_cell(70, 4, clean(end_dc), align="R")
    
    pdf.line(10, 32, 200, 32)
    pdf.ln(20)

    # --- DADOS DO CLIENTE ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, f"DATA: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="R")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Aos cuidados: {clean(contato).upper()}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Cliente: {clean(cliente)}", ln=True)
    pdf.cell(0, 6, f"E-mail: {clean(email)} | Tel: {clean(tel)}", ln=True)
    
    # INTRODUÇÃO
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    texto_intro = "Com 36 anos de experiência no mercado de filtragem industrial, a Filtros DC consolida-se pela excelência técnica. Apresentamos nossa proposta comercial detalhada."
    pdf.multi_cell(0, 5, clean(texto_intro), align="J")
    
    # TÍTULO
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "PROPOSTA COMERCIAL", ln=True, align="C", fill=True)

    # --- TABELA DE ITENS (CORRIGIDA) ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "Descricao", border=1, fill=True)
    pdf.cell(15, 8, "Qtd", border=1, align="C", fill=True)
    pdf.cell(42, 8, "Unitario", border=1, align="C", fill=True)
    pdf.cell(43, 8, "Total", border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for it in itens:
        alt_inicial = pdf.get_y()
        # Coluna Descrição (MultiCell para detalhes técnicos)
        pdf.multi_cell(90, 5, clean(f"{it['ITEM']}\n{it['DETALHES']}"), border=1)
        alt_final = pdf.get_y()
        h_linha = alt_final - alt_inicial
        
        # Reposiciona para as colunas laterais na mesma altura
        pdf.set_xy(100, alt_inicial)
        pdf.cell(15, h_linha, str(it['QTD']), border=1, align="C")
        pdf.cell(42, h_linha, f"R$ {it['UNIT']:,.2f}", border=1, align="R")
        pdf.cell(43, h_linha, f"R$ {it['TOTAL']:,.2f}", border=1, align="R")
        pdf.ln(h_linha)

    # TOTAL
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(147, 10, "VALOR TOTAL:", align="R")
    pdf.cell(43, 10, f"R$ {total:,.2f}", border=1, align="R", ln=True)
    
    # OBSERVAÇÕES
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "CONDICOES GERAIS:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, clean(obs))

    # --- ASSINATURA (RECUPERADA) ---
    pdf.ln(10)
    try:
        pdf.image("Assinatura Chiodo.jpg", x=70, w=65)
    except:
        pdf.ln(15)
        pdf.cell(0, 5, "________________________________________", ln=True, align="C")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, f"Vendedor: {clean(vendedor)} - Filtros DC", ln=True, align="C")

    return pdf.output()

# --- 2. INTERFACE E LÓGICA ---

st.set_page_config(page_title="Orçamentos | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Carregamento de bases
ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_C = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Clientes"
URL_P = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Produtos"

@st.cache_data(ttl=2)
def carregar_bases():
    c = pd.read_csv(URL_C)
    p = pd.read_csv(URL_P)
    c.columns = [str(col).upper() for col in c.columns]
    p.columns = [str(col).upper() for col in p.columns]
    return c, p

df_cli, df_prod = carregar_bases()

# --- POPUP DE EDIÇÃO COMPLETA ---
@st.dialog("📝 Editar Orçamento e PDF")
def editar_orcamento_dialog(cliente, data_orig, itens_df):
    if 'cesta_temp' not in st.session_state:
        st.session_state.cesta_temp = []
        for _, it in itens_df.iterrows():
            st.session_state.cesta_temp.append({
                "ITEM": it['PRODUTO'], "DETALHES": it['DETALHES'],
                "QTD": int(it['QT']), "UNIT": float(it['VALOR UNITARIO']),
                "TOTAL": float(it['VALOR TOTAL'])
            })

    st.subheader(f"Cliente: {cliente}")
    
    # 1. Adicionar NOVO item dentro do Editar
    with st.expander("➕ Adicionar novo item a este orçamento"):
        p_sel = st.selectbox("Escolha o Produto", df_prod['NOME'].unique(), key="add_p_pop")
        c1, c2 = st.columns(2)
        q_sel = c1.number_input("Qtd", min_value=1, value=1, key="add_q_pop")
        v_sel = c2.number_input("Preço", value=0.0, key="add_v_pop")
        d_sel = st.text_area("Detalhes Técnicos", key="add_d_pop").upper()
        if st.button("Inserir Item"):
            st.session_state.cesta_temp.append({
                "ITEM": p_sel, "DETALHES": d_sel, "QTD": q_sel, "UNIT": v_sel, "TOTAL": q_sel * v_sel
            })
            st.rerun()

    st.divider()
    
    # 2. Lista de Itens Atuais
    itens_para_remover = []
    for i, item in enumerate(st.session_state.cesta_temp):
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 0.5])
            col1.write(f"**{item['ITEM']}**")
            st.session_state.cesta_temp[i]['QTD'] = col2.number_input("Qtd", value=item['QTD'], key=f"q_pop_{i}")
            st.session_state.cesta_temp[i]['UNIT'] = col3.number_input("Unit", value=item['UNIT'], key=f"u_pop_{i}")
            st.session_state.cesta_temp[i]['DETALHES'] = st.text_area("Detalhes Técnicos", value=item['DETALHES'], key=f"d_pop_{i}").upper()
            if col4.button("🗑️", key=f"del_pop_{i}"):
                itens_para_remover.append(i)
    
    for i in sorted(itens_para_remover, reverse=True):
        st.session_state.cesta_temp.pop(i)
        st.rerun()

    total_t = sum(it['TOTAL'] for it in st.session_state.cesta_temp)
    obs_pop = st.text_area("Condições Gerais", "PAGAMENTO: 30 DIAS | ENTREGA: 05 DIAS", key="obs_p").upper()
    
    st.markdown(f"### Total: R$ {total_t:,.2f}")
    
    if st.button("📥 GERAR PDF ATUALIZADO", use_container_width=True, type="primary"):
        pdf_b = gerar_pdf_orcamento(cliente, "", st.session_state.cesta_temp, total_t, obs_pop, "VENDEDOR", "CLIENTE", "", "")
        st.download_button("CLIQUE PARA BAIXAR", data=bytes(pdf_b), file_name=f"Orcamento_{cliente}.pdf", use_container_width=True)

# --- ABAS PRINCIPAIS ---
aba1, aba2 = st.tabs(["➕ Novo Orçamento", "🔍 Buscar Orçamentos"])

with aba1:
    # (Sua lógica de novo orçamento já funciona bem, mantive o padrão)
    st.subheader("Cadastro de Proposta")
    # ... (restante do seu código de novo orçamento) ...
    if st.button("➕ ADICIONAR ITEM NA CESTA PRINCIPAL"):
        # Lógica de adição aqui...
        pass

with aba2:
    st.subheader("Histórico de Orçamentos")
    df_hist = conn.read(worksheet="Orcamentos", ttl=0)
    if not df_hist.empty:
        # Agrupamento para não repetir linhas
        resumo = df_hist.groupby(['DATA', 'CLIENTE']).size().reset_index()
        for i, row in resumo.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 3, 1])
                c1.write(row['DATA'])
                c2.write(f"**{row['CLIENTE']}**")
                if c3.button("✏️ Editar / PDF", key=f"h_{i}"):
                    itens_sel = df_hist[(df_hist['CLIENTE'] == row['CLIENTE']) & (df_hist['DATA'] == row['DATA'])]
                    if 'cesta_temp' in st.session_state: del st.session_state.cesta_temp
                    editar_orcamento_dialog(row['CLIENTE'], row['DATA'], itens_sel)

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)