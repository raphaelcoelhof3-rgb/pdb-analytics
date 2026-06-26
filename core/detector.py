"""
detector.py
-----------
Detecta as sprints dentro dos trackpoints.
  - Identifica todos os intervalos que cobrem a distância da sprint (≡ PythonCaller3)
  - Remove sprints sobrepostas, mantendo apenas as não sobrepostas (≡ PythonCaller4)
  - Filtra pela quantidade de tiros informada pelo usuário               (≡ TestFilter1 e 2)
  - Preserva coordenadas GPS de todos os trackpoints de cada tiro (mapa + retidão)
"""

from datetime import datetime


def detect_sprints(
    trackpoints: list[dict],
    distancia_sprint: float,
    numero_partes: int,
    qtd_tiros: int,
) -> list[dict]:
    """
    Retorna lista de dicionários, um por sprint válida detectada.
    Cada dicionário contém todos os atributos calculados para a sprint,
    incluindo CoordsTraco (lista de {lat, lon} de todos os trackpoints do tiro).
    """

    dist_parte = distancia_sprint / numero_partes

    registros = sorted(trackpoints, key=lambda f: int(f["Ordem"]))
    registros = [
        r for r in registros
        if r.get("Ordem") not in (None, "")
        and r.get("Distance_metros") not in (None, "")
        and r.get("Time") not in (None, "")
    ]

    n = len(registros)
    candidatas = []

    for i in range(n):
        dist_inicial = float(registros[i]["Distance_metros"])
        limites = []

        for p in range(1, numero_partes + 1):
            alvo = dist_inicial + (dist_parte * p)
            indice = None
            for j in range(i + 1, n):
                if float(registros[j]["Distance_metros"]) >= alvo:
                    indice = j
                    break
            if indice is None:
                limites = []
                break
            limites.append(indice)

        if len(limites) != numero_partes:
            continue

        j_fim = limites[-1]
        dt_ini = datetime.fromisoformat(registros[i]["Time"])
        dt_fim = datetime.fromisoformat(registros[j_fim]["Time"])
        tempo_total = (dt_fim - dt_ini).total_seconds()

        if tempo_total <= 0:
            continue

        dist_total = float(registros[j_fim]["Distance_metros"]) - dist_inicial
        vel_total  = (dist_total / tempo_total) * 3.6
        qtd_reg    = (j_fim - i) + 1
        intervalo_medio = tempo_total / (qtd_reg - 1) if qtd_reg > 1 else None

        # Velocidades suavizadas no intervalo
        vels_suav = [
            float(registros[k]["km/h_suavizada"])
            for k in range(i, j_fim + 1)
            if registros[k].get("km/h_suavizada") not in (None, "")
        ]

        # Coordenadas GPS de todos os trackpoints do tiro (mapa + retidão)
        coords_tiro = [
            {"lat": registros[k]["Latitude"], "lon": registros[k]["Longitude"]}
            for k in range(i, j_fim + 1)
            if registros[k].get("Latitude") is not None
            and registros[k].get("Longitude") is not None
        ]

        tp_ref = registros[i]
        sprint = {
            "TreinoDuracao_min":  tp_ref.get("TreinoDuracao_min"),
            "TreinoDistancia_m":  tp_ref.get("TreinoDistancia_m"),
            "OrdemInicio":        int(registros[i]["Ordem"]),
            "OrdemFim":           int(registros[j_fim]["Ordem"]),
            "TimeInicioSprint":   registros[i]["Time"],
            "TimeFimSprint":      registros[j_fim]["Time"],
            "VelSprint_kmh":      round(vel_total, 2),
            "TempoSprint_s":      round(tempo_total, 1),
            "DistSprint_real":    round(dist_total, 2),
            "QtdRegSprint":       qtd_reg,
            "IntervaloMedio_s":   round(intervalo_medio, 2) if intervalo_medio else None,
            "VelMaxSuavizada":    round(max(vels_suav), 2) if vels_suav else None,
            "VelMinSuavizada":    round(min(vels_suav), 2) if vels_suav else None,
            "VelMediaSuavizada":  round(sum(vels_suav) / len(vels_suav), 2) if vels_suav else None,
            # GPS: ponto de início, fim e traçado completo do tiro
            "LatInicio":   registros[i].get("Latitude"),
            "LonInicio":   registros[i].get("Longitude"),
            "LatFim":      registros[j_fim].get("Latitude"),
            "LonFim":      registros[j_fim].get("Longitude"),
            "CoordsTraco": coords_tiro,
        }

        # Velocidade, tempo e distância real de cada parte
        inicio_idx = i
        for parte in range(numero_partes):
            fim_idx = limites[parte]
            dt1 = datetime.fromisoformat(registros[inicio_idx]["Time"])
            dt2 = datetime.fromisoformat(registros[fim_idx]["Time"])
            t_parte = (dt2 - dt1).total_seconds()
            d_parte = float(registros[fim_idx]["Distance_metros"]) - float(registros[inicio_idx]["Distance_metros"])
            if t_parte > 0:
                sprint[f"VelParte{parte+1}_kmh"]  = round((d_parte / t_parte) * 3.6, 2)
                sprint[f"TempoParte{parte+1}_s"]   = round(t_parte, 1)
                sprint[f"DistParte{parte+1}_m"]    = round(d_parte, 1)
            else:
                sprint[f"VelParte{parte+1}_kmh"]  = None
                sprint[f"TempoParte{parte+1}_s"]   = None
                sprint[f"DistParte{parte+1}_m"]    = None
            inicio_idx = fim_idx

        for parte in range(numero_partes + 1, 5):
            sprint[f"VelParte{parte}_kmh"] = None
            sprint[f"TempoParte{parte}_s"]  = None
            sprint[f"DistParte{parte}_m"]   = None

        # Série de velocidade suavizada x distância relativa (para gráficos)
        dist_base = float(registros[i]["Distance_metros"])
        serie_grafico = [
            {
                "dist_rel": round(float(registros[k]["Distance_metros"]) - dist_base, 1),
                "vel":      registros[k].get("km/h_suavizada") or registros[k].get("km/h") or 0,
            }
            for k in range(i, j_fim + 1)
            if registros[k].get("Distance_metros") is not None
        ]
        sprint["SerieGrafico"] = serie_grafico

        candidatas.append(sprint)

    # Ordena por velocidade e remove sobreposições
    candidatas.sort(key=lambda s: s["VelSprint_kmh"], reverse=True)

    intervalos_aceitos = []
    sprint_rank_vel = 1
    validas = []

    for sprint in candidatas:
        ini = sprint["OrdemInicio"]
        fim = sprint["OrdemFim"]
        sobrepoe = any(
            not (fim < a_ini or ini > a_fim)
            for a_ini, a_fim in intervalos_aceitos
        )
        if sobrepoe:
            continue

        sprint["SprintRank_Vel"] = sprint_rank_vel
        intervalos_aceitos.append((ini, fim))
        validas.append(sprint)
        sprint_rank_vel += 1

    validas = validas[:qtd_tiros]
    return validas
