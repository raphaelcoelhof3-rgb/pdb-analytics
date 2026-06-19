"""
builder.py
----------
Gera o relatório HTML completo a partir das sprints analisadas.
"""

import os
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE FORMATAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def _br(valor, decimais=2):
    """Formata número no padrão brasileiro: ponto milhar, vírgula decimal."""
    if valor is None:
        return "-"
    try:
        v = float(valor)
        formatado = f"{v:,.{decimais}f}"          # ex: 1,234.56
        return formatado.replace(",", "X").replace(".", ",").replace("X", ".")  # ex: 1.234,56
    except Exception:
        return str(valor)


def _vel(valor):
    return f"{_br(valor, 2)} km/h"

def _dist(valor):
    return f"{_br(valor, 1)} m"

def _tempo_fmt(segundos_raw):
    seg = int(round(float(segundos_raw)))
    return f"{seg // 60}min {seg % 60:02d}s"

def _duracao_fmt(minutos_raw):
    """Formata duração de minutos decimais para 'X min e Y seg'."""
    if minutos_raw is None:
        return "-"
    total_seg = int(round(float(minutos_raw) * 60))
    minutos = total_seg // 60
    segundos = total_seg % 60
    return f"{minutos} min e {segundos} seg"

def _consistencia_label(indice: float) -> str:
    """Converte índice bruto em nota 0-100 e rótulo."""
    nota = round((1 - indice) * 100, 1)
    if indice < 0.005:
        rotulo = "Excelente"
    elif indice < 0.010:
        rotulo = "Boa"
    elif indice < 0.020:
        rotulo = "Regular"
    else:
        rotulo = "Irregular"
    return nota, rotulo

def _cor_score(score: float) -> str:
    if score >= 70:
        return "#1a7a3a"   # verde escuro
    elif score >= 50:
        return "#e07b00"   # laranja
    else:
        return "#b71c1c"   # vermelho

def _cor_classificacao(cl: str) -> str:
    cores = {
        "Progressivo":      "#1565c0",
        "Muito consistente":"#1a7a3a",
        "Consistente":      "#558b2f",
        "Queda moderada":   "#e07b00",
        "Quebrou":          "#b71c1c",
    }
    return cores.get(cl, "#555")

