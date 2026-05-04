import re
import os
import sys
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from fpdf import FPDF
import io
from datetime import datetime

def _fonte_ttf(bold=False):
    """Resolve a fonte TTF Unicode com múltiplos fallbacks (Windows e Linux/Cloud)."""
    nome_arial  = "arialbd.ttf"       if bold else "arial.ttf"
    nome_dejavu = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"

    candidatos = []

    # 1. Pasta fonts/ na raiz do projeto (arial local ou dejavu baixado)
    try:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidatos += [
            os.path.join(raiz, "fonts", nome_arial),
            os.path.join(raiz, "fonts", nome_dejavu),
        ]
    except Exception:
        pass

    # 2. Windows — diretório de fontes do sistema
    if sys.platform == "win32":
        candidatos += [
            os.path.join(r"C:\Windows\Fonts", nome_arial),
            os.path.join(r"C:\Windows\Fonts", nome_dejavu),
        ]

    # 3. Linux / Streamlit Cloud — DejaVu instalado via packages.txt
    candidatos += [
        f"/usr/share/fonts/truetype/dejavu/{nome_dejavu}",
        f"/usr/share/fonts/dejavu/{nome_dejavu}",
        f"/usr/share/fonts/truetype/ttf-dejavu/{nome_dejavu}",
    ]

    for caminho in candidatos:
        if os.path.isfile(caminho):
            return caminho

    raise FileNotFoundError(
        f"Fonte Unicode não encontrada. Instale 'fonts-dejavu-core' (Linux) "
        f"ou copie arial.ttf para a pasta fonts/ do projeto."
    )

# Dicionário de palavras portuguesas sem acento → com acento correto
_ACENTOS_PT = {
    # Preposições e conjunções comuns
    "apos": "após", "ate": "até", "alem": "além",
    "atraves": "através", "entao": "então",
    # Verbos / substantivos gerais
    "acao": "ação", "acoes": "ações",
    "atencao": "atenção", "atencoes": "atenções",
    "cancelamento": "cancelamento",
    "composicao": "composição",
    "condicao": "condição", "condicoes": "condições",
    "confirmacao": "confirmação",
    "conexao": "conexão", "conexoes": "conexões",
    "corrosao": "corrosão",
    "dimensao": "dimensão", "dimensoes": "dimensões",
    "especificacao": "especificação", "especificacoes": "especificações",
    "excecao": "exceção",
    "fabricacao": "fabricação",
    "filtracao": "filtração",
    "funcao": "função", "funcoes": "funções",
    "gestao": "gestão",
    "informacao": "informação", "informacoes": "informações",
    "manutencao": "manutenção",
    "numero": "número", "numeros": "números",
    "operacao": "operação", "operacoes": "operações",
    "opcao": "opção", "opcoes": "opções",
    "posicao": "posição",
    "pressao": "pressão", "pressoes": "pressões",
    "protecao": "proteção",
    "reducao": "redução",
    "relacao": "relação",
    "retencao": "retenção",
    "selecao": "seleção",
    "servico": "serviço", "servicos": "serviços",
    "situacao": "situação",
    "solucao": "solução", "solucoes": "soluções",
    "substituicao": "substituição",
    "transmissao": "transmissão",
    "utilizacao": "utilização",
    "vazao": "vazão",
    "vedacao": "vedação",
    "versao": "versão",
    # Adjetivos e termos técnicos
    "carcaca": "carcaça", "carcacas": "carcaças",
    "caracteristica": "característica", "caracteristicas": "características",
    "compativel": "compatível", "compativeis": "compatíveis",
    "diametro": "diâmetro", "diametros": "diâmetros",
    "eficiencia": "eficiência",
    "hidraulico": "hidráulico", "hidraulica": "hidráulica",
    "hidraulicos": "hidráulicos", "hidraulicas": "hidráulicas",
    "maximo": "máximo", "maxima": "máxima", "max": "máx",
    "minimo": "mínimo", "minima": "mínima",
    "micron": "mícron", "microns": "mícrons",
    "oleo": "óleo", "oleos": "óleos",
    "pneumatico": "pneumático", "pneumatica": "pneumática",
    "pneumaticos": "pneumáticos", "pneumaticas": "pneumáticas",
    "tecnico": "técnico", "tecnica": "técnica",
    "tecnicos": "técnicos", "tecnicas": "técnicas",
    "uteis": "úteis",
    "valvula": "válvula", "valvulas": "válvulas",
    # Termos comerciais
    "comercio": "comércio",
    "orcamento": "orçamento", "orcamentos": "orçamentos",
    "proposta": "proposta",
    "prazo": "prazo",
}

