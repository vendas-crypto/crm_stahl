import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from streamlit.connections import GSheetsConnection

# 1. CONFIGURAÇÃO BASE DA PÁGINA
st.set_page_config(page_title="STAHL CRM - Sistema Integrado", layout="wide", initial_sidebar_state="expanded")

# Caminhos das imagens que estão no seu GitHub
CAMINHO_LOGO = "logo_stahl.png"
CAMINHO_LAYOUT_LOGIN = "layout_login.png"

# Função auxiliar para converter imagem local in Base64 para o CSS de fundo
def obter_base64_da_imagem(caminho_arquivo):
    import os
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "rb") as f:
            dados = f.read()
        return base64.b64encode(dados).decode()
    return ""

# Inicialização das variáveis de sessão
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None
if 'bg_dinamico' not in st.session_state:
    st.session_state['bg_dinamico'] = None
if 'mensagem_sucesso_orcar' not in st.session_state:
    st.session_state['mensagem_sucesso_orcar'] = None

# INICIALIZAÇÃO DE CHAVES DE FILTROS
if 'filtro_orc_atual' not in st.session_state: st.session_state['filtro_orc_atual'] = []
if 'filtro_rep_atual' not in st.session_state: st.session_state['filtro_rep_atual'] = []
if 'filtro_item_atual' not in st.session_state: st.session_state['filtro_item_atual'] = []
if 'busca_empresa_atual' not in st.session_state: st.session_state['busca_empresa_atual'] = ""

# INICIALIZAÇÃO DO CONTADOR MESTRE SEQUENCIAL
if 'proximo_numero_orc' not in st.session_state:
    st.session_state['proximo_numero_orc'] = 66800

# --- CARREGAMENTO DO BACKGROUND ---
if not st.session_state['logado']:
    import os
    if not st.session_state['bg_dinamico'] and os.path.exists(CAMINHO_LAYOUT_LOGIN):
        try: st.session_state['bg_dinamico'] = obter_base64_da_imagem(CAMINHO_LAYOUT_LOGIN)
        except Exception: pass

    if st.session_state['bg_dinamico']:
        html_bg = f"""
        <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: url('data:image/png;base64,{st.session_state['bg_dinamico']}');
            background-size: cover; background-position: center center; background-repeat: no-repeat; z-index: -1;">
        </div>
        """
        st.markdown(html_bg, unsafe_allow_html=True)

# --- CUSTOMIZAÇÃO VISUAL COMPLEMENTAR VIA CSS ---
estilo_css = """
    <style>
        """ + ("""
        .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
            background-color: transparent !important; background-image: none !important;
        }
        """ if not st.session_state['logado'] else """
        .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"] { background-color: #F8F9FA !important; background-image: none !important; }
        .main { background-color: #F8F9FA !important; }
        """) + """
        h1, h2, h3, .section-header { color: #00205B !important; font-family: sans-serif; font-weight: 700; }
        [data-testid="stSidebar"] { background-color: #00205B !important; box-shadow: 4px 0px 10px rgba(0,0,0,0.3); }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #FFFFFF !important; font-size: 14px !important; }
        [data-testid="stSidebar"] input { color: #000000 !important; font-weight: 500 !important; }
        .main .block-container { padding-bottom: 40px !important; padding-top: 20px !important; }
        .section-header { font-size: 14px; border-bottom: 2px solid #00205B; padding-bottom: 3px; margin-top: 20px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        div.stButton > button:first-child {
            background-color: #FFB800 !important; color: #00205B !important; font-size: 16px !important;
            font-weight: bold !important; border-radius: 8px !important; border: 2px solid #FFB800 !important;
            width: 100% !important; padding: 10px 20px !important; transition: all 0.3s ease !important; box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important;
        }
        div.stButton > button:first-child:hover { background-color: #FFFFFF !important; color: #00205B !important; border: 2px solid #FFFFFF !important; transform: scale(1.02); }
    </style>
"""
st.markdown(estilo_css, unsafe_allow_html=True)

