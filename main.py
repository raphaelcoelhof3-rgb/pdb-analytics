"""
main.py
-------
Ponto de entrada do projeto Canoa Analytics.
Orquestra todas as etapas do pipeline:
  1. Lê as configurações do usuário (inputs/config.py)
  2. Faz o parse do arquivo TCX
  3. Enriquece os trackpoints
  4. Detecta as sprints
  5. Analisa e pontua
  6. Gera e salva o relatório HTML

Uso:
    python main.py
"""

import os
import sys

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.dirname(__file__))

from inputs import config
from core.parser import parse_tcx
from core.enricher import enrich_trackpoints
from core.detector import detect_sprints
from core.analyzer import analisar
from report.builder import gerar_html, salvar_html


def main():
    print("=" * 50)
    print("  CANOA ANALYTICS — Gerador de Relatório")
    print("=" * 50)

    # ── 1. Configurações ──────────────────────────────
    cfg = {
        "TCX_FILE":        config.TCX_FILE,
        "NOME_CLUB":       config.NOME_CLUB,
        "CANOA_TIPO":      config.CANOA_TIPO,
        "NOMES_MEMBROS":   config.NOMES_MEMBROS,
        "DISTANCIA_SPRINT": config.DISTANCIA_SPRINT,
        "NUMERO_PARTES":   config.NUMERO_PARTES,
        "QTD_TIROS":       config.QTD_TIROS,
        "PESO_VELOCIDADE":   config.PESO_VELOCIDADE,
        "PESO_SUSTENTACAO":  config.PESO_SUSTENTACAO,
        "PESO_CONSISTENCIA": config.PESO_CONSISTENCIA,
    }

    print(f"\nArquivo TCX : {cfg['TCX_FILE']}")
    print(f"Clube       : {cfg['NOME_CLUB']}")
    print(f"Canoa       : {cfg['CANOA_TIPO']}")
    print(f"Sprint      : {cfg['DISTANCIA_SPRINT']}m em {cfg['NUMERO_PARTES']} partes")
    print(f"Tiros       : {cfg['QTD_TIROS']}")

    if not os.path.exists(cfg["TCX_FILE"]):
        print(f"\n[ERRO] Arquivo TCX não encontrado: {cfg['TCX_FILE']}")
        sys.exit(1)

    # ── 2. Parse do TCX ───────────────────────────────
    print("\n[1/4] Lendo arquivo TCX...")
    trackpoints = parse_tcx(cfg["TCX_FILE"])
    print(f"      {len(trackpoints)} trackpoints carregados.")

    # ── 3. Enriquecimento ─────────────────────────────
    print("[2/4] Calculando velocidade suavizada e aceleração...")
    trackpoints = enrich_trackpoints(trackpoints)

    # ── 4. Detecção de sprints ────────────────────────
    print("[3/4] Detectando sprints...")
    # DISTANCIA_SPRINT pode ser float (única) ou list (variada por tiro)
    distancia = cfg.get("LISTA_DISTANCIAS") or cfg["DISTANCIA_SPRINT"]
    sprints = detect_sprints(
        trackpoints,
        distancia_sprint=distancia,
        numero_partes=cfg["NUMERO_PARTES"],
        qtd_tiros=cfg["QTD_TIROS"],
    )
    print(f"      {len(sprints)} sprint(s) válida(s) encontrada(s).")

    if len(sprints) == 0:
        print("\n[AVISO] Nenhuma sprint detectada. Verifique as configurações.")
        sys.exit(0)

    # ── 5. Análise ────────────────────────────────────
    print("[4/4] Calculando scores e índices...")
    sprints = analisar(
        sprints,
        peso_velocidade=cfg["PESO_VELOCIDADE"],
        peso_sustentacao=cfg["PESO_SUSTENTACAO"],
        peso_consistencia=cfg["PESO_CONSISTENCIA"],
    )

    # ── 6. Relatório HTML ─────────────────────────────
    html = gerar_html(sprints, cfg)

    nome_saida = os.path.splitext(cfg["TCX_FILE"])[0] + "_relatorio.html"
    salvar_html(html, nome_saida)

    print("\n✅ Concluído!")
    print(f"   Abra o arquivo '{nome_saida}' no seu navegador.")
    print("=" * 50)


if __name__ == "__main__":
    main()
