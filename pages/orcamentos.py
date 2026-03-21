import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from fpdf import FPDF
import io
from datetime import datetime

def gerar_pdf_orcamento(cliente, validade, itens, total, obs, vendedor, contato, email, tel):
    pdf = FPDF()
    pdf.add_page()

  
    # Função para evitar erro de caracteres (Hífen longo, etc)
    
    #def clean(txt):
        #if not txt: return ""
       # return str(txt).replace('—', '-').replace('–', '-').replace('“', '"').replace('”', '"')

    # --- 1. Função de limpeza (Coloque isso no topo da função do PDF ou antes de usar) ---
    def limpar_para_pdf(texto):
        if not texto: return ""
        # Troca o símbolo R$ por RS, remove acentos e caracteres especiais que travam a Helvetica
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', str(texto))
        texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)])
        return texto_limpo.replace("R$", "RS").encode('ascii', 'ignore').decode('ascii')
    def clean(txt):
        return limpar_para_pdf(txt)

    # --- 2. Aplicação no Total ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)

    # Formatamos o valor (1.350,00)
    valor_formatado = f"RS {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    #pdf.cell(147, 10, limpar_para_pdf("VALOR TOTAL DA PROPOSTA:"), align="R")
    #pdf.cell(43, 10, valor_formatado, align="R", ln=True)

    # --- 3. Aplicação nas Condições Gerais ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    #pdf.cell(0, 5, limpar_para_pdf("CONDICOES GERAIS:"), ln=True)

    pdf.set_font("Helvetica", "", 9)
    # Aqui limpamos as observações para o PDF não travar
    #pdf.multi_cell(0, 5, limpar_para_pdf(obs))


    # --- 1. CABEÇALHO ---
    try:
        pdf.image("LOGO Fundo Branco Puro.png", x=10, y=8, w=50)
    except:
        pdf.set_font("Helvetica", "B", 15)
        pdf.text(10, 15, "FILTROS DC")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(130, 10)
    end_dc = "Filtros DC Comercio Ltda.\nCNPJ 61.696.514/0001-18\nRua Nicolau Zarvos, 161 - Jabaquara\n(11) 2592.0025 | www.masterfilter.com.br"
    pdf.multi_cell(70, 4, clean(end_dc), align="R")
    
    pdf.ln(15)
    pdf.line(10, 32, 200, 32)

    # --- 2. DADOS DO CLIENTE ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, f"DATA: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="R")
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Aos cuidados: {clean(contato).upper()}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Cliente: {clean(cliente)}", ln=True)
    pdf.cell(0, 6, f"E-mail: {clean(email)} | Tel: {clean(tel)}", ln=True)
    
   
    # --- NOVO: TEXTO DE APRESENTAÇÃO (36 ANOS) ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    texto_intro = (
        "Com 36 anos de experiência no mercado de filtragem industrial, a Filtros DC consolida-se pela "
        "excelência técnica e compromisso com a qualidade. Apresentamos abaixo nossa proposta comercial "
        "detalhada, desenvolvida sob medida para atender às necessidades específicas de sua operação."
    )
    pdf.multi_cell(0, 5, clean(texto_intro), align="J") # "J" para justificado
    pdf.ln(5)

         # --- TÍTULO DA PROPOSTA ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "PROPOSTA COMERCIAL", ln=True, align="C", fill=True)

    # --- 3. TABELA DE PRODUTOS (Recuperada e Ampliada) ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(130, 8, "Descrição / Especificações Técnicas", border=1, fill=True)
    pdf.cell(10, 8, "Qtd", border=1, align="C", fill=True)
    pdf.cell(25, 8, "Unitário", border=1, align="C", fill=True)
    pdf.cell(25, 8, "Total", border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for it in itens:
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Descrição com MultiCell para as especificações técnicas
        pdf.multi_cell(130, 5, clean(f"{it['ITEM']}\n{it['DETALHES']}"), border=1)
        y_end = pdf.get_y()
        h_linha = y_end - y_start
        
        # Colunas laterais
        pdf.set_xy(x_start + 130, y_start)
        pdf.cell(10, h_linha, str(it['QTD']), border=1, align="C")
        
        u = f"R$ {it['UNIT']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        t = f"R$ {it['TOTAL']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        pdf.cell(25, h_linha, u, border=1, align="R")
        pdf.cell(25, h_linha, t, border=1, align="R")
        pdf.ln()

   # --- 4. TOTAL E CONDIÇÕES GERAIS ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    
    # Formatamos o valor e garantimos que a string seja compatível com a fonte
    tot_br = f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    # Tratamento para evitar o erro 'latin-1' no valor total
    tot_safe = tot_br.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.cell(147, 10, "VALOR TOTAL DA PROPOSTA:", align="R")
    pdf.cell(43, 10, tot_safe, align="R", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "CONDIÇÕES GERAIS:", ln=True)
    
    pdf.set_font("Helvetica", "", 9)
    
    # Tratamento para evitar erro nas observações (acentos e caracteres especiais)
    obs_limpa = clean(obs).encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, obs_limpa)
    # --- 5. ASSINATURA ---
    pdf.ln(10)
    try:
        # Centralizando a imagem da assinatura
        pdf.image("Assinatura Chiodo.jpg", x=70, w=65) 
    except:
        pdf.ln(10)
        pdf.cell(0, 5, "________________________________________________", ln=True, align="C")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, f"Vendedor: {clean(vendedor)} - Filtros DC", ln=True, align="C")

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