def _barra_score(score: float) -> str:
    cor = _cor_score(score)
    return f"""
    <div style="background:#e0e0e0;border-radius:6px;height:14px;width:100%;min-width:80px;">
      <div style="background:{cor};width:{min(score,100):.0f}%;height:14px;border-radius:6px;"></div>
    </div>
    <span style="font-size:0.85em;color:{cor};font-weight:bold;">{_br(score,1)}</span>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
  * { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    margin: 0; padding: 0;
    background: #f0f4f8; color: #1a1a2e;
  }
  .container { max-width: 960px; margin: 0 auto; padding: 30px 20px; }

  /* Cabeçalho */
  .header {
    background: linear-gradient(135deg, #003366 0%, #005599 100%);
    color: white; border-radius: 12px;
    padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
  }
  .header h1 { margin: 0 0 6px 0; font-size: 1.8em; letter-spacing: 1px; }
  .header .sub { opacity: 0.85; font-size: 0.95em; margin: 2px 0; }
  .header .meta-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 6px 24px; margin-top: 16px; font-size: 0.92em;
  }
  .header .meta-grid span b { opacity: 0.75; font-weight: normal; }

  /* Seções */
  .section {
    background: white; border-radius: 12px;
    padding: 24px 28px; margin-bottom: 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }
  .section h2 {
    color: #003366; font-size: 1.2em;
    border-bottom: 2px solid #e0e8f4;
    padding-bottom: 8px; margin-top: 0;
  }
  .section h3 { color: #005599; font-size: 1em; margin-top: 18px; }

  /* Cards do pódio */
  .podium { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 12px; }
  .card {
    flex: 1; min-width: 160px;
    border-radius: 10px; padding: 16px 18px;
    text-align: center; color: white;
    box-shadow: 0 3px 10px rgba(0,0,0,0.13);
  }
  .card.ouro   { background: linear-gradient(135deg,#c8922a,#f0c040); }
  .card.prata  { background: linear-gradient(135deg,#7a8fa6,#b0c4d8); }
  .card.bronze { background: linear-gradient(135deg,#a0522d,#cd7f32); }
  .card .medal { font-size: 2em; }
  .card .lugar { font-size: 0.8em; opacity: 0.9; margin: 2px 0; }
  .card .tiro  { font-size: 1.1em; font-weight: bold; margin: 6px 0 4px; }
  .card .score-val { font-size: 1.6em; font-weight: bold; }
  .card .vel-val { font-size: 0.88em; opacity: 0.9; }

  /* Resumo info-grid */
  .info-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px 30px; margin: 12px 0;
  }
  .info-item { font-size: 0.95em; }
  .info-item b { color: #003366; }

  /* Tabelas */
  table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 0.92em; }
  th {
    background: #003366; color: white;
    padding: 10px 8px; text-align: center; font-weight: 600;
  }
  td { padding: 8px; text-align: center; border-bottom: 1px solid #e8eef5; }
  tr:nth-child(even) td { background: #f5f8fd; }
  thead tr:nth-child(2) th {
    background: #2471a3 !important;
    font-size: 0.85em;
    padding: 5px 4px;
  }
  tr:hover td { background: #e8f0fb; }
  .cl-badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 12px; color: white; font-size: 0.85em; font-weight: 600;
  }

  /* Stats cards */
  .stats-row { display: flex; gap: 14px; flex-wrap: wrap; margin: 14px 0; }
  .stat-card {
    flex: 1; min-width: 130px; background: #f0f4f8;
    border-radius: 8px; padding: 14px; text-align: center;
    border-left: 4px solid #003366;
  }
  .stat-card .val { font-size: 1.4em; font-weight: bold; color: #003366; }
  .stat-card .lbl { font-size: 0.78em; color: #555; margin-top: 4px; }

  /* Destaque técnico */
  .destaque {
    background: #f5f8fd; border-left: 4px solid #005599;
    border-radius: 6px; padding: 12px 16px; margin: 10px 0;
  }
  .destaque .d-title { font-weight: bold; color: #003366; margin-bottom: 4px; }
  .destaque .d-val { font-size: 1.05em; }

  /* Interpretação */
  .interp {
    background: #fffde7; border-left: 4px solid #f9a825;
    border-radius: 6px; padding: 12px 16px; margin: 10px 0;
    font-size: 0.95em;
  }

  .page-break { page-break-before: always; margin-top: 36px; }
  @media(max-width:600px) {
    .container { padding: 12px 8px; }
    .header { padding: 16px 14px; border-radius: 8px; }
    .header h1 { font-size: 1.25em; line-height: 1.3; }
    .header .sub { font-size: 0.82em; line-height: 1.5; }
    .info-grid, .meta-grid { grid-template-columns: 1fr; gap: 4px; }
    .header .meta-grid { font-size: 0.82em; margin-top: 10px; }
    .header .meta-grid span { word-break: break-word; }
    .section { padding: 14px 12px; border-radius: 8px; }
    .section h2 { font-size: 1.05em; }
    .podium, .stats-row { flex-direction: column; }
    table { font-size: 0.82em; }
    th, td { padding: 5px 4px !important; }
  }

  /* ── CSS de impressão / PDF ─────────────────────────────────── */
  @media print {
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    body { background: white !important; margin: 0; padding: 0; font-size: 11pt; }
    .container { max-width: 100%; padding: 0; margin: 0; }
    .header {
      background: #003366 !important; color: white !important;
      border-radius: 0 !important; padding: 16px 20px !important;
      margin-bottom: 16px !important; box-shadow: none !important;
      page-break-inside: avoid;
    }
    .header h1 { font-size: 1.4em !important; }
    .header .meta-grid { grid-template-columns: 1fr 1fr; gap: 4px 16px; }
    .section {
      border-radius: 0 !important; box-shadow: none !important;
      border: 1px solid #ccd6e8 !important;
      padding: 14px 16px !important; margin-bottom: 14px !important;
      page-break-inside: avoid;
    }
    .podium { display: flex !important; flex-direction: row !important; gap: 8px !important; }
    .card { flex: 1 !important; padding: 10px !important; border-radius: 6px !important; page-break-inside: avoid; }
    .card.ouro   { background: #c8922a !important; }
    .card.prata  { background: #7a8fa6 !important; }
    .card.bronze { background: #a0522d !important; }
    .stats-row { display: flex !important; flex-direction: row !important; gap: 6px !important; }
    .stat-card { flex: 1 !important; min-width: 0 !important; padding: 8px !important; border-radius: 4px !important; page-break-inside: avoid; }
    .stat-card .val { font-size: 1.1em !important; }
    .info-grid { grid-template-columns: 1fr 1fr; }
    table { font-size: 9.5pt !important; page-break-inside: auto; }
    tr { page-break-inside: avoid; }
    th { background: #003366 !important; color: white !important; padding: 6px 5px !important; }
    td { padding: 5px !important; }
    .cl-badge { padding: 1px 7px !important; font-size: 8pt !important; }
    .destaque { page-break-inside: avoid; padding: 8px 12px !important; margin: 6px 0 !important; }
    .interp   { page-break-inside: avoid; padding: 8px 12px !important; }
    .page-break { page-break-before: always !important; margin-top: 0 !important; }
    #map { display: none !important; }
    details summary { display: none !important; }
    details ul { display: block !important; font-size: 8.5pt; }
    a { text-decoration: none !important; color: inherit !important; }
  }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — Cabeçalho + Pódio + Ranking por Score
# ═══════════════════════════════════════════════════════════════════════════════

def _pagina_resumo(sprints: list[dict], config: dict) -> str:
    ordenadas_score = sorted(sprints, key=lambda s: s.get("ScoreSprint", 0), reverse=True)
    melhor = ordenadas_score[0]
    pior   = ordenadas_score[-1]
    total  = len(sprints)
    ref    = sprints[0]
    tcx_nome = os.path.basename(config["TCX_FILE"])

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    header = f"""
<div class="header">
  <h1>🏝️ {config['NOME_CLUB']} — Planilha de Treino</h1>
  <div class="sub">📅 {ref['DateTimeTreino']} &nbsp;|&nbsp; 🛶 {config['CANOA_TIPO']} &nbsp;|&nbsp; 📄 {tcx_nome}</div>
  <div class="meta-grid">
    <span><b>Atletas (Voga › Leme):</b> {config['NOMES_MEMBROS']}</span>
    <span><b>Relatório gerado em:</b> {ref['DateTimeNow']}</span>
    <span><b>Duração total:</b> {_duracao_fmt(ref['TreinoDuracao_min'])}</span>
    <span><b>Distância total:</b> {_dist(ref['TreinoDistancia_m'])}</span>
    <span><b>Distância por tiro:</b> {_br(config['DISTANCIA_SPRINT'], 0)} m em {config['NUMERO_PARTES']} partes</span>
    <span><b>Total de tiros:</b> {total}</span>
  </div>
