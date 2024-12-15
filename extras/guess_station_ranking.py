#!/usr/bin/env python3
# extras/guess_station_ranking.py
# copyright 2024 Kuupa Ork <kuupaork+github@hfdl.observer>
# see LICENSE (or https://github.com/hfdl-observer/hfdlobserver888/blob/main/LICENSE) for terms of use.
# TL;DR: BSD 3-clause
#
import math
import sys


# lame hack, include the groundstations file directly. If these change, this utility will be less useful.
stations = [
    {
        "id": 1,
        "lat": 38.384587,
        "lon": -121.759647,
        "frequencies": (21934.0, 17919.0, 13276.0, 11327.0, 10081.0, 8927.0, 6559.0, 5508.0,),
        "name": "San Francisco, California",
    },
    {
        "id": 2,
        "lat": 21.184428,
        "lon": -157.186846,
        "frequencies": (
            21937.0, 17919.0, 13324.0, 13312.0, 13276.0, 11348.0, 11312.0, 10027.0, 8936.0, 8912.0, 6565.0, 5514.0,
        ),
        "name": "Molokai, Hawaii",
    },
    {
        "id": 3,
        "lat": 63.847168,
        "lon": -22.455754,
        "frequencies": (17985.0, 15025.0, 11184.0, 8977.0, 6712.0, 5720.0, 3900.0),
        "name": "Reykjavik, Iceland",
    },
    {
        "id": 4,
        "lat": 40.881922,
        "lon": -72.63762,
        "frequencies": (21931.0, 17919.0, 13276.0, 11387.0, 8912.0, 6661.0, 5652.0),
        "name": "Riverhead, New York",
    },
    {
        "id": 5,
        "lat": -37.015757,
        "lon": 174.809637,
        "frequencies": (17916.0, 13351.0, 10084.0, 8921.0, 6535.0, 5583.0),
        "name": "Auckland, New Zealand",
    },
    {
        "id": 6,
        "lat": 6.937536,
        "lon": 100.388451,
        "frequencies": (21949.0, 17928.0, 13270.0, 10066.0, 8825.0, 6535.0, 5655.0),
        "name": "Hat Yai, Thailand",
    },
    {
        "id": 7,
        "lat": 52.744089,
        "lon": -8.926752,
        "frequencies": (11384.0, 10081.0, 8942.0, 8843.0, 6532.0, 5547.0, 3455.0, 2998.0,),
        "name": "Shannon, Ireland",
    },
    {
        "id": 8,
        "lat": -26.129658,
        "lon": 28.206078,
        "frequencies": (21949.0, 17922.0, 13321.0, 11321.0, 8834.0, 5529.0, 4681.0, 3016.0,),
        "name": "Johannesburg, South Africa",
    },
    {
        "id": 9,
        "lat": 71.25849,
        "lon": -156.577447,
        "frequencies": (
            21937.0,
            21928.0,
            17934.0,
            17919.0,
            11354.0,
            10093.0,
            10027.0,
            8936.0,
            8927.0,
            6646.0,
            5544.0,
            5538.0,
            5529.0,
            4687.0,
            4654.0,
            3497.0,
            3007.0,
            2992.0,
            2944.0,
        ),
        "name": "Barrow, Alaska",
    },
    {
        "id": 10,
        "lat": 35.032377,
        "lon": 126.238644,
        "frequencies": (21931.0, 17958.0, 13342.0, 10060.0, 8939.0, 6619.0, 5502.0, 2941.0,),
        "name": "Muan, South Korea",
    },
    {
        "id": 11,
        "lat": 9.084681,
        "lon": -79.373969,
        "frequencies": (17901.0, 13264.0, 10063.0, 8894.0, 6589.0, 5589.0),
        "name": "Albrook, Panama",
    },
    {
        "id": 13,
        "lat": -17.671199,
        "lon": -63.157088,
        "frequencies": (21997.0, 17916.0, 13315.0, 11318.0, 8957.0, 6628.0, 4660.0),
        "name": "Santa Cruz, Bolivia",
    },
    {
        "id": 14,
        "lat": 56.152603,
        "lon": 92.583337,
        "frequencies": (21990.0, 17912.0, 13321.0, 10087.0, 8886.0, 6596.0, 5622.0),
        "name": "Krasnoyarsk, Russia",
    },
    {
        "id": 15,
        "lat": 26.268773,
        "lon": 50.648978,
        "frequencies": (21982.0, 17967.0, 13312.0, 10030.0, 8885.0, 6646.0, 5544.0, 2986.0,),
        "name": "Al Muharraq, Bahrain",
    },
    {
        "id": 16,
        "lat": 13.488833,
        "lon": 144.828233,
        "frequencies": (21928.0, 17919.0, 13312.0, 11306.0, 8927.0, 6652.0, 5451.0),
        "name": "Agana, Guam",
    },
    {
        "id": 17,
        "lat": 27.960945,
        "lon": -15.405608,
        "frequencies": (21955.0, 17928.0, 13303.0, 11348.0, 8948.0, 6529.0),
        "name": "Canarias, Spain",
    },
]


def distance(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """
    Calculate the Haversine distance.

    Parameters
    ----------
    origin : tuple of float
        (lat, long)
    destination : tuple of float
        (lat, long)

    Returns
    -------
    distance_in_km : float

    Examples
    --------
    >>> origin = (48.1372, 11.5756)  # Munich
    >>> destination = (52.5186, 13.4083)  # Berlin
    >>> round(distance(origin, destination), 1)
    504.2
    """
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2)
    a += math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def guess(lat: float, lon: float) -> list[tuple[int, int, str]]:
    src = (lat, lon)

    distances: list = []
    for station in stations:
        result = (
            round(distance(src, (float(station["lat"]), float(station["lon"]))), 1),  # type: ignore[arg-type]
            station["id"],
            station["name"],
        )
        distances.append(result)

    distances.sort()
    return distances


if __name__ == "__main__":
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    distances = guess(lat, lon)
    print("This line can be used in settings.yaml (indent it properly):")
    print(f'ranked_stations: [{", ".join(str(d[1]) for d in distances)}]')
