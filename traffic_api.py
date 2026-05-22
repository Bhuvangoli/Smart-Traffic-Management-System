import requests

API_KEY = "dtXepsDULX915FETPCu9NsA25FCaB34S"

def get_traffic(lat, lon):
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

    params = {
        "key": API_KEY,
        "point": f"{lat},{lon}"
    }

    response = requests.get(url, params=params)
    
    return response.json()