</div>"""

    # ── Resumo rápido ─────────────────────────────────────────────────────────
    resumo = f"""
<div class="section">
  <h2>📋 Resumo do Treino</h2>
  <div class="info-grid">
    <div class="info-item">🏆 <b>Melhor tiro:</b> Tiro {melhor['OrdemExecucaoSprint']} (Score {_br(melhor['ScoreSprint'], 1)})</div>
    <div class="info-item">📉 <b>Pior tiro:</b> Tiro {pior['OrdemExecucaoSprint']} (Score {_br(pior['ScoreSprint'], 1)})</div>
  </div>
</div>"""

    # ── Observações do treino ───────────────────────────────────────────────────
    observacoes_texto = (config.get("OBSERVACOES") or "").strip()
    observacoes_html = ""
    if observacoes_texto:
        observacoes_formatadas = observacoes_texto.replace("\n", "<br>")
        observacoes_html = f"""
<div class="section">
  <h2>📝 Observações do Treino</h2>
  <p style="white-space:pre-wrap;line-height:1.6;">{observacoes_formatadas}</p>
</div>"""

    # ── Pódio ─────────────────────────────────────────────────────────────────
    estilos = ["ouro", "prata", "bronze"]
    medais  = ["🥇", "🥈", "🥉"]
    lugares = ["1º Lugar", "2º Lugar", "3º Lugar"]
    cards   = ""
    for i in range(min(3, total)):
        f = ordenadas_score[i]
        cards += f"""
    <div class="card {estilos[i]}">
      <div class="medal">{medais[i]}</div>
      <div class="lugar">{lugares[i]}</div>
      <div class="tiro">Tiro {f['OrdemExecucaoSprint']}</div>
      <div class="score-val">{_br(f['ScoreSprint'], 1)}</div>
      <div class="vel-val">{_vel(f['VelSprint_kmh'])}</div>
    </div>"""

    podio = f"""
<div class="section">
  <h2>🏆 Pódio do Treino</h2>
  <div class="podium">{cards}</div>
</div>"""

    # ── Ranking por Score ─────────────────────────────────────────────────────
    linhas = ""
    for f in ordenadas_score:
        score = float(f['ScoreSprint'])
        cl    = f['ClassificacaoSprint']
        cor_cl = _cor_classificacao(cl)
        ind_c  = float(f['IndiceConsistencia'])
        nota_c, rotulo_c = _consistencia_label(ind_c)
        linhas += f"""
    <tr>
      <td><b>{f['OrdemScore']}</b></td>
      <td>{_barra_score(score)}</td>
      <td>{_vel(f['VelSprint_kmh'])}</td>
      <td>{_br(f['IndiceSustentacao'], 3)}</td>
      <td>{_br(nota_c, 1)}/100<br><small style="color:#666">{rotulo_c}</small></td>
      <td><span class="cl-badge" style="background:{cor_cl}">{cl}</span></td>
      <td><b>Tiro {f['OrdemExecucaoSprint']}</b></td>
    </tr>"""

    legenda = """
  <details style="margin-bottom:12px;cursor:pointer;">
    <summary style="color:#005599;font-weight:bold;">ℹ️ Ver legenda das colunas</summary>
    <ul style="margin-top:8px;line-height:1.9;font-size:0.92em;">
      <li><b>Score:</b> Nota geral do tiro (0–100). Combina velocidade, sustentação e consistência.</li>
      <li><b>Velocidade:</b> Velocidade média real do tiro (distância ÷ tempo).</li>
      <li><b>Sustentação:</b> Razão entre a velocidade da 2ª metade e da 1ª metade. Próximo de 1 = ritmo mantido; acima de 1 = acelerou; abaixo = desacelerou.</li>
      <li><b>Consistência:</b> Nota de 0 a 100 — quanto maior, mais uniforme foi a execução. Excelente ≥ 99,5 | Boa ≥ 99,0 | Regular ≥ 98,0 | Irregular &lt; 98,0.</li>
      <li><b>Classificação:</b> Comportamento geral do tiro.</li>
      <li><b>Tiro:</b> Ordem de execução durante o treino.</li>
    </ul>
  </details>"""

    ranking = f"""