def _corrigir_acentos(texto):
    """Aplica acentos ortográficos em texto português digitado sem acentuação."""
    if not texto:
        return texto
    tokens = re.split(r"(\W+)", str(texto))
    resultado = []
    for token in tokens:
        corrigida = _ACENTOS_PT.get(token.lower())
        if corrigida:
            if token.isupper():
                resultado.append(corrigida.upper())
            elif token[0].isupper():
                resultado.append(corrigida[0].upper() + corrigida[1:])
            else:
                resultado.append(corrigida)
        else:
            resultado.append(token)
    return "".join(resultado)

def gerar_pdf_orcamento(cliente, validade, itens, total, obs, vendedor, contato, email, tel):
    # Corrige acentos em todos os campos dinâmicos antes de renderizar
    cliente  = _corrigir_acentos(cliente)
    contato  = _corrigir_acentos(contato)
    obs      = _corrigir_acentos(obs)
    vendedor = _corrigir_acentos(vendedor)
    itens = [
        {**it, "ITEM": _corrigir_acentos(it["ITEM"]), "DETALHES": _corrigir_acentos(it["DETALHES"])}
        for it in itens
    ]

    AZUL    = (26, 58, 107)
    BRANCO  = (255, 255, 255)
    CINZA   = (245, 245, 245)
    ALT_ROW = (235, 242, 255)
    TEXTO   = (40, 40, 40)

    pdf = FPDF()
    pdf.add_page()
    pdf.c_margin = 2
    pdf.add_font("Arial", style="",  fname=_fonte_ttf(bold=False))
    pdf.add_font("Arial", style="B", fname=_fonte_ttf(bold=True))

    def fmt_brl(val):
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    # === CABEÇALHO ===
    _here = os.path.dirname(os.path.abspath(__file__))
    try:
        pdf.image(os.path.join(_here, "LOGO Fundo Branco Puro.png"), x=10, y=8, w=50)
    except:
        pdf.set_font("Arial", "B", 15)
        pdf.set_text_color(*AZUL)
        pdf.text(10, 18, "FILTROS DC")

    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(115, 8)
    pdf.multi_cell(85, 4.5,
        "Filtros DC Comércio Ltda.\nCNPJ 61.696.514/0001-18\n"
        "Rua Nicolau Zarvos, 161 - Jabaquara\n(11) 2592.0025 | www.masterfilter.com.br",
        align="R"
    )

    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.8)
    pdf.line(10, 33, 200, 33)
    pdf.set_line_width(0.2)

    # === DADOS DO CLIENTE ===
    pdf.set_xy(10, 37)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 5, f"DATA: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="R")

    box_y = pdf.get_y() + 2
    pdf.set_fill_color(*CINZA)
    pdf.set_draw_color(210, 215, 225)
    pdf.set_line_width(0.3)
    pdf.rect(10, box_y, 190, 21, style="DF")

    pdf.set_xy(14, box_y + 3)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 6, f"Aos cuidados de: {contato.upper()}", ln=True)

    pdf.set_x(14)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*TEXTO)
    pdf.cell(0, 5, f"Cliente: {cliente}", ln=True)

    pdf.set_x(14)
    pdf.cell(0, 5, f"E-mail: {email}   |   Tel: {tel}", ln=True)

    # === APRESENTAÇÃO ===
    pdf.ln(6)
    pdf.set_font("Arial", "", 9.5)
    pdf.set_text_color(*TEXTO)
    pdf.multi_cell(0, 5.5,
        "Com 36 anos de experiência no mercado de filtragem industrial, a Filtros DC consolida-se "
        "pela excelência técnica e compromisso com a qualidade. Apresentamos abaixo nossa proposta "
        "comercial detalhada, desenvolvida sob medida para atender às necessidades específicas de "
        "sua operação.",
        align="J"
    )

    # === TÍTULO DA PROPOSTA ===
    pdf.ln(4)
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 11, "PROPOSTA COMERCIAL", ln=True, fill=True, align="C")

    # === TABELA - CABEÇALHO ===
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("Arial", "B", 9)
    pdf.set_draw_color(180, 195, 220)
    pdf.cell(110, 8, "Descrição / Especificações Técnicas", border=1, fill=True)
    pdf.cell(15, 8, "Qtd", border=1, align="C", fill=True)
    pdf.cell(33, 8, "Unitário", border=1, align="C", fill=True)
    pdf.cell(32, 8, "Total", border=1, align="C", fill=True)
    pdf.ln()

    # === TABELA - LINHAS ===
    pdf.set_text_color(*TEXTO)
    for i, it in enumerate(itens):
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        row_fill = ALT_ROW if i % 2 else BRANCO
        pdf.set_fill_color(*row_fill)
        pdf.set_font("Arial", "", 9)

        linha = f"**{it['ITEM']}**"
        if it['DETALHES']:
            linha += f"\n{it['DETALHES']}"

        pdf.multi_cell(110, 5, linha, border=1, fill=True, markdown=True)
        y1 = pdf.get_y()
        h = y1 - y0

        pdf.set_xy(x0 + 110, y0)
        pdf.set_font("Arial", "", 9)
        pdf.set_fill_color(*row_fill)
        pdf.cell(15, h, str(it['QTD']), border=1, align="C", fill=True)
        pdf.cell(33, h, fmt_brl(it['UNIT']), border=1, align="R", fill=True)
        pdf.cell(32, h, fmt_brl(it['TOTAL']), border=1, align="R", fill=True)
        pdf.set_xy(x0, y1)

    # === VALOR TOTAL ===
    pdf.ln(4)
    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.5)
    pdf.set_fill_color(*CINZA)
    pdf.set_text_color(*AZUL)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(158, 10, "VALOR TOTAL DA PROPOSTA:", align="R", fill=True, border="TBL")
    pdf.cell(32, 10, fmt_brl(total), align="R", fill=True, border="TBR", ln=True)
    pdf.set_line_width(0.2)

    # === CONDIÇÕES GERAIS ===
    pdf.ln(6)
    pdf.set_fill_color(*CINZA)
    pdf.set_draw_color(210, 215, 225)
    pdf.set_line_width(0.3)
    pdf.set_text_color(*AZUL)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "CONDIÇÕES GERAIS:", ln=True, fill=True, border=1)

    pdf.ln(2)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*TEXTO)
    pdf.multi_cell(0, 5, obs)

    # === ASSINATURA ===
    pdf.ln(8)
    try:
        pdf.image(os.path.join(_here, "Assinatura Chiodo.jpg"), x=70, w=65)
    except:
        pdf.ln(10)
        pdf.set_draw_color(*AZUL)
        pdf.set_line_width(0.4)
        pdf.line(65, pdf.get_y(), 145, pdf.get_y())
        pdf.ln(2)


    return pdf.output()


# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Orçamentos | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

perfil_usuario = st.session_state.get('perfil', 'VENDEDOR').upper().strip()

# Inicialização da Cesta de Orçamento
if 'cesta_orc' not in st.session_state: st.session_state.cesta_orc = []
if 'idx_o' not in st.session_state: st.session_state.idx_o = 0

ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_C = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Clientes"
URL_P = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Produtos"

def limpar_colunas(df):
    # Remove aspas e espaços dos nomes das colunas e coloca em MAIÚSCULO
    df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
    return df

@st.cache_data(ttl=2)
def carregar():
    try:
        # Lemos os CSVs diretamente
        c = pd.read_csv(URL_C)
        p = pd.read_csv(URL_P)
        return limpar_colunas(c), limpar_colunas(p)
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_cli, df_prod = carregar()

st.title("📄 Novo Orçamento")

# --- LOGICA DE NUMERAÇÃO E STATUS ---
df_hist_base = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
df_hist_base.columns = [str(c).strip().upper() for c in df_hist_base.columns]

# Calcula o próximo número disponível
if not df_hist_base.empty and 'NUMERO' in df_hist_base.columns:
    ultimo_num = pd.to_numeric(df_hist_base['NUMERO'], errors='coerce').max()
    prox_num = int(ultimo_num + 1) if not pd.isna(ultimo_num) else 1
