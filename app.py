"""
app.py
------
Interface web do Canoa Analytics via Streamlit.
Execute com: streamlit run app.py

Para hospedar gratuitamente:
  1. Suba o projeto no GitHub
  2. Acesse https://share.streamlit.io
  3. Conecte o repositório e aponte para este arquivo
"""

import sys
import os
import tempfile
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from core.parser import parse_tcx
from core.enricher import enrich_trackpoints
from core.detector import detect_sprints
from core.analyzer import analisar
from report.builder import gerar_html


import hmac


# Autenticacao por senha
# Defina no Streamlit Cloud: Settings > Secrets > APP_PASSWORD = "sua_senha"
# Localmente: crie .streamlit/secrets.toml com APP_PASSWORD = "sua_senha"

def _checar_senha():
    def _verificar():
        senha_correta = st.secrets.get("APP_PASSWORD", "")
        if not senha_correta:
            st.session_state["autenticado"] = True
            return
        digitada = st.session_state.get("senha_digitada", "")
        if hmac.compare_digest(digitada, senha_correta):
            st.session_state["autenticado"] = True
            st.session_state["senha_errada"] = False
        else:
            st.session_state["autenticado"] = False
            st.session_state["senha_errada"] = True

    if st.session_state.get("autenticado"):
        return

    st.title("Canoa Analytics")
    st.markdown("---")
    st.subheader("Acesso restrito")
    st.text_input(
        "Senha", type="password",
        key="senha_digitada",
        on_change=_verificar,
        placeholder="Digite a senha e pressione Enter"
    )
    if st.session_state.get("senha_errada"):
        st.error("Senha incorreta. Tente novamente.")
    st.stop()


_checar_senha()

# ── Configuração da página ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Canoa Analytics",
    page_icon="🛶",
    layout="centered",
)

st.title("🛶 Canoa Analytics")
st.caption("Gere o relatório de treino a partir do seu arquivo TCX do Garmin.")

# ── Upload do TCX ─────────────────────────────────────────────────────────────

st.header("1. Arquivo TCX")

with st.expander("📱 Usando Android? Leia antes de fazer o upload"):
    st.markdown("""
O Android restringe o seletor de arquivos e pode não mostrar arquivos `.tcx`.

**Solução simples:**
1. Localize o arquivo TCX na pasta Downloads
2. Renomeie-o trocando `.tcx` por `.txt` (ex: `treino.tcx` → `treino.txt`)
3. Faça o upload normalmente — o app reconhece os dois formatos
""")

tcx_file = st.file_uploader(
    "Selecione o arquivo TCX exportado do Garmin Connect",
    type=None,
    help="No Garmin Connect: abra a atividade → ⋮ → Exportar para TCX"
)

# ── Dados do treino ───────────────────────────────────────────────────────────

st.header("2. Dados do Treino")

col1, col2 = st.columns(2)

with col1:
    nome_clube = st.text_input("Nome do Clube", value="Nome do Clube")
    canoa_tipo = st.selectbox("Tipo de Canoa", ["OC1", "OC2", "OC3", "OC4", "OC6", "V1", "V3", "V6", "Outro"])

with col2:
    qtd_tiros = st.number_input(
        "Quantidade de tiros realizados", min_value=1, max_value=20,
        value=5, step=1
    )
    numero_partes = st.selectbox(
        "Dividir cada tiro em quantas partes?", [2, 4], index=0
    )

# Distâncias dos tiros
st.subheader("Distância dos tiros")
tiros_variados = st.radio(
    "Os tiros tiveram distâncias diferentes?",
    ["Não — todos com a mesma distância", "Sim — distâncias variadas"],
    horizontal=True,
)

if tiros_variados.startswith("Não"):
    distancia_sprint = st.number_input(
        "Distância por tiro (metros)", min_value=100, max_value=5000,
        value=500, step=50
    )
    lista_distancias = [float(distancia_sprint)] * int(qtd_tiros)
else:
    st.caption("Informe a distância de cada tiro na ordem em que foram executados.")
    lista_distancias = []
    for i in range(int(qtd_tiros)):
        d = st.number_input(
            f"Tiro {i+1} — distância (metros)",
            min_value=100, max_value=5000,
            value=500, step=50,
            key=f"dist_tiro_{i}"
        )
        lista_distancias.append(float(d))
    distancia_sprint = lista_distancias  # passa como lista

# ── Campos dinâmicos de atletas por posição ───────────────────────────────────

st.subheader("Atletas por posição")

QTD_BANCOS = {
    "OC1": 1, "V1": 1,
    "OC2": 2,
    "V3":  3,
    "OC4": 4,
    "OC6": 6, "V6": 6,
    "Outro": 1,
}

qtd_bancos = QTD_BANCOS.get(canoa_tipo, 1)
nomes_por_banco = []

if qtd_bancos == 1:
    nome_unico = st.text_input("Atleta", value="", placeholder="Nome do atleta")
    nomes_por_banco = [nome_unico]