<div class="section">
  <h2>📊 Ranking por Score</h2>
  {legenda}
  <table>
    <tr>
      <th>Rank</th><th>Score</th><th>Velocidade</th>
      <th>Sustentação</th><th>Consistência</th>
      <th>Classificação</th><th>Tiro</th>
    </tr>
    {linhas}
  </table>
</div>"""

    return header + resumo + observacoes_html + podio + ranking


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — Análise Técnica
# ═══════════════════════════════════════════════════════════════════════════════

def _pagina_analise(sprints: list[dict]) -> str:
    velocidades   = [float(s["VelSprint_kmh"]) for s in sprints]
    sustentacoes  = [float(s["IndiceSustentacao"]) for s in sprints]
    consistencias = [float(s["IndiceConsistencia"]) for s in sprints]

    contagem = {"Progressivo": 0, "Muito consistente": 0,
                "Consistente": 0, "Queda moderada": 0, "Quebrou": 0}
    melhor_score = melhor_vel = melhor_sust = None

    for s in sprints:
        cl = s.get("ClassificacaoSprint")
        if cl in contagem:
            contagem[cl] += 1
        if melhor_score is None or float(s["ScoreSprint"]) > float(melhor_score["ScoreSprint"]):
            melhor_score = s
        if melhor_vel is None or float(s["VelSprint_kmh"]) > float(melhor_vel["VelSprint_kmh"]):
            melhor_vel = s
        if melhor_sust is None or float(s["IndiceSustentacao"]) > float(melhor_sust["IndiceSustentacao"]):
            melhor_sust = s

    vel_media  = sum(velocidades) / len(velocidades)
    sust_media = sum(sustentacoes) / len(sustentacoes)
    cons_media = sum(consistencias) / len(consistencias)
    vel_max    = max(velocidades)
    vel_min    = min(velocidades)
    total      = len(sprints)
    n_cons     = contagem["Muito consistente"] + contagem["Consistente"]
    pct        = (n_cons / total) * 100

    nota_cons_media, rotulo_cons_media = _consistencia_label(cons_media)

    # Stats cards
    stats = f"""
  <div class="stats-row">
    <div class="stat-card">
      <div class="val">{_br(vel_media, 2)}</div>
      <div class="lbl">Vel. Média (km/h)</div>
    </div>
    <div class="stat-card">
      <div class="val">{_br(vel_max, 2)}</div>
      <div class="lbl">Maior Vel. (km/h)</div>
    </div>
    <div class="stat-card">
      <div class="val">{_br(vel_min, 2)}</div>
      <div class="lbl">Menor Vel. (km/h)</div>
    </div>
    <div class="stat-card">
      <div class="val">{_br(sust_media, 3)}</div>
      <div class="lbl">Sustentação Média</div>
    </div>
    <div class="stat-card">
      <div class="val">{_br(nota_cons_media, 1)}/100</div>
      <div class="lbl">Consistência Média<br><small>({rotulo_cons_media})</small></div>
    </div>
  </div>"""

    # Distribuição de classificações
    linhas_cl = "".join(
        f"""<tr>
          <td><span class="cl-badge" style="background:{_cor_classificacao(cl)}">{cl}</span></td>
          <td>{qt}</td>
          <td>{"█" * qt}</td>
        </tr>"""
        for cl, qt in contagem.items()
    )

    # Interpretação automática
    if pct >= 80:
        txt_cons = f"{pct:.0f}% dos tiros apresentaram comportamento consistente, indicando excelente controle de ritmo durante o treino."
    elif pct >= 60:
        txt_cons = f"{pct:.0f}% dos tiros apresentaram comportamento consistente, indicando boa distribuição de esforço."
    elif pct >= 40:
        txt_cons = f"{pct:.0f}% dos tiros apresentaram comportamento consistente. Há sinais de oscilação de ritmo em parte das execuções."
    else:
        txt_cons = f"Apenas {pct:.0f}% dos tiros foram consistentes, sugerindo dificuldade em manter um padrão estável de velocidade."

    if sust_media >= 1.05:
        txt_sust = "Forte capacidade de aceleração ao longo dos tiros — a equipe terminou em média mais rápido do que começou."
    elif sust_media >= 1.00:
        txt_sust = "Excelente manutenção de velocidade ao longo dos tiros."
    elif sust_media >= 0.97:
        txt_sust = "Boa sustentação, com pequenas perdas de velocidade ao final dos tiros."
    elif sust_media >= 0.94:
        txt_sust = "Perda moderada de desempenho ao longo dos tiros, indicando espaço para evolução na resistência específica."
    else:
        txt_sust = "Dificuldade em sustentar o ritmo, com quedas significativas de velocidade ao longo dos tiros."

    # Destaques
    ind_c_ms, rot_ms = _consistencia_label(float(melhor_score["IndiceConsistencia"]))
    ind_c_mv, rot_mv = _consistencia_label(float(melhor_vel["IndiceConsistencia"]))

    destaques = f"""
  <div class="destaque">
    <div class="d-title">🏅 Melhor Tiro Geral (maior Score)</div>
    <div class="d-val">Tiro {melhor_score['OrdemExecucaoSprint']} &mdash;
      Score {_br(melhor_score['ScoreSprint'], 1)} &nbsp;|&nbsp;
      {_vel(melhor_score['VelSprint_kmh'])} &nbsp;|&nbsp;
      <span class="cl-badge" style="background:{_cor_classificacao(melhor_score['ClassificacaoSprint'])};color:white">{melhor_score['ClassificacaoSprint']}</span>
    </div>
  </div>
  <div class="destaque">
    <div class="d-title">⚡ Tiro Mais Rápido</div>
    <div class="d-val">Tiro {melhor_vel['OrdemExecucaoSprint']} &mdash;
      {_vel(melhor_vel['VelSprint_kmh'])} &nbsp;|&nbsp;
      Score {_br(melhor_vel['ScoreSprint'], 1)}
    </div>
  </div>
  <div class="destaque">
    <div class="d-title">💪 Maior Sustentação</div>
    <div class="d-val">Tiro {melhor_sust['OrdemExecucaoSprint']} &mdash;
      Sustentação {_br(melhor_sust['IndiceSustentacao'], 3)}
      &nbsp;|&nbsp; {melhor_sust['ClassificacaoSprint']}
    </div>
  </div>"""

    return f"""
