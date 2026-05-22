import requests

def get_coordinates(place):
    url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        "q": place,
        "format": "json"
    }

    headers = {
        "User-Agent": "SmartTrafficManagementApp/1.0"
    }

    res = requests.get(url, params=params, headers=headers).json()

    if res:
        return float(res[0]["lat"]), float(res[0]["lon"])

    return None, None