import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado!")
    st.stop()

st.set_page_config(page_title="Clientes | Filtros DC", layout="wide")

# 2. CONFIGURAÇÃO DE CONEXÃO
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_LEITURA = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/gviz/tq?tqx=out:csv&sheet=Clientes"

# Conexão para SALVAR
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados():
    try:
        df = pd.read_csv(URL_LEITURA)
        df.columns = [c.replace('"', '').strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

@st.dialog("📝 Ficha Completa do Cliente")
def editar_cliente_dialog(indice, dados):
    st.markdown(f"### Registro: {dados['NR CLIENTE']}")
    
    # --- DADOS PRINCIPAIS (BLOQUEADOS) ---
    c1, c2 = st.columns(2)
    c1.text_input("RAZÃO SOCIAL", value=dados['RAZAO SOCIAL'], disabled=True)
    c2.text_input("CNPJ", value=dados['CNPJ'], disabled=True)
    
    # --- DADOS EDITÁVEIS (CONTATO) ---
    c3, c4, c5 = st.columns([2, 2, 1])
    novo_fantasia = c3.text_input("NOME REDUZIDO", value=dados['NOME REDUZIDO'])
    novo_email = c4.text_input("EMAIL", value=dados['EMAIL'])
    novo_tel = c5.text_input("TELEFONE", value=dados['TELEFONE'])
    
    # --- ENDEREÇO ---
    st.divider()
    c6, c7, c8 = st.columns([3, 1, 2])
    novo_rua = c6.text_input("RUA", value=dados['RUA'])
    novo_num = c7.text_input("Nº", value=dados['NUMERO'])
    novo_bairro = c8.text_input("BAIRRO", value=dados['BAIRRO'])
    
    c9, c10, c11 = st.columns([2, 1, 2])
    novo_mun = c9.text_input("MUNICÍPIO", value=dados['MUNICIPIO'])
    novo_uf = c10.text_input("UF", value=dados['UF'], max_chars=2)
    novo_cep = c11.text_input("CEP", value=dados['CEP'])
    
    # --- NOVO CAMPO: HISTÓRICO DE AÇÕES ---
    st.divider()
    st.markdown("📋 **Histórico de Interações / Ações Tratadas**")
    # Pega o histórico antigo ou deixa vazio se for a primeira vez
    hist_antigo = str(dados.get('HISTORICO', '')) if str(dados.get('HISTORICO', '')) != 'nan' else ""
    novo_historico = st.text_area("Notas do Comercial", value=hist_antigo, height=150, 
                                  placeholder="Ex: 12/03/2026 - Cliente solicitou orçamento de filtros de carvão...")

    if st.button("💾 ATUALIZAR FICHA DO CLIENTE", use_container_width=True):
        try:
            df_full = conn.read(worksheet="Clientes", ttl=0)
            
            # Mapeando as atualizações
            df_full.at[indice, 'NOME REDUZIDO'] = novo_fantasia
            df_full.at[indice, 'EMAIL'] = novo_email
            df_full.at[indice, 'TELEFONE'] = novo_tel
            df_full.at[indice, 'RUA'] = novo_rua
            df_full.at[indice, 'NUMERO'] = novo_num
            df_full.at[indice, 'BAIRRO'] = novo_bairro
            df_full.at[indice, 'MUNICIPIO'] = novo_mun
            df_full.at[indice, 'UF'] = novo_uf
            df_full.at[indice, 'CEP'] = novo_cep
            df_full.at[indice, 'HISTORICO'] = novo_historico
            
            conn.update(worksheet="Clientes", data=df_full)
            st.success("Ficha atualizada com sucesso!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# --- INTERFACE ---
st.title("👥 Gestão de Clientes - Filtros DC")

# Criando as abas
aba1, aba2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])

df_clientes = carregar_dados()