# --- INÍCIO DO BLOCO DE BUSCA E EDIÇÃO ---
with st.expander("🔍 BUSCAR ORÇAMENTO ANTIGO PARA EDITAR", expanded=False):
    if not df_hist_base.empty:
        # Filtramos para mostrar apenas o que faz sentido editar
        df_editavel = df_hist_base[df_hist_base['STATUS'].isin(['ABERTO', 'PERDIDO', 'CANCELADO'])]
        
        df_editavel['OPCAO'] = "Nº " + df_editavel['NUMERO'].astype(str) + " | " + df_editavel['CLIENTE'].astype(str) + " (" + df_editavel['STATUS'] + ")"
        lista_orc = sorted(df_editavel['OPCAO'].unique().tolist(), reverse=True)
        orc_escolhido = st.selectbox("Selecione um orçamento salvo:", [""] + lista_orc)
        
if orc_escolhido != "":
        if st.button("📂 CARREGAR DADOS NO FORMULÁRIO", use_container_width=True):
            # 1. Tratamento do Número (Tudo dentro do 1º IF do botão)
            num_sel = orc_escolhido.split(" | ")[0].replace("Nº ", "")
            st.session_state.num_orc_atual = int(float(num_sel)) 
        
            # 2. Localiza o orçamento
            itens_salvos = df_hist_base[df_hist_base['NUMERO'].astype(str).str.contains(num_sel)]
        
            if not itens_salvos.empty:
                dados_cabecalho = itens_salvos.iloc[0]
            
                # 3. Carrega dados do orçamento para o session_state
                st.session_state.cliente_selecionado = dados_cabecalho['CLIENTE']
                st.session_state.contato_orc = str(dados_cabecalho.get('CONTATO', ""))
                st.session_state.email_orc = str(dados_cabecalho.get('EMAIL', ""))
                st.session_state.tel_orc = str(dados_cabecalho.get('TELEFONE', ""))
            
                # 4. Sincroniza o índice do Selectbox do Cliente
                if 'NOME REDUZIDO' in df_cli.columns:
                    lista_nomes = sorted(df_cli['NOME REDUZIDO'].astype(str).unique().tolist())
                    if dados_cabecalho['CLIENTE'] in lista_nomes:
                        st.session_state.idx_o = lista_nomes.index(dados_cabecalho['CLIENTE'])

                # 5. Carrega a cesta de itens (Também dentro do IF do botão)
                st.session_state.cesta_orc = []
                for _, linha in itens_salvos.iterrows():
                    st.session_state.cesta_orc.append({
                        "ITEM": linha["PRODUTO"],
                        "DETALHES": str(linha["DETALHES"]).upper() if str(linha["DETALHES"]) != 'nan' else "",
                        "QTD": int(linha["QT"]),
                        "UNIT": float(linha["VALOR UNITARIO"]),
                        "TOTAL": float(linha["VALOR TOTAL"])
                    })
                
                # 6. Finalização e Recarregamento
                st.success(f"Orçamento Nº {num_sel} carregado!")
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