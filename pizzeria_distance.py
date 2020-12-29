import requests
from elasticpath import get_entries
from geopy import distance


def get_nearest_pizzeria(current_pos):
    pizzerias = get_entries('pizzeria')
    for pizzeria in pizzerias:
        pizzeria['distance'] = distance.distance(
            (pizzeria['Longitude'], pizzeria['Latitude']),
            current_pos,
        ).km
    return min(pizzerias, key=lambda x: x['distance'])


def fetch_coordinates(apikey, place):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {"geocode": place, "apikey": apikey, "format": "json"}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    try:
        places_found = response.json()['response']['GeoObjectCollection']['featureMember']
        most_relevant = places_found[0]
        lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
        return lon, lat
    except IndexError:
        return None
