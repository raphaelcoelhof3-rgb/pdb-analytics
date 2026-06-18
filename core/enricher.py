"""
enricher.py
-----------
Enriquece os trackpoints com:
  - Distância e duração total do treino        (≡ PythonCaller2)
  - km/h_anterior, km/h_aumento               (≡ AttributeCreator2 e 3)
  - Time_anterior, IntervaloTempo              (≡ AttributeCreator4 + DateTimeCalculator)
  - km/h_suavizada (média ponderada 5 pontos)  (≡ AttributeCreator5)
  - Aceleracao, Aceleracao_suavizada           (≡ AttributeCreator6)
"""

from datetime import datetime


def enrich_trackpoints(trackpoints: list[dict]) -> list[dict]:
    """Adiciona todos os campos calculados a cada trackpoint."""

    if not trackpoints:
        return trackpoints

    # ── Totais do treino (PythonCaller2) ──────────────────────────────────────
    dist_max = 0.0
    tempo_min = None
    tempo_max = None

    for tp in trackpoints:
        dist = tp.get("Distance_metros")
        tempo = tp.get("Time")

        if dist is not None and float(dist) > dist_max:
            dist_max = float(dist)

        if tempo:
            dt = datetime.fromisoformat(tempo)
            if tempo_min is None or dt < tempo_min:
                tempo_min = dt
            if tempo_max is None or dt > tempo_max:
                tempo_max = dt

    duracao_min = (tempo_max - tempo_min).total_seconds() / 60.0 if tempo_min and tempo_max else 0.0

    for tp in trackpoints:
        tp["TreinoDistancia_m"] = round(dist_max, 1)
        tp["TreinoDuracao_min"] = round(duracao_min, 1)

    # ── Velocidade anterior e variação (AttributeCreators 2 e 3) ─────────────
    for i, tp in enumerate(trackpoints):
        prev = trackpoints[i - 1] if i > 0 else None
        tp["km/h_anterior"] = prev.get("km/h") if prev else None
        vel_atual = tp.get("km/h")
        vel_ant = tp.get("km/h_anterior")
        if vel_atual is not None and vel_ant is not None:
            tp["km/h_aumento"] = round(float(vel_atual) - float(vel_ant), 2)
        else:
            tp["km/h_aumento"] = None

    # ── Intervalo de tempo entre pontos (AttributeCreator4 + DateTimeCalculator)
    for i, tp in enumerate(trackpoints):
        prev = trackpoints[i - 1] if i > 0 else None
        tp["Time_anterior"] = prev.get("Time") if prev else None
        if tp["Time_anterior"] and tp.get("Time"):
            dt1 = datetime.fromisoformat(tp["Time_anterior"])
            dt2 = datetime.fromisoformat(tp["Time"])
            tp["IntervaloTempo"] = (dt2 - dt1).total_seconds()
        else:
            tp["IntervaloTempo"] = None

    # ── Velocidade suavizada — média ponderada 5 pontos (AttributeCreator5) ──
    # Formula original: (vel[-2]*dt[-2] + vel[-1]*dt[-1] + vel[0]*dt[0] +
    #                    vel[+1]*dt[+1] + vel[+2]*dt[+2])
    #                 / (dt[-2]+dt[-1]+dt[0]+dt[+1]+dt[+2])
    n = len(trackpoints)
    for i, tp in enumerate(trackpoints):
        vizinhos = range(max(0, i - 2), min(n, i + 3))
        num = 0.0
        den = 0.0
        valido = True
        for j in vizinhos:
            vel = trackpoints[j].get("km/h")
            dt  = trackpoints[j].get("IntervaloTempo")
            if vel is None or dt is None:
                valido = False
                break
            num += float(vel) * float(dt)
            den += float(dt)
        if valido and den > 0:
            tp["km/h_suavizada"] = round(num / den, 2)
        else:
            tp["km/h_suavizada"] = tp.get("km/h")  # fallback: valor bruto

    # ── Aceleração (AttributeCreator6) ────────────────────────────────────────
    for i, tp in enumerate(trackpoints):
        prev = trackpoints[i - 1] if i > 0 else None
        dt = tp.get("IntervaloTempo")

        vel_atual = tp.get("km/h")
        vel_ant   = prev.get("km/h") if prev else None
        if vel_atual is not None and vel_ant is not None and dt and float(dt) > 0:
            tp["Aceleracao"] = round((float(vel_atual) - float(vel_ant)) / float(dt), 2)
        else:
            tp["Aceleracao"] = None

        vel_s_atual = tp.get("km/h_suavizada")
        vel_s_ant   = prev.get("km/h_suavizada") if prev else None
        if vel_s_atual is not None and vel_s_ant is not None and dt and float(dt) > 0:
            tp["Aceleracao_suavizada"] = round((float(vel_s_atual) - float(vel_s_ant)) / float(dt), 2)
        else:
            tp["Aceleracao_suavizada"] = None

    return trackpoints