# 2. LISTA ATIVA DE EQUIPAMENTOS STAHL
EQUIPAMENTOS_DB = {
    "Complemento Of": 2, "Componentes": 5, "Estimativa": 4, "Guindaste Especial": 5, 
    "Guindaste Giratório": 5, "Guindaste Smalljib": 5, "Monovia": 5, "Pacote de Equipamentos": 10,
    "Pacote de Pontes": 7, "Pacote de Talhas": 5, "Ponte Rolante Duobox": 7, "Ponte Rolante Monobox": 7,
    "Ponte Rolante Smallcrane": 7, "Pórtico Manual": 7, "Pórtico Rolante": 10, "Sistema Modular Lcs": 5,
    "Talha Elétrica de Cabo Top Lift": 5, "Talha Elétrica de Cabo Scs": 5, "Talha Elétrica de Corrente Scs": 2,
    "Talha Elétrica de Corrente Top Lift": 2
}

ESTADOS_BR = ["SP", "PR", "MG", "BA", "RJ", "SC", "RS", "PE", "AM", "RN", "PB", "GO", "DF", "ES", "CE"]
LISTA_REPRESENTANTES = ["Meire Queiroz", "Fernando H. Junior", "Eng° Julio Correia", "Eng° Gustavo Swenson", "Daniela Santana", "Eng° Darilton Aguiar", "Haroldo Rezende", "Bruno Castro", "Eng° Mauro Reich", "Eng° Jacson Voit", "Eng° Ozias Winckler", "Ronaldo Silva", "Basílio Oliveira", "S/rep"]

# LISTA OFICIAL EM CAIXA ALTA PERFEITA
LISTA_ORCAMENTISTAS_CADASTRO = ["LF", "RS", "JV", "REP", "Não Definido"]

def somar_dias_uteis(data_inicio, dias):
    data_atual = data_inicio
    d_somados = 0
    while d_somados < dias:
        data_atual += timedelta(days=1)
        if data_atual.weekday() < 5: d_somados += 1
    return data_atual

# CONEXÃO DIRETA COM O GOOGLE SHEETS VIA STREAMLIT CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_aba_segura(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl="0h")
        df.columns = df.columns.str.strip()
        if 'Orçamentista' in df.columns:
            df['Orçamentista'] = df['Orçamentista'].astype(str).str.strip().str.upper().replace('NAN', 'Não Definido')
        
        # Lógica de cálculo de atraso
        if nome_aba == "Orçar" and not df.empty:
            if 'Orçamento' not in df.columns: df['Orçamento'] = ''
            if 'ValorTotal' not in df.columns: df['ValorTotal'] = 0.0
            if 'Atraso' not in df.columns: df['Atraso'] = ''
            
            hoje = datetime.today().date()
            atrasos_calculados = []
            for idx, row in df.iterrows():
                try:
                    data_prev_str = str(row['Previsto']).split(' ')[0]
                    if '/' in data_prev_str: data_prev = datetime.strptime(data_prev_str, '%d/%m/%Y').date()
                    else: data_prev = pd.to_datetime(data_prev_str).date()
                    
                    if hoje > data_prev:
                        dias_estouro = (hoje - data_prev).days
                        atrasos_calculados.append(f"{dias_estouro} dias")
                    else:
                        atrasos_calculados.append("No prazo")
                except Exception: atrasos_calculados.append("")
            df['Atraso'] = atrasos_calculados

        for col in df.columns:
            if col in ['Solicitado', 'Previsto', 'Iníciado', 'Enviado']:
                df[col] = df[col].astype(str).str.replace(' 00:00:00', '')
        return df
    except Exception:
        return pd.DataFrame([])

# CORREÇÃO DOS NOMES DAS ABAS ADAPTADOS PARA O SINGULAR DO SEU DRIVE
if 'df_orcar' not in st.session_state or st.session_state['df_orcar'].empty:
    st.session_state['df_orcar'] = carregar_aba_segura("Orçar")
if 'df_orcados' not in st.session_state or st.session_state['df_orcados'].empty:
    st.session_state['df_orcados'] = carregar_aba_segura("Orçado")
if 'df_perdidos' not in st.session_state or st.session_state['df_perdidos'].empty:
    st.session_state['df_perdidos'] = carregar_aba_segura("perdido")

USUARIOS_DB = {"thamires": {"nome": "Thamires Martins", "sigla": "TM", "perfil": "administrador"}}

with st.sidebar:
    import os
    if os.path.exists(CAMINHO_LOGO): st.image(CAMINHO_LOGO, use_container_width=True)
    else: st.markdown("<div style='font-size:16px; font-weight:800; color:#FFFFFF; text-align:center;'>GERENCIAMENTO STAHL TALHAS</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:15px 0; border-color: rgba(255,255,255,0.15);'>", unsafe_allow_html=True)

