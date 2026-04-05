import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES INICIAIS
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_LEITURA = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"

# Conexão GSheets
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados():
    try:
        # Lendo os dados brutos
        df = pd.read_csv(URL_LEITURA)
        
        # Limpeza de nomes de colunas (Maiúsculas e sem aspas)
        df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
        
        # TRATAMENTO DE VÍRGULA PARA PONTO (Padrão Geográfico)
        for col in ['LATITUDE', 'LONGITUDE']:
            if col in df.columns:
                # Transforma "-23,49" em "-23.49" e converte para número
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da Filtros DC: {e}")
        return pd.DataFrame()

def aba_mapa_comercial():
    st.subheader("📍 Expansão Filtros DC: Localização Estratégica")
    st.markdown("---")
    
    df = carregar_dados()
    
    if not df.empty:
        # Filtra apenas quem tem as coordenadas convertidas com sucesso
        # Isso evita que o mapa trave por falta de informação técnica
        df_mapa = df.dropna(subset=['LATITUDE', 'LONGITUDE'])
        
        if not df_mapa.empty:
            # Centraliza o mapa na média das posições dos seus clientes (Auto-zoom)
            centro = [df_mapa['LATITUDE'].mean(), df_mapa['LONGITUDE'].mean()]
            m = folium.Map(location=centro, zoom_start=10, tiles="cartodbpositron")
            
            # Adiciona os marcadores (Pins) no mapa
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
            
            # Renderiza o mapa final
            st_folium(m, width=1100, height=600, returned_objects=[])
            st.success(f"📍 {len(df_mapa)} clientes localizados no mapa com sucesso!")
            
        else:
            st.warning("Nenhum cliente possui coordenadas (Lat/Lon) válidas na planilha. Verifique se estão com ponto decimal.")
    else:
        st.warning("A base de dados de clientes está vazia.")

# Execução da página
if __name__ == "__main__":
    aba_mapa_comercial()