else:
    for i in range(qtd_bancos):
        nome_banco = st.text_input(f"Banco {i+1}", value="", placeholder=f"Atleta do banco {i+1}", key=f"banco_{i}")
        nomes_por_banco.append(nome_banco)

# Lista de nomes por banco, preenchendo vazios como "—" (preserva ordem Voga → Leme)
nomes_membros = [n.strip() if n.strip() else "—" for n in nomes_por_banco]

# ── Observações do treino ─────────────────────────────────────────────────────

st.subheader("Observações do treino")
observacoes = st.text_area(
    "Anotações livres (opcional)",
    value="",
    placeholder="Ex: O atleta do banco 1 trocou de lugar com o atleta do banco 2 a partir do 3º tiro.",
    height=80,
)

# ── Pesos do Score ────────────────────────────────────────────────────────────

with st.expander("⚙️ Configurações avançadas (pesos do Score)"):
    st.caption("Os três pesos devem somar 100.")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        peso_vel = st.number_input("Peso Velocidade (%)", 0, 100, 50, 5)
    with col_p2:
        peso_sus = st.number_input("Peso Sustentação (%)", 0, 100, 30, 5)
    with col_p3:
        peso_con = st.number_input("Peso Consistência (%)", 0, 100, 20, 5)

    soma_pesos = peso_vel + peso_sus + peso_con
    if soma_pesos != 100:
        st.warning(f"⚠️ A soma dos pesos é {soma_pesos}%. Deve ser exatamente 100%.")

# ── Botão gerar ───────────────────────────────────────────────────────────────

st.header("3. Gerar Relatório")

gerar = st.button(
    "🚀 Gerar Relatório",
    type="primary",
    disabled=(tcx_file is None or soma_pesos != 100),
    use_container_width=True,
)

if tcx_file is None:
    st.info("📂 Faça o upload do arquivo TCX para habilitar o botão.")

if gerar and tcx_file is not None and soma_pesos == 100:

    with st.spinner("Processando... aguarde."):

        # Salva TCX em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix=".tcx", delete=False) as tmp:
            tmp.write(tcx_file.read())
            tmp_path = tmp.name

        try:
            # Pipeline completo
            trackpoints = parse_tcx(tmp_path)
            trackpoints = enrich_trackpoints(trackpoints)
            sprints = detect_sprints(
                trackpoints,
                distancia_sprint=lista_distancias,
                numero_partes=int(numero_partes),
                qtd_tiros=int(qtd_tiros),
            )

            if len(sprints) == 0:
                st.error(
                    "⚠️ Nenhum tiro foi detectado com os parâmetros informados. "
                    "Verifique a distância por tiro e a quantidade de tiros."
                )
            else:
                cfg = {
                    "TCX_FILE":        tcx_file.name,
                    "NOME_CLUB":       nome_clube,
                    "CANOA_TIPO":      canoa_tipo,
                    "NOMES_MEMBROS":   nomes_membros,
                    "DISTANCIA_SPRINT": distancia_sprint,
                    "NUMERO_PARTES":   numero_partes,
                    "QTD_TIROS":       qtd_tiros,
                    "PESO_VELOCIDADE":   peso_vel,
                    "PESO_SUSTENTACAO":  peso_sus,
                    "PESO_CONSISTENCIA": peso_con,
                    "OBSERVACOES":       observacoes.strip(),
                }

                sprints = analisar(
                    sprints,
                    peso_velocidade=peso_vel,
                    peso_sustentacao=peso_sus,
                    peso_consistencia=peso_con,
                )

                html = gerar_html(sprints, cfg)

                # Métricas rápidas no topo
                st.success(f"✅ {len(sprints)} tiro(s) detectado(s) com sucesso!")

                cols = st.columns(len(sprints))
                ordenados = sorted(sprints, key=lambda s: s["OrdemExecucaoSprint"])
                for i, s in enumerate(ordenados):
                    with cols[i]:
                        st.metric(
                            label=f"Tiro {s['OrdemExecucaoSprint']}",
                            value=f"{s['VelSprint_kmh']} km/h",
                            delta=f"Score {s.get('ScoreSprint', '—')}",
                        )

                # Nome do arquivo: Treino_DD-MM-AAAA_NomeDoClube.html
                data_hoje = datetime.now().strftime("%d-%m-%Y")
                clube_slug = "".join(c for c in nome_clube if c.isalnum() or c in (" ", "-")).strip()
                clube_slug = clube_slug.replace(" ", "")
                nome_arquivo = f"Treino_{data_hoje}_{clube_slug or 'Treino'}.html"

                st.download_button(
                    label="📥 Baixar Relatório HTML",
                    data=html.encode("utf-8"),
                    file_name=nome_arquivo,
                    mime="text/html",
                    type="primary",
                    use_container_width=True,
                )

                st.caption(
                    "💡 Dica: baixe o HTML, abra no navegador e compartilhe "
                    "pelo WhatsApp usando o botão de compartilhamento do celular."
                )

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")

        finally:
            os.unlink(tmp_path)