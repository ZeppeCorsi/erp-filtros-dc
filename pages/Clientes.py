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

@st.dialog("📝 Editar Ficha do Cliente")
def editar_cliente_dialog(indice, dados):
    st.write(f"Editando Registro: **{dados['NR CLIENTE']}**")
    
    # Campos que PODEM ser editados
    c1, c2 = st.columns(2)
    novo_nome_fantasia = c1.text_input("NOME REDUZIDO (Fantasia)", value=dados['NOME REDUZIDO'])
    novo_tipo = c2.selectbox("TIPO", ["Pessoa Juridica", "Pessoa Fisica"], index=0 if dados['TIPO'] == "Pessoa Juridica" else 1)
    
    # Campos TRAVADOS (não podem editar CNPJ nem Razão Social)
    st.text_input("RAZÃO SOCIAL (Protegido)", value=dados['RAZAO SOCIAL'], disabled=True)
    st.text_input("CNPJ/CPF (Protegido)", value=dados['CNPJ'] if str(dados['CNPJ']) != 'nan' else dados['CPF'], disabled=True)
    
    # Outros campos de contato/endereço
    c3, c4 = st.columns(2)
    novo_tel = c3.text_input("TELEFONE", value=dados['TELEFONE'])
    novo_email = c4.text_input("EMAIL", value=dados['EMAIL'])
    
    novo_rua = st.text_input("RUA", value=dados['RUA'])
    
    if st.button("💾 ATUALIZAR CADASTRO", use_container_width=True):
        try:
            df_full = conn.read(worksheet="Clientes", ttl=0)
            # Atualiza os valores permitidos usando o índice
            df_full.at[indice, 'NOME REDUZIDO'] = novo_nome_fantasia
            df_full.at[indice, 'TIPO'] = novo_tipo
            df_full.at[indice, 'TELEFONE'] = novo_tel
            df_full.at[indice, 'EMAIL'] = novo_email
            df_full.at[indice, 'RUA'] = novo_rua
            
            conn.update(worksheet="Clientes", data=df_full)
            st.success("Dados atualizados!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")


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