<div class="page-break"></div>
<div class="section">
  <h2>📈 Análise Técnica do Treino</h2>
  <h3>🎯 Resumo da Performance</h3>
  {stats}

  <h3>🏃 Distribuição das Classificações</h3>
  <table>
    <tr><th>Classificação</th><th>Qtd</th><th>Proporção</th></tr>
    {linhas_cl}
  </table>

  <h3>🥇 Destaques do Treino</h3>
  {destaques}

  <h3>📌 Interpretação Automática</h3>
  <div class="interp">
    <p>{txt_cons}</p>
    <p>{txt_sust}</p>
    <p>A melhor combinação entre velocidade, sustentação e consistência foi
    observada no <b>Tiro {melhor_score['OrdemExecucaoSprint']}</b>,
    com Score de <b>{_br(melhor_score['ScoreSprint'], 1)}</b>.</p>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — Ranking por Ordem de Execução
# ═══════════════════════════════════════════════════════════════════════════════

def _pagina_ranking(sprints: list[dict]) -> str:
    linhas = ""
    for s in sorted(sprints, key=lambda x: int(x["OrdemExecucaoSprint"])):
        score = float(s["ScoreSprint"])
        cl    = s["ClassificacaoSprint"]
        linhas += f"""
    <tr>
      <td><b>Tiro {s['OrdemExecucaoSprint']}</b></td>
      <td>{s['SprintRank_Vel']}</td>
      <td>{_vel(s['VelSprint_kmh'])}</td>
      <td>{_tempo_fmt(s['TempoSprint_s'])}</td>
      <td>{_barra_score(score)}</td>
      <td><span class="cl-badge" style="background:{_cor_classificacao(cl)}">{cl}</span></td>
    </tr>"""

    return f"""
<div class="page-break"></div>
<div class="section">
  <h2>📊 Ranking por Ordem de Execução</h2>
  <p style="font-size:0.9em;color:#555;">Tiros ordenados conforme foram executados no treino.</p>
  <table>
    <tr>
      <th>Tiro</th><th>Rank Vel.</th><th>Velocidade</th>
      <th>Tempo</th><th>Score</th><th>Classificação</th>
    </tr>
    {linhas}
  </table>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — Detalhamento Técnico
# ═══════════════════════════════════════════════════════════════════════════════

def _pagina_detalhamento(sprints: list[dict], numero_partes: int) -> str:

    def fmt_vel(s, campo):
        v = s.get(campo)
        return _br(v, 2) if v not in (None, "") else "-"

    def fmt_tempo(s, campo):
        v = s.get(campo)
        return _tempo_fmt(v) if v not in (None, "") else "-"

    np = numero_partes
    colspan_vel   = np
    colspan_tempo = np
    colspan_dist  = np

    # Cabeçalho com grupos mesclados (como no Excel)
    sub_vel   = "".join(f"<th>P{i}</th>" for i in range(1, np + 1))
    sub_tempo = "".join(f"<th>P{i}</th>" for i in range(1, np + 1))
    sub_dist  = "".join(f"<th>P{i}</th>" for i in range(1, np + 1))

    sprint_homogenea   = min(sprints, key=lambda s: float(s.get("IndiceConsistencia") or 999))
    sprint_progressiva = max(sprints, key=lambda s: float(s.get("IndiceSustentacao") or 0))
    sprint_queda       = min(sprints, key=lambda s: float(s.get("IndiceSustentacao") or 999))

    linhas = ""
    for s in sorted(sprints, key=lambda x: int(x["OrdemExecucaoSprint"])):
        ind_c = float(s["IndiceConsistencia"])
        nota_c, rotulo_c = _consistencia_label(ind_c)
        cols_vel   = "".join(f"<td>{fmt_vel(s, f'VelParte{i}_kmh')}</td>"  for i in range(1, np + 1))
        cols_tempo = "".join(f"<td>{fmt_tempo(s, f'TempoParte{i}_s')}</td>" for i in range(1, np + 1))
        cols_dist  = "".join(f"<td>{_br(s.get(f'DistParte{i}_m'), 1)}</td>" for i in range(1, np + 1))
        linhas += f"""
    <tr>
      <td><b>Tiro {s['OrdemExecucaoSprint']}</b></td>
      {cols_vel}{cols_tempo}{cols_dist}
      <td>{_br(s['IndiceSustentacao'], 3)}</td>
      <td>{_br(nota_c, 1)}/100<br><small style="color:#666">{rotulo_c}</small></td>
    </tr>"""

    ind_hom, rot_hom = _consistencia_label(float(sprint_homogenea["IndiceConsistencia"]))

    destaques = f"""
  <div class="destaque">
    <div class="d-title">🎯 Tiro mais homogêneo (menor variação de velocidade)</div>
    <div class="d-val">Tiro {sprint_homogenea['OrdemExecucaoSprint']} &mdash;
      Consistência {_br(ind_hom, 1)}/100 ({rot_hom})</div>
  </div>
  <div class="destaque">
    <div class="d-title">📈 Tiro mais progressivo (maior aceleração na 2ª metade)</div>
    <div class="d-val">Tiro {sprint_progressiva['OrdemExecucaoSprint']} &mdash;
      Sustentação {_br(sprint_progressiva['IndiceSustentacao'], 3)}</div>
  </div>
  <div class="destaque">
    <div class="d-title">📉 Tiro com maior queda de rendimento</div>
    <div class="d-val">Tiro {sprint_queda['OrdemExecucaoSprint']} &mdash;
      Sustentação {_br(sprint_queda['IndiceSustentacao'], 3)}</div>
  </div>"""

    return f"""