else:
    prox_num = 1

# Session state para controlar o número atual que estamos usando
if 'num_orc_atual' not in st.session_state:
    st.session_state.num_orc_atual = prox_num

# --- BUSCA E EDIÇÃO DE ORÇAMENTOS ---
with st.expander("🔍 BUSCAR / EDITAR ORÇAMENTO EXISTENTE",
                 expanded=bool(st.session_state.get('editando_orc'))):

    if df_hist_base.empty:
        st.info("Nenhum orçamento cadastrado ainda.")
    else:
        col_f, col_s = st.columns([3, 1])
        busca_orc   = col_f.text_input("Filtrar por cliente ou nº:", placeholder="Ex: HOTEL  ou  42")
        status_orc  = col_s.selectbox("Status:", ["TODOS", "ABERTO", "PERDIDO", "CANCELADO"])

        df_edit = df_hist_base[df_hist_base['STATUS'].isin(
            ['ABERTO', 'PERDIDO', 'CANCELADO'] if status_orc == "TODOS" else [status_orc]
        )].copy()

        if busca_orc:
            mask = (df_edit['CLIENTE'].astype(str).str.contains(busca_orc.upper(), na=False) |
                    df_edit['NUMERO'].astype(str).str.contains(busca_orc, na=False))
            df_edit = df_edit[mask]

        df_uniq = df_edit.drop_duplicates(subset=['NUMERO'])
        df_uniq['OPCAO'] = ("Nº " + df_uniq['NUMERO'].astype(str) +
                            " | " + df_uniq['CLIENTE'].astype(str) +
                            " | " + df_uniq.get('DATA', pd.Series([""] * len(df_uniq))).astype(str) +
                            " (" + df_uniq['STATUS'] + ")")
        lista_orc = sorted(df_uniq['OPCAO'].tolist(), reverse=True)

        if not lista_orc:
            st.warning("Nenhum orçamento encontrado com esses filtros.")
        else:
            orc_sel = st.selectbox("Selecione o orçamento:", [""] + lista_orc, key="sel_edit_orc")

            if orc_sel:
                num_prev = orc_sel.split(" | ")[0].replace("Nº ", "").strip()
                df_prev  = df_hist_base[df_hist_base['NUMERO'].astype(str).str.strip() == num_prev]
                if not df_prev.empty:
                    cab  = df_prev.iloc[0]
                    tot  = pd.to_numeric(df_prev['VALOR TOTAL'], errors='coerce').sum()
                    itns = " | ".join(df_prev['PRODUTO'].dropna().astype(str).tolist())
                    st.markdown(f"**Cliente:** {cab['CLIENTE']}  •  **Data:** {cab.get('DATA','')}  •  "
                                f"**Total:** R$ {tot:,.2f}".replace(',','X').replace('.',',').replace('X','.'))
                    st.caption(f"Itens: {itns}")

                if st.button("📂 CARREGAR PARA EDIÇÃO", use_container_width=True, type="primary"):
                    num_sel    = orc_sel.split(" | ")[0].replace("Nº ", "").strip()
                    itens_salvos = df_hist_base[df_hist_base['NUMERO'].astype(str).str.strip() == num_sel]
                    if not itens_salvos.empty:
                        cab = itens_salvos.iloc[0]
                        st.session_state.num_orc_atual  = int(float(num_sel))
                        st.session_state.contato_orc    = str(cab.get('CONTATO', ""))
                        st.session_state.email_orc      = str(cab.get('EMAIL', ""))
                        st.session_state.tel_orc        = str(cab.get('TELEFONE', ""))
                        if 'NOME REDUZIDO' in df_cli.columns:
                            nomes = sorted(df_cli['NOME REDUZIDO'].astype(str).unique().tolist())
                            if cab['CLIENTE'] in nomes:
                                st.session_state.idx_o = nomes.index(cab['CLIENTE'])
                        st.session_state.cesta_orc = [
                            {
                                "ITEM":    linha["PRODUTO"],
                                "DETALHES": str(linha["DETALHES"]).upper() if str(linha["DETALHES"]) != 'nan' else "",
                                "QTD":     int(linha["QT"]),
                                "UNIT":    float(linha["VALOR UNITARIO"]),
                                "TOTAL":   float(linha["VALOR TOTAL"]),
                            }
                            for _, linha in itens_salvos.iterrows()
                        ]
                        st.session_state.editando_orc = {'NUMERO': num_sel}
                        st.success(f"✅ Orçamento Nº {num_sel} carregado para edição!")
                        st.rerun()