# --- CONTEÚDO DA ABA 1 (LISTA) ---
with aba1:
    if not df_clientes.empty:
        # Busca aprimorada
        busca = st.text_input("🔍 Buscar por Nome, CNPJ ou Cidade...", placeholder="Digite para filtrar...")
        
        # Filtro lógico
        if busca:
            mask = df_clientes.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)
            df_exibir = df_clientes[mask]
        else:
            df_exibir = df_clientes

        st.write(f"Exibindo {len(df_exibir)} clientes")
        st.divider()

        # Layout de "Cards" ou Tabela com botão
        # Para um visual bem "comercial", vamos usar colunas para simular uma tabela com botão
        cols = st.columns([1, 3, 2, 2, 1])
        cols[0].markdown("**ID**")
        cols[1].markdown("**CLIENTE**")
        cols[2].markdown("**CNPJ/CPF**")
        cols[3].markdown("**CONTATO**")
        cols[4].markdown("**AÇÃO**")
        st.divider()

        for i, row in df_exibir.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 1])
                c1.write(row['NR CLIENTE'])
                c2.write(f"**{row['NOME REDUZIDO']}**")
                c3.write(row['CNPJ'] if str(row['CNPJ']) != 'nan' else row['CPF'])
                c4.write(row['TELEFONE'])
                
                # Botão para abrir o Popup de edição
                if c5.button("✏️ Ver/Edit", key=f"edit_{i}"):
                    editar_cliente_dialog(i, row)
                st.divider()
    else:
        st.info("Nenhum cliente cadastrado.")

# --- CONTEÚDO DA ABA 2 (CADASTRO) ---
with aba2:
    st.subheader("Ficha de Cadastro de Cliente")
    
    # LÓGICA DO ID (NR CLIENTE)
    proximo_nr = 1
    if not df_clientes.empty and 'NR CLIENTE' in df_clientes.columns:
        ultimo_nr = pd.to_numeric(df_clientes['NR CLIENTE'], errors='coerce').max()
        if not pd.isna(ultimo_nr):
            proximo_nr = int(ultimo_nr + 1)
    
    id_formatado = str(proximo_nr).zfill(4)

    # FORMULÁRIO (Todo o bloco abaixo está recuado para ficar DENTRO da aba2)
    with st.form("form_cliente_completo", clear_on_submit=True):
        st.warning(f"📌 Próximo Registro: **NR CLIENTE {id_formatado}**")
        
        c1, c2, c3 = st.columns([1, 2, 2])
        tipo = c1.selectbox("TIPO", ["Pessoa Juridica", "Pessoa Fisica"])
        nome_reduzido = c2.text_input("NOME REDUZIDO (Fantasia) *")
        razao_social = c3.text_input("RAZAO SOCIAL *")

        c4, c5, c6, c7, c8 = st.columns([1.5, 2, 1.5, 1.5, 1.5])
        telefone = c4.text_input("TELEFONE")
        email = c5.text_input("EMAIL")
        cpf = c6.text_input("CPF")
        cnpj = c7.text_input("CNPJ")
        inscricao = c8.text_input("INSCRIÇÃO MUNICIPAL")

        c9, c10, c11 = st.columns([3, 1, 2])
        rua = c9.text_input("RUA")
        numero = c10.text_input("NUMERO")
        bairro = c11.text_input("BAIRRO")

        c12, c13, c14, c15 = st.columns([2, 1, 2, 1.5])
        municipio = c12.text_input("MUNICIPIO")
        uf = c13.text_input("UF", max_chars=2)
        complemento = c14.text_input("COMPLEMENTO")
        cep = c15.text_input("CEP")

        # BOTÃO DE SALVAR (Recuado para ficar DENTRO do formulário)
        botao_salvar = st.form_submit_button("✅ SALVAR CLIENTE NA NUVEM", use_container_width=True)

        if botao_salvar:
            if not nome_reduzido or not razao_social:
                st.error("Campos com * são obrigatórios!")
            else:
                try:
                    # Preparar os dados para salvar
                    novo_cliente = {
                        "NR CLIENTE": id_formatado,
                        "TIPO": tipo,
                        "NOME REDUZIDO": nome_reduzido,
                        "RAZAO SOCIAL": razao_social,
                        "TELEFONE": telefone,
                        "EMAIL": email,
                        "CPF": cpf,
                        "CNPJ": cnpj,
                        "INSCRICAO MUNICIPAL": inscricao,
                        "RUA": rua,
                        "NUMERO": numero,
                        "BAIRRO": bairro,
                        "MUNICIPIO": municipio,
                        "UF": uf,
                        "COMPLEMENTO": complemento,
                        "CEP": cep
                    }
                    
                    # Adicionar ao DataFrame
                    df_novo = pd.DataFrame([novo_cliente])
                    df_final = pd.concat([df_clientes, df_novo], ignore_index=True)
                    
                    # Salvar na planilha
                    conn.update(worksheet="Clientes", data=df_final)
                    
                    st.success(f"🎉 Cliente {id_formatado} salvo com sucesso!")
                    st.balloons()
                    st.cache_data.clear() 
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}. Verifique as permissões do seu arquivo secrets.toml.")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)