<div class="page-break"></div>
<div class="section">
  <h2>📊 Detalhamento Técnico dos Tiros</h2>
  <div style="overflow-x:auto;">
  <table style="min-width:100%;white-space:nowrap;font-size:0.88em;">
    <thead>
      <tr>
        <th rowspan="2" style="vertical-align:middle;">Tiro</th>
        <th colspan="{colspan_vel}" style="background:#1a5276;">Velocidade (km/h)</th>
        <th colspan="{colspan_tempo}" style="background:#1a5276;">Tempo</th>
        <th colspan="{colspan_dist}" style="background:#1a5276;">Distância (m)</th>
        <th rowspan="2" style="vertical-align:middle;background:#117a65;">Sustentação</th>
        <th rowspan="2" style="vertical-align:middle;background:#117a65;">Consistência</th>
      </tr>
      <tr>
        {sub_vel}{sub_tempo}{sub_dist}
      </tr>
    </thead>
    <tbody>
    {linhas}
    </tbody>
  </table>
  </div>
  <h3>🏅 Destaques Técnicos</h3>
  {destaques}
</div>"""



# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — Mapa dos Tiros + Índice de Retidão
# ═══════════════════════════════════════════════════════════════════════════════

# Cores para até 10 tiros
CORES_TIROS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
    "#fabed4", "#469990"
]


def _pagina_mapa(sprints: list[dict]) -> str:
    import json

    ordenadas = sorted(sprints, key=lambda s: s["OrdemExecucaoSprint"])

    # Verifica se há coordenadas disponíveis
    com_coords = [s for s in ordenadas if s.get("CoordsTraco")]
    if not com_coords:
        return """
<div class="page-break"></div>
<div class="section">
  <h2>🗺️ Mapa dos Tiros</h2>
  <p style="color:#888;">Coordenadas GPS não disponíveis para este treino.</p>
