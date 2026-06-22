"""
analyzer.py
-----------
Calcula todos os índices analíticos das sprints, agrupando por distância alvo.
Grupos com apenas 1 tiro recebem Score=None e aviso de incomparabilidade.
"""

import math
from datetime import datetime


# ── Haversine ─────────────────────────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _retidao_label(indice):
    if indice >= 0.995: return "Excelente"
    elif indice >= 0.985: return "Boa"
    elif indice >= 0.970: return "Regular"
    else: return "Irregular"


# ── Sustentação, Consistência e Retidão ───────────────────────────────────────

def _classificar(sustentacao):
    if sustentacao >= 1.03:   return "Progressivo"
    elif sustentacao >= 0.99: return "Muito consistente"
    elif sustentacao >= 0.96: return "Consistente"
    elif sustentacao >= 0.92: return "Queda moderada"
    else:                     return "Quebrou"


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
    else:
        metade     = len(velocidades) // 2
        media_prim = sum(velocidades[:metade]) / metade
        media_ult  = sum(velocidades[metade:]) / len(velocidades[metade:])
        media_tot  = sum(velocidades) / len(velocidades)
        sust = media_ult / media_prim if media_prim > 0 else None
        desvio = math.sqrt(sum((v - media_tot)**2 for v in velocidades) / len(velocidades))
        cons = desvio / media_tot if media_tot > 0 else None
        sprint["IndiceSustentacao"]   = round(sust, 3) if sust is not None else None
        sprint["IndiceConsistencia"]  = round(cons, 4) if cons is not None else None
        sprint["ClassificacaoSprint"] = _classificar(sust) if sust is not None else "Indefinido"

    # Retidão
    lat_ini = sprint.get("LatInicio"); lon_ini = sprint.get("LonInicio")
    lat_fim = sprint.get("LatFim");   lon_fim = sprint.get("LonFim")
    dist_real = sprint.get("DistSprint_real")
    if all(v is not None for v in [lat_ini, lon_ini, lat_fim, lon_fim]) and dist_real and dist_real > 0:
        dist_reta = _haversine(lat_ini, lon_ini, lat_fim, lon_fim)
        indice_ret = min(round(dist_reta / dist_real, 4), 1.0)
        sprint["DistRetaMetros"] = round(dist_reta, 1)
        sprint["IndiceRetidao"]  = indice_ret
        sprint["RetidaoLabel"]   = _retidao_label(indice_ret)
    else:
        sprint["DistRetaMetros"] = None
        sprint["IndiceRetidao"]  = None
        sprint["RetidaoLabel"]   = "Sem dados"

    return sprint


# ── Normalização e Score por grupo ────────────────────────────────────────────