st.info(f"📍 **ORÇAMENTO ATUAL: Nº {st.session_state.num_orc_atual}**")

# --- 1. CLIENTE ---
st.subheader("1. Identificação do Cliente")
c_b, c_l = st.columns([3, 1])
busca = c_b.text_input("Buscar cliente por nome", placeholder="Ex: HOTEL")
# Novos campos para preenchimento manual ou automático
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1: 
    # Agora o campo 'lê' o que foi carregado no session_state
    contato_orc = st.text_input("Aos cuidados de (Nome):", 
                                value=st.session_state.get('contato_orc', ""), 
                                placeholder="Sr. João")
with col_c2: 
    email_orc = st.text_input("E-mail de contato:", 
                              value=st.session_state.get('email_orc', ""))
with col_c3: 
    tel_orc = st.text_input("Telefone/WhatsApp:", 
                            value=st.session_state.get('tel_orc', ""))


# Forçamos a busca pela coluna exata 'NOME'
if 'NOME REDUZIDO' in df_cli.columns:
    # Criamos a lista garantindo que sejam apenas os nomes (texto)
    lista_nomes = df_cli['NOME REDUZIDO'].astype(str).unique().tolist()
    lista_nomes = sorted([n for n in lista_nomes if n not in ['nan', 'None', '0', '1']])
    
    if c_l.button("🔍 Buscar"):
        # Filtra a lista pelo que foi digitado
        match = [n for n in lista_nomes if busca.upper() in n.upper()]
        if match: 
            st.session_state.idx_o = lista_nomes.index(match[0])
            st.rerun() # Força a atualização para selecionar o nome encontrado
        else: 
            st.warning("Cliente não encontrado.")

    col1, col2 = st.columns([3, 1])
    
    # IMPORTANTE: O selectbox usa a lista_nomes que só tem texto agora
    cliente_orc = col1.selectbox(
        "Confirme o Cliente", 
        options=lista_nomes, 
        index=st.session_state.idx_o if st.session_state.idx_o < len(lista_nomes) else 0
    )
    validade_orc = col2.date_input("Válido até", datetime.now(), format="DD/MM/YYYY")
else:
    # Se não achar 'NOME', ele mostra as colunas disponíveis para você conferir
    st.error(f"Coluna 'NOME' não encontrada. Colunas disponíveis: {list(df_cli.columns)}")
    st.stop()

# --- 2. PRODUTOS COM DETALHES ---
st.subheader("2. Itens do Orçamento")

# AJUSTE 2: Busca pelas colunas exatas
col_prod = "NOME" if "NOME" in df_prod.columns else next((c for c in df_prod.columns if 'DESCRI' in c or 'PRODUTO' in c), None)
col_preco = "PRECO" if "PRECO" in df_prod.columns else next((c for c in df_prod.columns if 'LISTA' in c or 'VALOR' in c), None)

