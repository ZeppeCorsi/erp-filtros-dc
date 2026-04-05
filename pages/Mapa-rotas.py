import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
from geopy.distance import geodesic

# 1. CONFIGURAÇÕES E DADOS EXATOS DA FILTROS DC
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_LEITURA = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"

# Coordenadas exatas da Rua Nicolau Zarvos, 161 baseadas no seu mapa
COORD_FILTROS_DC = (-23.6425, -46.6475) 

def carregar_dados():
    try:
        df = pd.read_csv(URL_LEITURA)
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Tratamento de vírgula para ponto e conversão numérica
        for col in ['LATITUDE', 'LONGITUDE']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def aba_mapa_comercial():
    st.subheader("📍 Planejamento de Rotas e Proximidade")
    
    df = carregar_dados()
    if df.empty:
        st.warning("Base de dados vazia.")
        return

    # Limpeza para o mapa (mantendo apenas quem tem lat/lon válidos)
    df_mapa = df.dropna(subset=['LATITUDE', 'LONGITUDE']).copy()

    # --- SELEÇÃO DE CLIENTE ---
    col1, col2 = st.columns([1, 1])
    with col1:
        st.info(f"🏠 **Sede:** Rua Nicolau Zarvos, 161")
        origem = st.radio("Sair de:", ["Filtros DC", "Outro Local"], horizontal=True)
    with col2:
        cliente_destino = st.selectbox(
            "Selecionar Cliente para Visita:", 
            options=["Nenhum"] + df_mapa['NOME REDUZIDO'].tolist()
        )

    # --- LÓGICA DE DISTÂNCIA ---
    if cliente_destino != "Nenhum":
        row_dest = df_mapa[df_mapa['NOME REDUZIDO'] == cliente_destino].iloc[0]
        coord_dest = (row_dest['LATITUDE'], row_dest['LONGITUDE'])
        
        # Calcula distância de todos em relação ao cliente escolhido
        df_mapa['DIST_DEST_KM'] = df_mapa.apply(
            lambda x: geodesic(coord_dest, (x['LATITUDE'], x['LONGITUDE'])).km, axis=1
        )

    # --- MAPA ---
    m = folium.Map(location=COORD_FILTROS_DC, zoom_start=13, tiles="cartodbpositron")

    # 1. Marcador da FILTROS DC (Vermelho)
    folium.Marker(
        COORD_FILTROS_DC,
        popup="<b>FILTROS DC</b><br>Rua Nicolau Zarvos, 161",
        tooltip="Nossa Empresa",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)

    # 2. Marcadores dos Clientes
    for idx, row in df_mapa.iterrows():
        # Destaque para o cliente selecionado
        is_dest = (row['NOME REDUZIDO'] == cliente_destino)
        cor = 'green' if is_dest else 'blue'
        
        # Montagem do Balão com E-mail e Telefone
        popup_html = f"""
        <div style="font-family: sans-serif; min-width: 200px;">
            <h4 style="color: #0047AB; margin-bottom: 2px;">{row['NOME REDUZIDO']}</h4>
            <p style="font-size: 12px; margin: 2px 0;"><b>📞 Tel:</b> {row['TELEFONE']}</p>
            <p style="font-size: 12px; margin: 2px 0;"><b>📧 E-mail:</b> {row.get('EMAIL', 'Não cadastrado')}</p>
            <p style="font-size: 11px; color: gray;">{row['MUNICIPIO']} - {row['UF']}</p>
        </div>
        """
        
        folium.Marker(
            [row['LATITUDE'], row['LONGITUDE']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['NOME REDUZIDO'],
            icon=folium.Icon(color=cor, icon='tint' if not is_dest else 'star', prefix='fa')
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

    # --- TABELA DE APOIO ---
    if cliente_destino != "Nenhum":
        st.write(f"### 🏁 Clientes num raio próximo a {cliente_destino}:")
        # Mostra os 5 mais próximos (excluindo o próprio selecionado)
        proximos = df_mapa[df_mapa['NOME REDUZIDO'] != cliente_destino].nsmallest(5, 'DIST_DEST_KM')
        st.dataframe(proximos[['NOME REDUZIDO', 'TELEFONE', 'EMAIL', 'MUNICIPIO', 'DIST_DEST_KM']])

if __name__ == "__main__":
    aba_mapa_comercial()