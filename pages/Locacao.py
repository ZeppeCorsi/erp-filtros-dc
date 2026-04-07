import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        # ... (seu código do formulário aqui - mantenha como está)
        st.markdown("### Registrar Contrato e Provisionar 12 Meses")
        col1, col2 = st.columns(2)
        # ... (resto do formulário)
        if st.form_submit_button("Gerar Locação e Lançamentos"):
             # ... (lógica de gravação)
             st.success("✅ Tudo pronto!")

    # --- AGORA DENTRO DA FUNÇÃO (Identado corretamente) ---
    st.markdown("---")
    st.markdown("### 📅 Controle de Contratos (Vencimento da 12ª Parcela)")
    
    df_controle = carregar_dados("Locacao")
    
    if not df_controle.empty:
        # Garantir que as colunas estejam em maiúsculo para não dar erro de nome
        df_controle.columns = [str(c).strip().upper() for c in df_controle.columns]
        
        try:
            # 1. Converter a data (tentando vários formatos para não travar)
            df_controle['DATA_INICIO'] = pd.to_datetime(df_controle['DATA_INICIO'], dayfirst=True, errors='coerce')
            df_controle = df_controle.dropna(subset=['DATA_INICIO']) # Remove se houver data inválida
            
            # 2. Calcular a 12ª parcela
            df_controle['VENCIMENTO_12_PARC'] = df_controle['DATA_INICIO'].apply(
                lambda x: (x + relativedelta(months=11)).replace(day=5)
            )
            
            # 3. Calcular dias restantes
            hoje = pd.Timestamp(date.today())
            df_controle['DIAS_RESTANTES'] = (df_controle['VENCIMENTO_12_PARC'] - hoje).dt.days
            
            # 4. Preparar exibição
            df_display = df_controle.copy()
            df_display['DATA_INICIO_STR'] = df_display['DATA_INICIO'].dt.strftime('%d/%m/%Y')
            df_display['VENCIMENTO_STR'] = df_display['VENCIMENTO_12_PARC'].dt.strftime('%d/%m/%Y')
            
            # Renomear para o usuário
            df_display = df_display.rename(columns={
                'EQUIPAMENTO': 'PRODUTO',
                'VALOR_MENSAL': 'VALOR (R$)',
                'VENCIMENTO_STR': 'DATA 12ª PARCELA',
                'DIAS_RESTANTES': 'DIAS PARA FIM'
            })

            # Exibir a tabela
            st.dataframe(
                df_display[['CLIENTE', 'PRODUTO', 'VALOR (R$)', 'DATA 12ª PARCELA', 'DIAS PARA FIM']]
                .style.applymap(lambda x: 'color: red' if isinstance(x, int) and x <= 30 else 'color: black', subset=['DIAS PARA FIM'])
            )
            st.caption("💡 Linhas em vermelho indicam vencimento em menos de 30 dias.")
            
        except Exception as e:
            st.error(f"Erro ao processar datas: {e}")
    else:
        st.info("Nenhuma locação registrada para exibir o cronograma.")

# O if name == main fica fora de tudo no final do arquivo
if __name__ == "__main__":
    aba_gestao_locacao()