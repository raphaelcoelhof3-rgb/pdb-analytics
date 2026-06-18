"""
parser.py
---------
Lê o arquivo TCX exportado pelo Garmin e retorna uma lista de
dicionários, um por trackpoint, com os campos:
    Time, Latitude, Longitude, Distance_metros, bpm, m/s, km/h, Lap, Ordem

Regra de validade: um trackpoint só é incluído se tiver
  - Velocidade: tag <ns3:TPX> com <ns3:Speed> preenchida
  - Localização: tags <LatitudeDegrees> e <LongitudeDegrees> presentes
"""

import xml.etree.ElementTree as ET
from datetime import timezone, timedelta

NAMESPACES = {
    "ns":  "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ns2": "http://www.garmin.com/xmlschemas/UserProfile/v2",
    "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    "ns4": "http://www.garmin.com/xmlschemas/ProfileExtension/v1",
    "ns5": "http://www.garmin.com/xmlschemas/ActivityGoals/v1",
}

BRT = timezone(timedelta(hours=-3))


def parse_tcx(tcx_file: str) -> list[dict]:
    """
    Lê o TCX e devolve lista de trackpoints válidos como dicionários.
    Um trackpoint é válido se tiver velocidade (ns3:Speed preenchida)
    e localização geográfica (Latitude e Longitude presentes).
    Equivale ao PythonCaller1 do FME.
    """
    tree = ET.parse(tcx_file)
    root = tree.getroot()
    run = root[0][0]

    trackpoints = []
    ordem = 0

    for lap_number, lap in enumerate(run.findall("ns:Lap", NAMESPACES)):
        track = lap.find("ns:Track", NAMESPACES)
        if track is None:
            continue

        for tp in track.findall("ns:Trackpoint", NAMESPACES):
            record = {"Lap": lap_number + 1, "Ordem": ordem}
            ordem += 1  # incrementa sempre, mesmo para inválidos

            # ── Velocidade (obrigatória) ──────────────────────────────────────
            ext = tp.find("ns:Extensions", NAMESPACES)
            tpx = ext.find("ns3:TPX", NAMESPACES) if ext is not None else None
            speed_node = tpx.find("ns3:Speed", NAMESPACES) if tpx is not None else None

            if speed_node is None or speed_node.text is None:
                continue  # trackpoint inválido: sem velocidade

            try:
                velocidade = round(float(speed_node.text), 3)
            except (ValueError, TypeError):
                continue  # trackpoint inválido: velocidade não numérica

            # ── Localização (obrigatória) ─────────────────────────────────────
            pos = tp.find("ns:Position", NAMESPACES)
            if pos is None:
                continue  # trackpoint inválido: sem localização

            lat_node = pos.find("ns:LatitudeDegrees", NAMESPACES)
            lon_node = pos.find("ns:LongitudeDegrees", NAMESPACES)

            if lat_node is None or lon_node is None:
                continue  # trackpoint inválido: lat/lon ausentes

            # ── Campos válidos ────────────────────────────────────────────────
            record["Latitude"]  = float(lat_node.text)
            record["Longitude"] = float(lon_node.text)
            record["m/s"]  = velocidade
            record["km/h"] = round(velocidade * 3.6, 2)

            time_node = tp.find("ns:Time", NAMESPACES)
            if time_node is not None:
                utc_time = ET.fromstring(
                    f"<t>{time_node.text}</t>"
                ) if False else None
                # parse manual sem dependência externa
                raw = time_node.text.replace("Z", "+00:00")
                from datetime import datetime
                utc_time = datetime.fromisoformat(raw)
                record["Time"] = utc_time.astimezone(BRT).isoformat()

            dist_node = tp.find("ns:DistanceMeters", NAMESPACES)
            if dist_node is not None:
                record["Distance_metros"] = round(float(dist_node.text), 2)

            hr = tp.find("ns:HeartRateBpm", NAMESPACES)
            if hr is not None:
                record["bpm"] = int(hr[0].text)

            trackpoints.append(record)

    return trackpoints