if not st.session_state['logado']:
    st.sidebar.markdown("<div style='text-align: center; margin-bottom: 20px;'><span style='font-size: 32px;'>🔒</span><div style='font-size: 15px; font-weight: 700; color: #FFB800; letter-spacing: 2px; margin-top: 5px;'>ACESSO</div></div>", unsafe_allow_html=True)
    usuario_input = st.sidebar.text_input("Login do usuário:")
    senha_input = st.sidebar.text_input("Senha corporativa:", type="password")
    botao_entrar = st.sidebar.button("Entrar no Sistema")

    if botao_entrar:
        usr = usuario_input.strip().lower()
        if usr in USUARIOS_DB and senha_input == "stahl@2026":
            st.session_state['logado'] = True
            st.session_state['user_info'] = USUARIOS_DB[usr]
            st.rerun()
        else: st.sidebar.error("Usuário ou senha incorretos.")

if st.session_state['logado']:
    user_info = st.session_state['user_info']
    st.sidebar.success(f"Conectado: {user_info['nome']}")
    menu = st.sidebar.radio("Navegação Administrador:", ["➕ Cadastrar Solicitação", "📁 Visão Geral das Bases", "⚙️ Configurações"])

    if st.sidebar.button("Sair / Desconectar"):
        st.session_state['logado'] = False
        st.rerun()

    # --- TELA DE CADASTRO ---
    if menu == "➕ Cadastrar Solicitação":
        st.subheader("📝 Cadastro de Nova Proposta Comercial")
        
        if st.session_state['mensagem_sucesso_orcar']:
            st.success(st.session_state['mensagem_sucesso_orcar'], icon="🚀")
            if st.button("Fechar Alerta ❌", key="close_cad"):
                st.session_state['mensagem_sucesso_orcar'] = None
                st.rerun()

        st.markdown("<div class='section-header'>Dados do Cliente e Localidade</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: empresa_sol = st.text_input("Razão Social da Empresa / Cliente:")
        with c2: cidade_sol = st.text_input("Cidade:")
        with c3: uf_sol = st.selectbox("UF do Destino:", ESTADOS_BR)
            
        cc1, cc2, cc3 = st.columns(3)
        with cc1: contato_nome = st.text_input("Nome do Contato Principal:")
        with cc2: contato_tel = st.text_input("Telefone de Contato:")
        with cc3: contato_email = st.text_input("E-mail do Cliente:")

        st.markdown("<br>", unsafe_allow_html=True)
        c7, c8, c9 = st.columns([2, 1, 1])
        with c7:
            eq_sol = st.selectbox("Equipamento Stahl:", list(EQUIPAMENTOS_DB.keys()))
            prazo_dias = EQUIPAMENTOS_DB[eq_sol]
        with c8: qtde_sol = st.number_input("Quantidade:", min_value=1, value=1)
        with c9: orc_resp = st.selectbox("Orçamentista Designado (Sigla):", LISTA_ORCAMENTISTAS_CADASTRO)

        rep_vinculado_automatico = "S/rep"
        if orc_resp == "REP":
            st.markdown("<div style='margin-top:-10px;'></div>", unsafe_allow_html=True)
            rep_vinculado_automatico = st.selectbox("Qual representante está orçando? (Controle Interno):", [r for r in LISTA_REPRESENTANTES if r != "S/rep"])

        st.markdown("<br>", unsafe_allow_html=True)
        c4, c5, c6 = st.columns(3)
        with c4: data_sol = st.date_input("Data de Entrada / Solicitação:", datetime.today().date(), format="DD/MM/YYYY")
        with c5:
            prazo_sugerido = somar_dias_uteis(data_sol, prazo_dias)
            previsao_entrega = st.date_input("Previsão de Entrega Técnica (Alterável):", prazo_sugerido, format="DD/MM/YYYY")
        
        with c6:
            index_default_rep = 0
            if orc_resp == "REP":
                if rep_vinculado_automatico in LISTA_REPRESENTANTES: index_default_rep = LISTA_REPRESENTANTES.index(rep_vinculado_automatico)
            else:
                for i, rep_nome in enumerate(LISTA_REPRESENTANTES):
                    if orc_resp.lower() in rep_nome.lower() and orc_resp != "Não Definido":
                        index_default_rep = i
                        break
            rep_sol = st.selectbox("Representante Comercial Responsável:", LISTA_REPRESENTANTES, index=index_default_rep)

        obs_sol = st.text_area("Observações Iniciais do Atendimento:")
        
        if st.button("Gravar Solicitação no Banco de Dados 🚀"):
            if not empresa_sol.strip(): st.error("Por favor, preencha a Razão Social da Empresa.")
            else:
                df_atual = st.session_state['df_orcar'].copy()
                if not df_atual.empty and 'IdSolicitacao' in df_atual.columns:
                    proximo_id = int(pd.to_numeric(df_atual['IdSolicitacao'], errors='coerce').max()) + 1
                else: proximo_id = 40774
                
                nova_linha = {
                    "IdSolicitacao": proximo_id, "Situação": "Orçar", "Atraso": "No prazo",
                    "Empresa": empresa_sol.strip(), "Representante": rep_sol,
                    "Solicitado": data_sol.strftime('%d/%m/%Y'), "Previsto": previsao_entrega.strftime('%d/%m/%Y'),
                    "Iníciado": "None", 
                    "Orçamentista": str(orc_resp).strip().upper(),
                    "Orçamento": "None", "Rev": 0, "Enviado": "None",
                    "Item": eq_sol, "Qtde": qtde_sol, "Observação": obs_sol.strip(),
                    "Fone": contato_tel, 
                    "UF": str(uf_sol).strip().upper(),
                    "Cidade": cidade_sol, "Contato": contato_nome, "ValorTotal": 0.0
                }
                
                df_final = pd.concat([df_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(worksheet="Orçar", data=df_final)
                st.session_state['df_orcar'] = df_final
                
                st.session_state['filtro_orc_atual'] = []
                st.session_state['busca_empresa_atual'] = ""
                st.session_state['mensagem_sucesso_orcar'] = f"✅ Gravado em Caixa Alta Padronizada! ID: {proximo_id}"
                st.rerun()

    # --- TELA DE VISÃO GERAL ---
    elif menu == "📁 Visão Geral das Bases":
        st.subheader("📁 Gerenciamento das Carteiras de Propostas")
        
        if st.session_state['mensagem_sucesso_orcar']:
            st.success(st.session_state['mensagem_sucesso_orcar'], icon="✅")
            if st.button("Fechar Alerta ❌", key="close_view"):
                st.session_state['mensagem_sucesso_orcar'] = None
                st.rerun()

        aba_orcar, aba_orcados, aba_perdidos = st.tabs(["⏳ 1. Base ORÇAR / ORÇANDO", "✅ 2. Base ORÇADOS", "❌ 3. Base PERDIDOS"])
        
        with aba_orcar:
            st.markdown("<div class='section-header'>🔍 Filtro</div>", unsafe_allow_html=True)
            f1, f2, f3 = st.columns(3)
            with f1:
                opcoes_orc = sorted([str(x).upper() for x in st.session_state['df_orcar']['Orçamentista'].dropna().unique() if str(x) != 'nan']) if not st.session_state['df_orcar'].empty else []
                st.session_state['filtro_orc_atual'] = st.multiselect("Filtrar por Orçamentista:", opcoes_orc, default=st.session_state['filtro_orc_atual'])
            with f2:
                opcoes_rep = sorted([str(x) for x in st.session_state['df_orcar']['Representante'].dropna().unique() if str(x) != 'nan']) if not st.session_state['df_orcar'].empty else []
                st.session_state['filtro_rep_atual'] = st.multiselect("Filtrar por Representante:", opcoes_rep, default=st.session_state['filtro_rep_atual'])
            with f3:
                opcoes_item = sorted([str(x) for x in st.session_state['df_orcar']['Item'].dropna().unique() if str(x) != 'nan']) if not st.session_state['df_orcar'].empty else []
                st.session_state['filtro_item_atual'] = st.multiselect("Filtrar por Item:", opcoes_item, default=st.session_state['filtro_item_atual'])
                
            st.session_state['busca_empresa_atual'] = st.text_input("⌨️ Pesquisar Empresa por escrito:", value=st.session_state['busca_empresa_atual'])
            
            df_orcar_filtrado = st.session_state['df_orcar'].copy() if not st.session_state['df_orcar'].empty else pd.DataFrame()
            
            if not df_orcar_filtrado.empty:
                if st.session_state['filtro_orc_atual']: df_orcar_filtrado = df_orcar_filtrado[df_orcar_filtrado['Orçamentista'].str.upper().isin(st.session_state['filtro_orc_atual'])]
                if st.session_state['filtro_rep_atual']: df_orcar_filtrado = df_orcar_filtrado[df_orcar_filtrado['Representante'].isin(st.session_state['filtro_rep_atual'])]
                if st.session_state['filtro_item_atual']: df_orcar_filtrado = df_orcar_filtrado[df_orcar_filtrado['Item'].isin(st.session_state['filtro_item_atual'])]
                if st.session_state['busca_empresa_atual']: 
                    df_orcar_filtrado = df_orcar_filtrado[df_orcar_filtrado['Empresa'].astype(str).str.contains(st.session_state['busca_empresa_atual'], case=False, na=False)]
            
            st.markdown("<div class='section-header'>⚙️ Ações</div>", unsafe_allow_html=True)
            
            if not df_orcar_filtrado.empty:
                df_orcar_filtrado.insert(0, "Selecionar", False)
                act1, act2, act3 = st.columns(3)
                
                st.markdown("### 📋 Registros Encontrados na Carteira")
                df_editado = st.data_editor(
                    df_orcar_filtrado,
                    key="editor_orcar_real",
                    hide_index=True,
                    use_container_width=True,
                    disabled=[c for c in df_orcar_filtrado.columns if c in ["IdSolicitacao", "Situação", "Atraso", "Solicitado", "Previsto"]]
                )
                
                linhas_selecionadas = df_editado[df_editado["Selecionar"] == True]
                
                with act1:
                    if st.button("🚀 Iniciar"):
                        if not linhas_selecionadas.empty:
                            num_atual = int(st.session_state['proximo_numero_orc'])
                            lista_numeros_gerados = []
                            for idx, row in linhas_selecionadas.iterrows():
                                id_sol = row["IdSolicitacao"]
                                num_orc = f"ORC-13-{num_atual:06d}"
                                lista_numeros_gerados.append(num_orc)
                                st.session_state['df_orcar'].loc[st.session_state['df_orcar']['IdSolicitacao'] == id_sol, 'Situação'] = 'Orçando'
                                st.session_state['df_orcar'].loc[st.session_state['df_orcar']['IdSolicitacao'] == id_sol, 'Orçamento'] = num_orc
                                st.session_state['df_orcar'].loc[st.session_state['df_orcar']['IdSolicitacao'] == id_sol, 'Iníciado'] = datetime.today().strftime('%d/%m/%Y')
                                num_atual += 1
                            st.session_state['proximo_numero_orc'] = num_atual
                            conn.update(worksheet="Orçar", data=st.session_state['df_orcar'])
                            st.session_state['mensagem_sucesso_orcar'] = f"Orçamento Iniciado com Sucesso! Sequência Gerada: {', '.join(lista_numeros_gerados)}"
                            st.rerun()
                        else: st.warning("Por favor, marque a caixinha antes.")
                        
                with act2:
                    if st.button("💾 Salvar Edições da Tabela"):
                        for idx, row in df_editado.iterrows():
                            id_sol = row["IdSolicitacao"]
                            for col in [c for c in df_editado.columns if c not in ["Selecionar"]]:
                                val = row[col]
                                if col == 'Orçamentista': val = str(val).strip().upper()
                                st.session_state['df_orcar'].loc[st.session_state['df_orcar']['IdSolicitacao'] == id_sol, col] = val
                        conn.update(worksheet="Orçar", data=st.session_state['df_orcar'])
                        st.session_state['mensagem_sucesso_orcar'] = "Alterações salvas em Caixa Alta com sucesso!"
                        st.rerun()
                        
                with act3:
                    if st.button("📨 Enviar Orçamento"):
                        if not linhas_selecionadas.empty:
                            indices_para_remover = []
                            for idx, row in linhas_selecionadas.iterrows():
                                id_sol = row["IdSolicitacao"]
                                registro_original = st.session_state['df_orcar'][st.session_state['df_orcar']['IdSolicitacao'] == id_sol]
                                if not registro_original.empty:
                                    reg = registro_original.iloc[0].to_dict()
                                    reg['Situação'] = 'Orçado'
                                    reg['ValorTotal'] = row['ValorTotal']
                                    reg['Orçamento'] = row['Orçamento']
                                    reg['Enviado'] = datetime.today().strftime('%d/%m/%Y')
                                    st.session_state['df_orcados'] = pd.concat([st.session_state['df_orcados'], pd.DataFrame([reg])], ignore_index=True)
                                    indices_para_remover.append(id_sol)
                            st.session_state['df_orcar'] = st.session_state['df_orcar'][~st.session_state['df_orcar']['IdSolicitacao'].isin(indices_para_remover)]
                            conn.update(worksheet="Orçar", data=st.session_state['df_orcar'])
                            # AJUSTADO PARA O NOME DA SUA ABA NO SINGULAR
                            conn.update(worksheet="Orçado", data=st.session_state['df_orcados'])
                            st.session_state['mensagem_sucesso_orcar'] = "✅ Confirmação: Transferido para a base de Orçados!"
                            st.rerun()
                        else: st.warning("Por favor, marque a caixinha antes.")
            else: st.info("Nenhum registro ativo para os filtros.")

        with aba_orcados:
            if not st.session_state['df_orcados'].empty: st.dataframe(st.session_state['df_orcados'], use_container_width=True)
            else: st.info("Planilha 'Orçado' na nuvem está vazia.")
        with aba_perdidos:
            if not st.session_state['df_perdidos'].empty: st.dataframe(st.session_state['df_perdidos'], use_container_width=True)
            else: st.info("Planilha 'perdido' na nuvem está vazia.")

    # --- CONFIGURAÇÃO ---
    elif menu == "⚙️ Configurações":
        st.subheader("⚙️ Configurações")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='section-header'>🎛️ Parametrização de Propostas</div>", unsafe_allow_html=True)
            num_ajustado = st.number_input("Definir próximo número sequencial da Stahl (Ex: 66800):", value=int(st.session_state['proximo_numero_orc']), step=1)
            if st.button("💾 Travar Sequência Numérica"):
                st.session_state['proximo_numero_orc'] = num_ajustado
                st.success(f"Configurado! Sequência travada em: ORC-13-{num_ajustado:06d}")
            
            st.markdown("<div class='section-header'>Upload da Identidade Visual</div>", unsafe_allow_html=True)
            upload_layout = st.file_uploader("Suba a imagem de Background da Tela Inicial:", type=['png', 'jpg', 'jpeg'])
            if upload_layout is not None:
                bytes_data = upload_layout.getvalue()
                st.session_state['bg_dinamico'] = base64.b64encode(bytes_data).decode()  
                if st.button("💾 Salvar Layout Definitivo"):
                    with open(CAMINHO_LAYOUT_LOGIN, "wb") as f: f.write(upload_layout.getbuffer())
                    st.success("Layout salvo com sucesso!")
                    st.rerun()
                    
        with col2:
            st.markdown("<div class='section-header'>📂 Carga Manual / Sobrescrita de Bancos de Dados (.xlsx)</div>", unsafe_allow_html=True)
            
            up_orcar = st.file_uploader("1. Forçar Atualização Completa da Aba ORÇAR:", type=['xlsx'])
            if up_orcar is not None and st.button("💾 Enviar e Substituir Aba ORÇAR"):
                df_up = pd.read_excel(up_orcar)
                conn.update(worksheet="Orçar", data=df_up)
                st.session_state['df_orcar'] = df_up
                st.success("Aba 'Orçar' sincronizada com sucesso!")

            up_orcados = st.file_uploader("2. Forçar Atualização Completa da Aba ORÇADOS:", type=['xlsx'])
            if up_orcados is not None and st.button("💾 Enviar e Substituir Aba ORÇADOS"):
                df_up = pd.read_excel(up_orcados)
                # AJUSTADO PARA O NOME DA SUA ABA NO SINGULAR
                conn.update(worksheet="Orçado", data=df_up)
                st.session_state['df_orcados'] = df_up
                st.success("Aba 'Orçado' sincronizada com sucesso!")

            up_perdidos = st.file_uploader("3. Forçar Atualização Completa da Aba PERDIDOS:", type=['xlsx'])
            if up_perdidos is not None and st.button("💾 Enviar e Substituir Aba PERDIDOS"):
                df_up = pd.read_excel(up_perdidos)
                # AJUSTADO PARA O NOME DA SUA ABA NO SINGULAR
                conn.update(worksheet="perdido", data=df_up)
                st.session_state['df_perdidos'] = df_up
                st.success("Aba 'perdido' sincronizada com sucesso!")