def _normalizar_grupo(
    grupo: list[dict],
    peso_velocidade: float,
    peso_sustentacao: float,
    peso_consistencia: float,
) -> list[dict]:
    """
    Normaliza e calcula Score para um grupo de tiros da mesma distância.
    Se o grupo tiver apenas 1 tiro, Score=None e ScoreComparavel=False.
    """
    unico = len(grupo) == 1

    vels  = [s["VelSprint_kmh"]     for s in grupo if s.get("VelSprint_kmh")     is not None]
    susts = [s["IndiceSustentacao"]  for s in grupo if s.get("IndiceSustentacao")  is not None]
    conss = [s["IndiceConsistencia"] for s in grupo if s.get("IndiceConsistencia") is not None]

    vel_min, vel_max = (min(vels), max(vels)) if vels else (0, 1)
    sus_min, sus_max = (min(susts), max(susts)) if susts else (0, 1)
    con_min, con_max = (min(conss), max(conss)) if conss else (0, 1)

    for s in grupo:
        s["VelMinTreino"]  = round(vel_min, 4); s["VelMaxTreino"]  = round(vel_max, 4)
        s["SustMinTreino"] = round(sus_min, 4); s["SustMaxTreino"] = round(sus_max, 4)
        s["ConsMinTreino"] = round(con_min, 4); s["ConsMaxTreino"] = round(con_max, 4)
        s["ScoreComparavel"] = not unico

        if unico:
            # Score não comparável — exibe índices brutos sem normalização
            s["VelocidadeNormalizada"]   = None
            s["SustentacaoNormalizada"]  = None
            s["ConsistenciaNormalizada"] = None
            s["ScoreSprint"]             = None
            s["Eficiencia"]              = None
        else:
            vel_n = round((s["VelSprint_kmh"] - vel_min) / (vel_max - vel_min), 2) if vel_max != vel_min else 0.0
            sus_n = (round((s["IndiceSustentacao"] - sus_min) / (sus_max - sus_min), 2)
                     if sus_max != sus_min and s.get("IndiceSustentacao") is not None else 0.0)
            con_n = (round(1 - (s["IndiceConsistencia"] - con_min) / (con_max - con_min), 2)
                     if con_max != con_min and s.get("IndiceConsistencia") is not None else 0.0)
            s["VelocidadeNormalizada"]   = vel_n
            s["SustentacaoNormalizada"]  = sus_n
            s["ConsistenciaNormalizada"] = con_n
            pw = peso_velocidade / 100
            ps = peso_sustentacao / 100
            pc = peso_consistencia / 100
            s["ScoreSprint"] = round(100 * (pw * vel_n + ps * sus_n + pc * con_n), 2)
            s["Eficiencia"]  = round(vel_n * (s.get("IndiceSustentacao") or 0), 2)

        if s.get("TimeFimSprint"):
            s["DateTimeTreino"] = datetime.fromisoformat(s["TimeFimSprint"]).strftime("%d/%m/%Y")
        else:
            s["DateTimeTreino"] = ""
        s["DateTimeNow"] = datetime.now().strftime("%d/%m/%Y")

    return grupo


# ── Numeração ordinal ─────────────────────────────────────────────────────────

def numerar_sprints(sprints: list[dict]) -> list[dict]:
    """
    OrdemExecucaoSprint: ordem de execução no treino (global, todas as distâncias).
    OrdemScore: ranking por Score dentro do grupo de distância.
    SprintRank_Vel: ranking por velocidade dentro do grupo de distância.
    """
    # Ordem de execução global (já estão ordenadas pelo detector)
    for i, s in enumerate(sprints):
        s["OrdemExecucaoSprint"] = i + 1

    # Ranking por Score e Velocidade dentro de cada grupo de distância
    grupos = {}
    for s in sprints:
        d = s.get("DistSprint_alvo", s.get("DistSprint_real", 0))
        grupos.setdefault(d, []).append(s)

    for grupo in grupos.values():
        # Rank velocidade
        por_vel = sorted(grupo, key=lambda s: s["VelSprint_kmh"], reverse=True)
        for i, s in enumerate(por_vel):
            s["SprintRank_Vel"] = i + 1
        # Rank score (só se comparável)
        comparaveis = [s for s in grupo if s.get("ScoreSprint") is not None]
        por_score = sorted(comparaveis, key=lambda s: s["ScoreSprint"], reverse=True)
        for i, s in enumerate(por_score):
            s["OrdemScore"] = i + 1
        # Tiros únicos não têm OrdemScore
        for s in grupo:
            if "OrdemScore" not in s:
                s["OrdemScore"] = None

    return sprints


# ── Pipeline completo ─────────────────────────────────────────────────────────

def analisar(
    sprints: list[dict],
    peso_velocidade: float = 50,
    peso_sustentacao: float = 30,
    peso_consistencia: float = 20,
) -> list[dict]:
    """
    Executa toda a cadeia de análise.
    Agrupa por DistSprint_alvo para normalização e Score.
    """
    # 1. Índices individuais
    for s in sprints:
        calcular_indices_sprint(s)

    # 2. Agrupa por distância alvo e normaliza dentro de cada grupo
    grupos = {}
    for s in sprints:
        d = s.get("DistSprint_alvo", s.get("DistSprint_real", 0))
        grupos.setdefault(d, []).append(s)

    for grupo in grupos.values():
        _normalizar_grupo(grupo, peso_velocidade, peso_sustentacao, peso_consistencia)

    # 3. Numeração ordinal
    numerar_sprints(sprints)

    return sprints
