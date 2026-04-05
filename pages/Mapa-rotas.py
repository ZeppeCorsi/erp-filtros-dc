import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
# IMPORTANTE: Importar a classe de conexão
from streamlit_gsheets import GSheetsConnection 

# CONFIGURAÇÃO DE CONEXÃO
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
# Usando export?format=csv é mais direto para o pandas ler
URL_LEITURA = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"

# Conexão para SALVAR/LER via Streamlit Native Connection
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados():
    try:
        # Lendo diretamente da URL de exportação para garantir compatibilidade
        df = pd.read_csv(URL_LEITURA)
        # Limpeza robusta de nomes de colunas
        df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da Filtros DC: {e}")
        return pd.DataFrame()

 def aba_mapa_comercial():
    st.subheader("📍 Expansão Filtros DC: Localização Estratégica")
    st.markdown("---")
    
    df = carregar_dados()
    
    if not df.empty:
        # 1. Filtramos apenas quem tem LATITUDE e LONGITUDE preenchidas e válidas
        # Convertemos para numérico caso tenham vindo como texto
        df['LATITUDE'] = pd.to_numeric(df.get('LATITUDE'), errors='coerce')
        df['LONGITUDE'] = pd.to_numeric(df.get('LONGITUDE'), errors='coerce')
        
        df_mapa = df.dropna(subset=['LATITUDE', 'LONGITUDE'])

        if not df_mapa.empty:
            # 2. Criar o mapa base centralizado na média dos seus clientes
            centro_lat = df_mapa['LATITUDE'].mean()
            centro_lon = df_mapa['LONGITUDE'].mean()
            
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=10, tiles="cartodbpositron")
            
            # 3. Adicionamos os marcadores SEM BUSCAR na internet (usando os dados da planilha)
            for idx, row in df_mapa.iterrows():
                popup_html = f"""
                <div style="font-family: sans-serif; min-width: 200px;">
                    <h4 style="color: #0047AB; margin-bottom: 5px;">{row['NOME REDUZIDO']}</h4>
                    <p style="font-size: 12px;"><b>📞 Contato:</b> {row['TELEFONE']}</p>
                    <p style="font-size: 11px; color: gray;">{row['MUNICIPIO']} - {row['UF']}</p>
                </div>
                """
                
                folium.Marker(
                    [row['LATITUDE'], row['LONGITUDE']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=row['NOME REDUZIDO'],
                    icon=folium.Icon(color='blue', icon='tint', prefix='fa')
                ).add_to(m)
            
            # Renderiza o mapa
            st_folium(m, width=1100, height=600, returned_objects=[])
            st.success(f"📍 {len(df_mapa)} clientes localizados no mapa com sucesso!")
        else:
            st.warning("Nenhum cliente possui coordenadas (Lat/Lon) cadastradas na planilha.")
    else:
        st.warning("A base de dados de clientes está vazia.")

# Para testar a função isoladamente
if __name__ == "__main__":
    aba_mapa_comercial()