if col_prod and col_preco:
    with st.container(border=True):
        c3, c4, c5 = st.columns([2, 1, 1])
        
        # 1. Lista de Produtos
        lista_prods = df_prod[col_prod].dropna().unique().tolist()
        prod_sel = c3.selectbox("Produto", options=[""] + lista_prods) # Adicionei o vazio para começar limpo
        
        # 2. Inicialização de variáveis de busca
        preco_unit = 0.0
        caract_sugerida = ""
        
        # 3. Busca de Dados na Planilha (Preço e Característica)
        if prod_sel != "":
            linha_prod = df_prod[df_prod[col_prod] == prod_sel]
            if not linha_prod.empty:
                # Busca Preço
                p_bruto = linha_prod[col_preco].values[0]
                if isinstance(p_bruto, str): 
                    p_bruto = p_bruto.replace('.', '').replace(',', '.')
                try:
                    preco_unit = float(p_bruto)
                except:
                    preco_unit = 0.0
                
                # Busca Característica (IMPORTANTE: Não zerar depois daqui!)
                val = linha_prod.iloc[0].get('CARACTERISTICAS', '')
                caract_sugerida = str(val) if str(val) != 'nan' else ""

        # 4. Campos de Entrada de Usuário
        qtd = c4.number_input("QTD", min_value=1, value=1)
        # O value do preço unitário agora é o preco_unit que buscamos acima
        valor_u = c5.number_input("Preço Unit (R$)", min_value=0.0, value=preco_unit, format="%.2f")
        
        # 5. Área de Detalhes Técnicos (Fora de IFs extras para evitar erros)
        detalhes_item = st.text_area(
            "🔧 Detalhes Técnicos deste Item", 
            value=caract_sugerida, 
            height=150,
            placeholder="As características aparecerão aqui automaticamente..."
        )

        if st.button("➕ ADICIONAR AO ORÇAMENTO", use_container_width=True):
            st.session_state.cesta_orc.append({
                "ITEM": prod_sel,
                "DETALHES": detalhes_item.upper(),
                "QTD": qtd,
                "UNIT": valor_u,
                "TOTAL": qtd * valor_u
            })
            st.rerun()
else:
    st.error(f"Erro: Colunas de produto não identificadas. Colunas atuais: {list(df_prod.columns)}")

