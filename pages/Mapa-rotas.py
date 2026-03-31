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
        # Criar coluna de endereço apenas se as colunas necessárias existirem
        colunas_necessarias = ['RUA', 'NUMERO', 'BAIRRO', 'MUNICIPIO', 'UF']
        if all(col in df.columns for col in colunas_necessarias):
            
            # Botão para processar o mapa (evita gasto de API desnecessário)
            if st.button("🗺️ Gerar Mapa de Clientes"):
                with st.spinner("Buscando coordenadas dos nossos clientes..."):
                    
                    # Inicializa o geolocalizador
                    geolocator = Nominatim(user_agent="filtros_dc_erp_v2")
                    
                    # Criar o mapa base (Brasil)
                    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="cartodbpositron")
                    
                    for idx, row in df.iterrows():
                        try:
                            # Monta o endereço para busca
                            endereco = f"{row['RUA']}, {row['NUMERO']} - {row['MUNICIPIO']}, {row['UF']}, Brazil"
                            
                            # Busca latitude e longitude
                            loc = geolocator.geocode(endereco, timeout=10)
                            
                            if loc:
                                # Conteúdo do Balão (Popup)
                                popup_html = f"""
                                <div style="font-family: sans-serif; min-width: 200px;">
                                    <h4 style="color: #0047AB; margin-bottom: 5px;">{row['NOME REDUZIDO']}</h4>
                                    <p style="font-size: 12px;"><b>Razão:</b> {row['RAZAO SOCIAL']}</p>
                                    <p style="font-size: 12px;"><b>📞 Contato:</b> {row['TELEFONE']}</p>
                                    <p style="font-size: 11px; color: gray;">{row['MUNICIPIO']} - {row['UF']}</p>
                                </div>
                                """
                                
                                folium.Marker(
                                    [loc.latitude, loc.longitude],
                                    popup=folium.Popup(popup_html, max_width=300),
                                    tooltip=f"Ver detalhes: {row['NOME REDUZIDO']}",
                                    icon=folium.Icon(color='blue', icon='tint', prefix='fa')
                                ).add_to(m)
                        except Exception as e:
                            # Se um endereço falhar, continua para o próximo
                            continue
                    
                    # Renderiza o mapa no Streamlit
                    st_folium(m, width=1100, height=600, returned_objects=[])
        else:
            st.error(f"Erro: As colunas de endereço não foram encontradas. Colunas lidas: {df.columns.tolist()}")
    else:
        st.warning("A base de dados de clientes está vazia.")

# Para testar a função isoladamente
if __name__ == "__main__":
    aba_mapa_comercial()