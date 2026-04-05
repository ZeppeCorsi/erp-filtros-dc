import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
from geopy.distance import geodesic

# 1. CONFIGURAÇÕES E DADOS DA FILTROS DC
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_LEITURA = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid=0"
ENDERECO_FILTROS_DC = "Rua Nicolau Zarvos, 161 - São Paulo - SP"
COORD_FILTROS_DC = (-23.5705, -46.6915) # Coordenadas aproximadas da sua sede

def carregar_dados():
    try:
        df = pd.read_csv(URL_LEITURA)
        df.columns = [str(c).strip().upper() for c in df.columns]
        for col in ['LATITUDE', 'LONGITUDE']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def aba_mapa_comercial():
    st.subheader("📍 Planejamento de Rotas: Filtros DC")
    
    df = carregar_dados()
    if df.empty:
        st.warning("Base de dados vazia.")
        return

    # Limpeza para o mapa
    df_mapa = df.dropna(subset=['LATITUDE', 'LONGITUDE']).copy()

    # --- NOVO: SELEÇÃO DE CLIENTE PARA ATENDIMENTO ---
    col1, col2 = st.columns([1, 1])
    with col1:
        origem = st.selectbox("Ponto de Saída:", ["FILTROS DC (Sede)", "Outra Localização"])
    with col2:
        cliente_destino = st.selectbox(
            "Selecione o Cliente para Atendimento:", 
            options=["Nenhum"] + df_mapa['NOME REDUZIDO'].tolist()
        )

    # Cálculo de distância se um cliente for selecionado
    distancias = []
    coord_origem = COORD_FILTROS_DC if origem == "FILTROS DC (Sede)" else None
    
    if cliente_destino != "Nenhum":
        row_dest = df_mapa[df_mapa['NOME REDUZIDO'] == cliente_destino].iloc[0]
        coord_dest = (row_dest['LATITUDE'], row_dest['LONGITUDE'])
        
        # Calcula distância de todos os clientes em relação ao destino selecionado
        df_mapa['DIST_DEST_KM'] = df_mapa.apply(
            lambda x: geodesic(coord_dest, (x['LATITUDE'], x['LONGITUDE'])).km, axis=1
        )
        st.info(f"Exibindo clientes em um raio próximo a: **{cliente_destino}**")

    # --- CRIAÇÃO DO MAPA ---
    m = folium.Map(location=COORD_FILTROS_DC, zoom_start=11, tiles="cartodbpositron")

    # 1. Pin da FILTROS DC (VERMELHO)
    folium.Marker(
        COORD_FILTROS_DC,
        popup="<b>FILTROS DC</b><br>Sede Administrativa",
        tooltip="Nossa Empresa",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)

    # 2. Pins dos Clientes
    for idx, row in df_mapa.iterrows():
        # Cor padrão é azul, mas se for o destino selecionado, fica Verde
        cor_pin = 'green' if row['NOME REDUZIDO'] == cliente_destino else 'blue'
        icone_pin = 'star' if row['NOME REDUZIDO'] == cliente_destino else 'tint'
        
        popup_txt = f"<b>{row['NOME REDUZIDO']}</b><br>Tel: {row['TELEFONE']}"
        if cliente_destino != "Nenhum":
            popup_txt += f"<br>Distância: {row['DIST_DEST_KM']:.2f} km"

        folium.Marker(
            [row['LATITUDE'], row['LONGITUDE']],
            popup=folium.Popup(popup_txt, max_width=250),
            tooltip=row['NOME REDUZIDO'],
            icon=folium.Icon(color=cor_pin, icon=icone_pin, prefix='fa')
        ).add_to(m)

    st_folium(m, width=1100, height=600, returned_objects=[])

    # Tabela lateral com os 5 mais próximos se houver destino
    if cliente_destino != "Nenhum":
        st.write("### 🏁 Clientes mais próximos para otimizar a rota:")
        proximos = df_mapa[df_mapa['NOME REDUZIDO'] != cliente_destino].nsmallest(5, 'DIST_DEST_KM')
        st.dataframe(proximos[['NOME REDUZIDO', 'MUNICIPIO', 'DIST_DEST_KM']])

if __name__ == "__main__":
    aba_mapa_comercial()