</div>"""

    # Centro do mapa: média de todas as coordenadas do primeiro tiro
    primeiro = com_coords[0]["CoordsTraco"]
    lat_centro = sum(p["lat"] for p in primeiro) / len(primeiro)
    lon_centro = sum(p["lon"] for p in primeiro) / len(primeiro)

    # Monta JS com os traçados
    js_tiros = []
    legenda_items = ""
    for idx, s in enumerate(ordenadas):
        coords = s.get("CoordsTraco", [])
        if not coords:
            continue
        cor = CORES_TIROS[idx % len(CORES_TIROS)]
        tiro_num = s["OrdemExecucaoSprint"]
        latlons = [[p["lat"], p["lon"]] for p in coords]
        js_tiros.append(f"""
    var tiro{tiro_num} = L.polyline({json.dumps(latlons)}, {{
        color: '{cor}', weight: 4, opacity: 0.85
    }}).addTo(map);
    tiro{tiro_num}.bindPopup('<b>Tiro {tiro_num}</b><br>{_vel(s["VelSprint_kmh"])}<br>Score {_br(s.get("ScoreSprint",""), 1)}');
    L.circleMarker({json.dumps(latlons[0])}, {{radius:7, color:'{cor}', fillColor:'white', fillOpacity:1, weight:3}})
        .bindPopup('Início — Tiro {tiro_num}').addTo(map);
    L.circleMarker({json.dumps(latlons[-1])}, {{radius:7, color:'{cor}', fillColor:'{cor}', fillOpacity:1, weight:2}})
        .bindPopup('Fim — Tiro {tiro_num}').addTo(map);""")

        ret = s.get("IndiceRetidao")
        ret_str = f"{_br(ret*100, 1)}%" if ret is not None else "—"
        legenda_items += f"""
      <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
        <div style="width:28px;height:5px;background:{cor};border-radius:3px;flex-shrink:0;"></div>
        <span>Tiro {tiro_num} &mdash; {_vel(s["VelSprint_kmh"])} &mdash; Retidão: {ret_str} ({s.get("RetidaoLabel","—")})</span>
      </div>"""

    js_all = "\n".join(js_tiros)

    # Tabela de retidão
    linhas_ret = ""
    tiro_mais_reto = max(ordenadas, key=lambda s: s.get("IndiceRetidao") or 0)
    for s in ordenadas:
        ret = s.get("IndiceRetidao")
        label = s.get("RetidaoLabel", "—")
        dist_reta = s.get("DistRetaMetros")
        dist_real = s.get("DistSprint_real")
        cor_label = {
            "Excelente": "#1a7a3a", "Boa": "#558b2f",
            "Regular": "#e07b00",   "Irregular": "#b71c1c"
        }.get(label, "#555")
        destaque = " style='background:#fffde7;'" if s["OrdemExecucaoSprint"] == tiro_mais_reto["OrdemExecucaoSprint"] else ""
        linhas_ret += f"""
    <tr{destaque}>
      <td><b>Tiro {s['OrdemExecucaoSprint']}</b></td>
      <td>{_dist(dist_reta) if dist_reta else '—'}</td>
      <td>{_dist(dist_real) if dist_real else '—'}</td>
      <td>{_br(ret, 4) if ret is not None else '—'}</td>
      <td><span class="cl-badge" style="background:{cor_label}">{label}</span></td>
    </tr>"""

    return f"""
<div class="page-break"></div>
<div class="section">
  <h2>🗺️ Mapa dos Tiros</h2>
  <div id="map" style="height:480px;border-radius:10px;margin-bottom:14px;z-index:0;"></div>
  <div style="background:#f5f8fd;border-radius:8px;padding:12px 16px;font-size:0.9em;">
    <b>Legenda:</b>
    {legenda_items}
  </div>
</div>

<div class="section">
  <h2>📐 Índice de Retidão dos Tiros</h2>
  <p style="font-size:0.9em;color:#555;">
    Razão entre a distância em linha reta (GPS início→fim) e a distância real percorrida.
    Quanto mais próximo de 1, mais reto foi o tiro.<br>
    <b>Excelente</b> ≥ 99,5% &nbsp;|&nbsp; <b>Boa</b> ≥ 98,5% &nbsp;|&nbsp;
    <b>Regular</b> ≥ 97,0% &nbsp;|&nbsp; <b>Irregular</b> &lt; 97,0%
  </p>
  <table>
    <tr>
      <th>Tiro</th><th>Dist. Reta</th><th>Dist. Real</th>
      <th>Índice</th><th>Classificação</th>
    </tr>
    {linhas_ret}
  </table>
  <div class="destaque" style="margin-top:14px;">
    <div class="d-title">🎯 Tiro mais reto</div>
    <div class="d-val">Tiro {tiro_mais_reto['OrdemExecucaoSprint']} &mdash;
      Índice {_br(tiro_mais_reto.get('IndiceRetidao'), 4)} ({tiro_mais_reto.get('RetidaoLabel','—')})
    </div>
  </div>
</div>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var map = L.map('map').setView([{lat_centro}, {lon_centro}], 15);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors', maxZoom: 19
  }}).addTo(map);
  {js_all}
