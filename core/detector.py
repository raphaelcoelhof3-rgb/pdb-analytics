"""
detector.py
-----------
Detecta os tiros dentro dos trackpoints.

Suporta dois modos:
  - Distância única: todos os tiros têm a mesma distância
  - Distâncias variadas: cada tiro tem sua própria distância (lista ordenada)

Em ambos os casos, o detector busca os tiros em sequência temporal,
respeitando a ordem de execução e evitando sobreposições.
"""

from datetime import datetime


def _detectar_melhor_tiro(
    registros: list[dict],
    distancia_sprint: float,
    numero_partes: int,
    a_partir_de: int,
    intervalos_aceitos: list,
) -> dict | None:
    """
    Busca o melhor tiro (maior velocidade) de `distancia_sprint` metros
    começando a partir do índice `a_partir_de`, sem sobrepor intervalos já aceitos.
    Retorna o dicionário do tiro ou None se não encontrar.
    """
    dist_parte = distancia_sprint / numero_partes
    n = len(registros)
    candidatas = []

    for i in range(a_partir_de, n):
        dist_inicial = float(registros[i]["Distance_metros"])
        limites = []

        for p in range(1, numero_partes + 1):
            alvo = dist_inicial + (dist_parte * p)
            indice = next(
                (j for j in range(i + 1, n)
                 if float(registros[j]["Distance_metros"]) >= alvo),
                None
            )
            if indice is None:
                limites = []
                break
            limites.append(indice)

        if len(limites) != numero_partes:
            continue

        j_fim = limites[-1]

        # Verifica sobreposição com tiros já aceitos
        ini = int(registros[i]["Ordem"])
        fim = int(registros[j_fim]["Ordem"])
        if any(not (fim < a[0] or ini > a[1]) for a in intervalos_aceitos):
            continue

        dt_ini = datetime.fromisoformat(registros[i]["Time"])
        dt_fim = datetime.fromisoformat(registros[j_fim]["Time"])
        tempo_total = (dt_fim - dt_ini).total_seconds()
        if tempo_total <= 0:
            continue

        dist_total = float(registros[j_fim]["Distance_metros"]) - dist_inicial
        vel_total  = (dist_total / tempo_total) * 3.6
        qtd_reg    = (j_fim - i) + 1
        intervalo_medio = tempo_total / (qtd_reg - 1) if qtd_reg > 1 else None

        vels_suav = [
            float(registros[k]["km/h_suavizada"])
            for k in range(i, j_fim + 1)
            if registros[k].get("km/h_suavizada") not in (None, "")
        ]

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
            "OrdemInicio":        ini,
            "OrdemFim":           fim,
            "TimeInicioSprint":   registros[i]["Time"],
            "TimeFimSprint":      registros[j_fim]["Time"],
            "VelSprint_kmh":      round(vel_total, 2),
            "TempoSprint_s":      round(tempo_total, 1),
            "DistSprint_real":    round(dist_total, 2),
            "DistSprint_alvo":    distancia_sprint,
            "QtdRegSprint":       qtd_reg,
            "IntervaloMedio_s":   round(intervalo_medio, 2) if intervalo_medio else None,
            "VelMaxSuavizada":    round(max(vels_suav), 2) if vels_suav else None,
            "VelMinSuavizada":    round(min(vels_suav), 2) if vels_suav else None,
            "VelMediaSuavizada":  round(sum(vels_suav) / len(vels_suav), 2) if vels_suav else None,
            "LatInicio":   registros[i].get("Latitude"),
            "LonInicio":   registros[i].get("Longitude"),
            "LatFim":      registros[j_fim].get("Latitude"),
            "LonFim":      registros[j_fim].get("Longitude"),
            "CoordsTraco": coords_tiro,
            "_idx_inicio": i,
            "_idx_fim":    j_fim,
        }

        # Partes
        inicio_idx = i
        for parte in range(numero_partes):
            fim_idx = limites[parte]
            dt1 = datetime.fromisoformat(registros[inicio_idx]["Time"])
            dt2 = datetime.fromisoformat(registros[fim_idx]["Time"])
            t_parte = (dt2 - dt1).total_seconds()
            d_parte = float(registros[fim_idx]["Distance_metros"]) - float(registros[inicio_idx]["Distance_metros"])
            if t_parte > 0:
                sprint[f"VelParte{parte+1}_kmh"] = round((d_parte / t_parte) * 3.6, 2)
                sprint[f"TempoParte{parte+1}_s"]  = round(t_parte, 1)
                sprint[f"DistParte{parte+1}_m"]   = round(d_parte, 1)
            else:
                sprint[f"VelParte{parte+1}_kmh"] = None
                sprint[f"TempoParte{parte+1}_s"]  = None
                sprint[f"DistParte{parte+1}_m"]   = None
            inicio_idx = fim_idx

        for parte in range(numero_partes + 1, 5):
            sprint[f"VelParte{parte}_kmh"] = None
            sprint[f"TempoParte{parte}_s"]  = None
            sprint[f"DistParte{parte}_m"]   = None

        dist_base = float(registros[i]["Distance_metros"])
        sprint["SerieGrafico"] = [
            {
                "dist_rel": round(float(registros[k]["Distance_metros"]) - dist_base, 1),
                "vel": registros[k].get("km/h_suavizada") or registros[k].get("km/h") or 0,
            }
            for k in range(i, j_fim + 1)
            if registros[k].get("Distance_metros") is not None
        ]

        candidatas.append(sprint)

    if not candidatas:
        return None

    # Retorna o de maior velocidade
    return max(candidatas, key=lambda s: s["VelSprint_kmh"])


def detect_sprints(
    trackpoints: list[dict],
    distancia_sprint: float | list,
    numero_partes: int,
    qtd_tiros: int,
) -> list[dict]:
    """
    Detecta os tiros nos trackpoints.

    distancia_sprint pode ser:
      - float: mesma distância para todos os tiros
      - list[float]: distância específica para cada tiro, na ordem de execução

    Retorna lista de sprints na ordem de execução, cada uma com
    DistSprint_alvo indicando a distância alvo daquele tiro.
    """
    registros = sorted(trackpoints, key=lambda f: int(f["Ordem"]))
    registros = [
        r for r in registros
        if r.get("Ordem") not in (None, "")
        and r.get("Distance_metros") not in (None, "")
        and r.get("Time") not in (None, "")
    ]

    # Normaliza para lista de distâncias
    if isinstance(distancia_sprint, (int, float)):
        distancias = [float(distancia_sprint)] * qtd_tiros
    else:
        distancias = [float(d) for d in distancia_sprint]

    intervalos_aceitos = []
    validas = []
    proximo_inicio = 0

    for pos, dist in enumerate(distancias):
        tiro = _detectar_melhor_tiro(
            registros=registros,
            distancia_sprint=dist,
            numero_partes=numero_partes,
            a_partir_de=proximo_inicio,
            intervalos_aceitos=intervalos_aceitos,
        )

        if tiro is None:
            break

        tiro["SprintRank_Vel"] = pos + 1  # será recalculado por grupo no analyzer
        intervalos_aceitos.append((tiro["OrdemInicio"], tiro["OrdemFim"]))
        # Avança o próximo início para logo após o fim deste tiro no array de registros
        idx_fim = tiro.pop("_idx_fim")
        tiro.pop("_idx_inicio", None)
        # Encontra o índice no array registros correspondente ao OrdemFim
        proximo_inicio = next(
            (k for k in range(idx_fim, len(registros))
             if int(registros[k]["Ordem"]) == tiro["OrdemFim"]),
            idx_fim
        ) + 1
        validas.append(tiro)

    return validas