# --- 3. RESUMO E GRAVAÇÃO ---
if st.session_state.cesta_orc:
    st.write("### 📝 Resumo da Proposta")
    for i, item in enumerate(st.session_state.cesta_orc):
        with st.container(border=True):
            cols = st.columns([4, 1, 1, 1])
            cols[0].write(f"**{i+1}. {item['ITEM']}**")
            if item['DETALHES']:
                cols[0].caption(f"Especificações: {item['DETALHES']}")
            cols[0].write(f"R$ {item['UNIT']:,.2f} x {item['QTD']} = **R$ {item['TOTAL']:,.2f}**")
            
            if cols[1].button("➖", key=f"mo_{i}"):
                if item['QTD'] > 1:
                    st.session_state.cesta_orc[i]['QTD'] -= 1
                    st.session_state.cesta_orc[i]['TOTAL'] = st.session_state.cesta_orc[i]['QTD'] * item['UNIT']
                else: st.session_state.cesta_orc.pop(i)
                st.rerun()
            if cols[2].button("➕", key=f"po_{i}"):
                st.session_state.cesta_orc[i]['QTD'] += 1
                st.session_state.cesta_orc[i]['TOTAL'] = st.session_state.cesta_orc[i]['QTD'] * item['UNIT']
                st.rerun()
            if cols[3].button("🗑️", key=f"do_{i}"):
                st.session_state.cesta_orc.pop(i)
                st.rerun()

    total_geral = sum(it['TOTAL'] for it in st.session_state.cesta_orc)
    st.info(f"#### 💰 VALOR TOTAL: R$ {total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    obs_gerais = st.text_area("📝 Condições Gerais", "PAGAMENTO: 30 DIAS | ENTREGA: 05 DIAS ÚTEIS | FRETE: FOB").upper()

    # --- BLOCO DE FOLLOW-UP (AÇÕES RÁPIDAS) ---
    if 'editando_orc' in st.session_state:
        st.divider()
        st.subheader("🏁 Finalizar Negociação (Follow-up)")
        st.caption(f"Alterar status do orçamento Nº {st.session_state.num_orc_atual}")
        
        c_p, c_c = st.columns(2)
        
        motivo = st.text_input("Motivo (Opcional):", placeholder="Ex: Cliente achou caro / Fechou com concorrente")

        if c_p.button("❌ MARCAR COMO PERDIDO", use_container_width=True):
            try:
                df_follow = conn.read(worksheet="Orcamentos", ttl=0)
                num_f = str(st.session_state.num_orc_atual)
                
                # Atualiza o status na planilha
                df_follow.loc[df_follow['NUMERO'].astype(str) == num_f, 'STATUS'] = "PERDIDO"
                # Opcional: Salva o motivo nos Detalhes ou Condições se desejar
                
                conn.update(worksheet="Orcamentos", data=df_follow)
                st.error(f"Orçamento {num_f} marcado como PERDIDO.")
                
                # Limpa a tela
                st.session_state.cesta_orc = []
                if 'editando_orc' in st.session_state: del st.session_state.editando_orc
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

        if c_c.button("🚫 MARCAR COMO CANCELADO", use_container_width=True):
            try:
                df_follow = conn.read(worksheet="Orcamentos", ttl=0)
                num_f = str(st.session_state.num_orc_atual)
                
                df_follow.loc[df_follow['NUMERO'].astype(str) == num_f, 'STATUS'] = "CANCELADO"
                
                conn.update(worksheet="Orcamentos", data=df_follow)
                st.warning(f"Orçamento {num_f} marcado como CANCELADO.")
                
                # Limpa a tela
                st.session_state.cesta_orc = []
                if 'editando_orc' in st.session_state: del st.session_state.editando_orc
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

    # --- INSERIR O BLOCO DO PDF AQUI (Entre a 153 e 154) ---
    # --- INSERIR O BLOCO DO PDF AQUI ---
    try:
       # 1. Gera o conteúdo bruto (bytearray)
        pdf_bruto = gerar_pdf_orcamento(
            cliente_orc, 
            validade_orc, 
            st.session_state.cesta_orc, 
            total_geral, 
            obs_gerais, 
            st.session_state.get('usuario', 'SISTEMA'),
            contato_orc,  # <--- 
            email_orc,    # <--- 
            tel_orc       # <--- 
        )
        
        # 2. O SEGREDO: Converte o bytearray em um formato que o botão entende (bytes)
        pdf_final = bytes(pdf_bruto)

        # 3. Botão de download atualizado
        st.download_button(
            label="📥 BAIXAR ORÇAMENTO EM PDF",
            data=pdf_final,
            file_name=f"Orcamento_{cliente_orc}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Erro ao gerar visualização do PDF: {e}")

    if st.button("💾 SALVAR ORÇAMENTO NA PLANILHA", use_container_width=True, type="primary"):
        try:
            vendedor = st.session_state.get('usuario', 'SISTEMA')
            df_atual = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
            
            # --- SE ESTIVER EDITANDO: Marcar o anterior como EDITADO ---
            if 'editando_orc' in st.session_state:
                num_edicao = st.session_state.editando_orc['NUMERO']
                # Mudamos o status de todas as linhas que tinham aquele número antigo
                df_atual.loc[df_atual['NUMERO'].astype(str) == str(num_edicao), 'STATUS'] = "EDITADO"

            # --- CRIAR AS NOVAS LINHAS (Nova Versão ABERTA) ---
            novas_linhas = []
            for it in st.session_state.cesta_orc:
                novas_linhas.append({
                    "NUMERO": st.session_state.num_orc_atual, # O mesmo número se for edição, ou novo se for novo
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "VALIDADE": validade_orc.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente_orc,
                    "PRODUTO": it["ITEM"],
                    "QT": it["QTD"],
                    "VALOR UNITARIO": it["UNIT"],
                    "VALOR TOTAL": it["TOTAL"],
                    "VENDEDOR": vendedor,
                    "CONDICOES GERAIS": obs_gerais,
                    "DETALHES": it["DETALHES"],
                    "STATUS": "ABERTO" # Sempre entra aberto
                })
            
            df_novos = pd.DataFrame(novas_linhas)
            df_final = pd.concat([df_atual, df_novos], ignore_index=True)
            conn.update(worksheet="Orcamentos", data=df_final)
            
            st.success(f"✅ ORÇAMENTO Nº {st.session_state.num_orc_atual} SALVO!")
            
            # Limpa tudo para o próximo
            st.session_state.cesta_orc = []
            if 'editando_orc' in st.session_state: del st.session_state.editando_orc
            st.session_state.num_orc_atual = prox_num + 1 # Reseta para o próximo número livre
            
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro técnico ao salvar: {e}")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)