"""
analyzer.py
-----------
Calcula todos os índices analíticos das sprints.
"""

import math
from datetime import datetime


# ── Haversine ─────────────────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Retorna distância em metros entre dois pontos GPS."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _retidao_label(indice: float) -> str:
    if indice >= 0.995:
        return "Excelente"
    elif indice >= 0.985:
        return "Boa"
    elif indice >= 0.970:
        return "Regular"
    else:
        return "Irregular"


# ── Sustentação e Consistência ────────────────────────────────────────────────

def _classificar(sustentacao: float) -> str:
    if sustentacao >= 1.03:
        return "Progressivo"
    elif sustentacao >= 0.99:
        return "Muito consistente"
    elif sustentacao >= 0.96:
        return "Consistente"
    elif sustentacao >= 0.92:
        return "Queda moderada"
    else:
        return "Quebrou"


def calcular_indices_sprint(sprint: dict) -> dict:
    velocidades = [
        float(sprint[f"VelParte{i}_kmh"])
        for i in range(1, 5)
        if sprint.get(f"VelParte{i}_kmh") not in (None, "")
    ]

    if len(velocidades) < 2:
        sprint["IndiceSustentacao"]   = None
        sprint["IndiceConsistencia"]  = None
        sprint["ClassificacaoSprint"] = "Indefinido"
        return sprint

    metade      = len(velocidades) // 2
    media_prim  = sum(velocidades[:metade]) / metade
    media_ult   = sum(velocidades[metade:]) / len(velocidades[metade:])
    media_total = sum(velocidades) / len(velocidades)

    sustentacao  = media_ult / media_prim if media_prim > 0 else None
    desvio       = math.sqrt(sum((v - media_total) ** 2 for v in velocidades) / len(velocidades))
    consistencia = desvio / media_total if media_total > 0 else None

    sprint["IndiceSustentacao"]   = round(sustentacao, 3)  if sustentacao  is not None else None
    sprint["IndiceConsistencia"]  = round(consistencia, 4) if consistencia is not None else None
    sprint["ClassificacaoSprint"] = _classificar(sustentacao) if sustentacao is not None else "Indefinido"

    # Índice de Retidão: distância reta (Haversine) / distância real percorrida
    lat_ini = sprint.get("LatInicio")
    lon_ini = sprint.get("LonInicio")
    lat_fim = sprint.get("LatFim")
    lon_fim = sprint.get("LonFim")
    dist_real = sprint.get("DistSprint_real")

    if all(v is not None for v in [lat_ini, lon_ini, lat_fim, lon_fim]) and dist_real and dist_real > 0:
        dist_reta = _haversine(lat_ini, lon_ini, lat_fim, lon_fim)
        indice_ret = min(round(dist_reta / dist_real, 4), 1.0)
        sprint["DistRetaMetros"]   = round(dist_reta, 1)
        sprint["IndiceRetidao"]    = indice_ret
        sprint["RetidaoLabel"]     = _retidao_label(indice_ret)
    else:
        sprint["DistRetaMetros"]   = None
        sprint["IndiceRetidao"]    = None
        sprint["RetidaoLabel"]     = "Sem dados"

    return sprint


# ── Min/Max globais ───────────────────────────────────────────────────────────

def calcular_extremos_treino(sprints: list[dict]) -> list[dict]:
    susts = [s["IndiceSustentacao"] for s in sprints if s.get("IndiceSustentacao") is not None]
    cons  = [s["IndiceConsistencia"] for s in sprints if s.get("IndiceConsistencia") is not None]
    vels  = [s["VelSprint_kmh"]      for s in sprints if s.get("VelSprint_kmh")      is not None]
    rets  = [s["IndiceRetidao"]       for s in sprints if s.get("IndiceRetidao")       is not None]

    extremos = {}
    if susts:
        extremos["SustMinTreino"] = round(min(susts), 4)
        extremos["SustMaxTreino"] = round(max(susts), 4)
    if cons:
        extremos["ConsMinTreino"] = round(min(cons), 4)
        extremos["ConsMaxTreino"] = round(max(cons), 4)
    if vels:
        extremos["VelMinTreino"] = round(min(vels), 4)
        extremos["VelMaxTreino"] = round(max(vels), 4)
    if rets:
        extremos["RetMinTreino"] = round(min(rets), 4)
        extremos["RetMaxTreino"] = round(max(rets), 4)

    for sprint in sprints:
        sprint.update(extremos)

    return sprints


# ── Normalização e Score ──────────────────────────────────────────────────────

def normalizar_e_pontuar(
    sprints: list[dict],
    peso_velocidade: float = 50,
    peso_sustentacao: float = 30,
    peso_consistencia: float = 20,
) -> list[dict]:
    for s in sprints:
        vel_min = s.get("VelMinTreino", 0)
        vel_max = s.get("VelMaxTreino", 1)
        sus_min = s.get("SustMinTreino", 0)
        sus_max = s.get("SustMaxTreino", 1)
        con_min = s.get("ConsMinTreino", 0)
        con_max = s.get("ConsMaxTreino", 1)

        vel_n = (
            round((s["VelSprint_kmh"] - vel_min) / (vel_max - vel_min), 2)
            if vel_max != vel_min else 0.0
        )
        sus_n = (
            round((s["IndiceSustentacao"] - sus_min) / (sus_max - sus_min), 2)
            if sus_max != sus_min and s.get("IndiceSustentacao") is not None else 0.0
        )
        con_n = (
            round(1 - (s["IndiceConsistencia"] - con_min) / (con_max - con_min), 2)
            if con_max != con_min and s.get("IndiceConsistencia") is not None else 0.0
        )

        s["VelocidadeNormalizada"]   = vel_n
        s["SustentacaoNormalizada"]  = sus_n
        s["ConsistenciaNormalizada"] = con_n

        pw = peso_velocidade / 100
        ps = peso_sustentacao / 100
        pc = peso_consistencia / 100
        s["ScoreSprint"] = round(100 * (pw * vel_n + ps * sus_n + pc * con_n), 2)
        s["Eficiencia"]  = round(vel_n * (s.get("IndiceSustentacao") or 0), 2)

        if s.get("TimeFimSprint"):
            dt = datetime.fromisoformat(s["TimeFimSprint"])
            s["DateTimeTreino"] = dt.strftime("%d/%m/%Y")
        else:
            s["DateTimeTreino"] = ""

        s["DateTimeNow"] = datetime.now().strftime("%d/%m/%Y")

    return sprints


# ── Numeração ordinal ─────────────────────────────────────────────────────────

def numerar_sprints(sprints: list[dict]) -> list[dict]:
    por_execucao = sorted(sprints, key=lambda s: s["OrdemInicio"])
    for i, s in enumerate(por_execucao):
        s["OrdemExecucaoSprint"] = i + 1

    por_score = sorted(sprints, key=lambda s: s.get("ScoreSprint", 0), reverse=True)
    for i, s in enumerate(por_score):
        s["OrdemScore"] = i + 1

    return sprints


# ── Pipeline completo ─────────────────────────────────────────────────────────

def analisar(
    sprints: list[dict],
    peso_velocidade: float = 50,
    peso_sustentacao: float = 30,
    peso_consistencia: float = 20,
) -> list[dict]:
    for s in sprints:
        calcular_indices_sprint(s)
    sprints = calcular_extremos_treino(sprints)
    sprints = normalizar_e_pontuar(
        sprints,
        peso_velocidade=peso_velocidade,
        peso_sustentacao=peso_sustentacao,
        peso_consistencia=peso_consistencia,
    )
    sprints = numerar_sprints(sprints)
    return sprints