</script>"""



# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 6 — Gráficos Velocidade × Distância
# ═══════════════════════════════════════════════════════════════════════════════

def _pagina_graficos(sprints: list[dict]) -> str:
    import json

    ordenadas = sorted(sprints, key=lambda s: s["OrdemExecucaoSprint"])

    # Verifica se há séries disponíveis
    if not any(s.get("SerieGrafico") for s in ordenadas):
        return ""

    # ── Gráfico comparativo (todos os tiros) ─────────────────────────────────
    traces_comparativo = []
    for idx, s in enumerate(ordenadas):
        serie = s.get("SerieGrafico", [])
        if not serie:
            continue
        cor = CORES_TIROS[idx % len(CORES_TIROS)]
        tiro_num = s["OrdemExecucaoSprint"]
        x = [p["dist_rel"] for p in serie]
        y = [p["vel"] for p in serie]
        traces_comparativo.append({
            "x": x, "y": y,
            "type": "scatter", "mode": "lines",
            "name": f"Tiro {tiro_num}",
            "line": {"color": cor, "width": 2},
            "hovertemplate": f"<b>Tiro {tiro_num}</b><br>Dist: %{{x}} m<br>Vel: %{{y:.2f}} km/h<extra></extra>"
        })

    layout_comp = {
        "title": {"text": "Comparativo de Velocidade — Todos os Tiros", "font": {"size": 15}},
        "xaxis": {"title": "Distância percorrida no tiro (m)", "gridcolor": "#e8eef5"},
        "yaxis": {"title": "Velocidade (km/h)", "gridcolor": "#e8eef5"},
        "plot_bgcolor": "#f8fafd",
        "paper_bgcolor": "white",
        "legend": {"orientation": "h", "y": -0.28, "x": 0.5, "xanchor": "center"},
        "margin": {"t": 50, "b": 110, "l": 60, "r": 20},
        "hovermode": "x unified",
    }

    # ── Gráficos individuais ──────────────────────────────────────────────────
    graficos_individuais = ""
    for idx, s in enumerate(ordenadas):
        serie = s.get("SerieGrafico", [])
        if not serie:
            continue
        cor = CORES_TIROS[idx % len(CORES_TIROS)]
        tiro_num = s["OrdemExecucaoSprint"]
        x = [p["dist_rel"] for p in serie]
        y = [p["vel"] for p in serie]

        # Linhas verticais das divisões de partes
        shapes = []
        annotations = []
        dist_base_tiro = 0.0
        num_partes = sum(1 for p in range(1, 5) if s.get(f"DistParte{p}_m") is not None)
        for p in range(1, num_partes):
            dist_p = s.get(f"DistParte{p}_m")
            if dist_p is None:
                continue
            dist_base_tiro += dist_p
            shapes.append({
                "type": "line",
                "x0": dist_base_tiro, "x1": dist_base_tiro,
                "y0": 0, "y1": 1, "yref": "paper",
                "line": {"color": "#aaa", "width": 1, "dash": "dot"}
            })
            annotations.append({
                "x": dist_base_tiro, "y": 1.04, "yref": "paper",
                "text": f"P{p}|P{p+1}", "showarrow": False,
                "font": {"size": 9, "color": "#888"}
            })

        trace_ind = [{
            "x": x, "y": y,
            "type": "scatter", "mode": "lines",
            "name": f"Tiro {tiro_num}",
            "line": {"color": cor, "width": 2.5},
            "fill": "tozeroy", "fillcolor": cor.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in cor else cor + "14",
            "hovertemplate": "Dist: %{x} m<br>Vel: %{y:.2f} km/h<extra></extra>"
        }]

        layout_ind = {
            "title": {"text": f"Tiro {tiro_num} — {_vel(s['VelSprint_kmh'])} | Score {_br(s.get('ScoreSprint',''), 1)}", "font": {"size": 13}},
            "xaxis": {"title": "Distância (m)", "gridcolor": "#e8eef5"},
            "yaxis": {"title": "Velocidade (km/h)", "gridcolor": "#e8eef5"},
            "plot_bgcolor": "#f8fafd", "paper_bgcolor": "white",
            "shapes": shapes, "annotations": annotations,
            "margin": {"t": 50, "b": 50, "l": 60, "r": 20},
            "showlegend": False,
        }

        div_id = f"grafico_tiro_{tiro_num}"
        graficos_individuais += f"""
  <h3 style="color:#005599;margin-top:22px;">Tiro {tiro_num}</h3>
  <div id="{div_id}" style="height:260px;"></div>
  <script>
    window.addEventListener('load', function() {{ Plotly.newPlot('{div_id}', {json.dumps(trace_ind)}, {json.dumps(layout_ind)}, {{responsive:true, displayModeBar:false}}); }});
  </script>"""

    div_comp = "grafico_comparativo"

    return f"""
<div class="page-break"></div>
<div class="section">
  <h2>📈 Gráficos de Velocidade × Distância</h2>
  <p style="font-size:0.9em;color:#555;">
    Velocidade suavizada ao longo da distância percorrida em cada tiro.
    As linhas pontilhadas nos gráficos individuais marcam as divisões entre partes.
  </p>

  <h3 style="color:#005599;">Comparativo — Todos os Tiros</h3>
  <div id="{div_comp}" style="height:380px;"></div>

  <h3 style="color:#005599;margin-top:28px;">Gráficos Individuais</h3>
  {graficos_individuais}
</div>

<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script>
  window.addEventListener('load', function() {{
    Plotly.newPlot('{div_comp}', {json.dumps(traces_comparativo)}, {json.dumps(layout_comp)}, {{responsive:true, displayModeBar:false}});
  }});
</script>"""


# ── Sobrescreve gerar_html para incluir página 6 ─────────────────────────────

def gerar_html(sprints: list[dict], config: dict) -> str:
    p1 = _pagina_resumo(sprints, config)
    p2 = _pagina_analise(sprints)
    p3 = _pagina_ranking(sprints)
    p4 = _pagina_detalhamento(sprints, config["NUMERO_PARTES"])
    p5 = _pagina_mapa(sprints)
    p6 = _pagina_graficos(sprints)
    return f"<html><head><meta charset='UTF-8'>{CSS}</head><body><div class='container'>{p1}{p2}{p3}{p4}{p5}{p6}</div></body></html>"


def salvar_html(html: str, caminho_saida: str) -> None:
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Relatório salvo em: {caminho_saida}")
