from json import loads, load
from pprint import pprint
from datetime import datetime
import urllib2

# The key read from the file forecastKey
_API_KEY = [None]
# The directions (converting from angle to compass direction)
_DIRECTIONS = "N NE E SE S SW W NW N".split()

# Read the key file
def _get_key():
    # Open the file
    with open("forecastKey") as f:
        # Read the key
        _API_KEY[0] = f.read().strip()
        return

# If not read the key already, read it
if not _API_KEY[0]:
    _get_key()

# Get the time as a string
def _get_time(unix):
    time = datetime.fromtimestamp(unix)
    return time.strftime('%H:%M')

# Fetch a file from internet
def _fetch(url):
    response = urllib2.urlopen(url)
    return load(response)

# Convert direction from angle to compass
def _direction(angle):
    # -22 to 23 is North, and so on
    return _DIRECTIONS[(angle + 22) // 45]

def forecast(location, time):
    """
    Get the forecast for a paricular location at a specific time
    :param location: THe (lat, lon) of location
    :param time: The unix timestamp
    :return: A dictionary of results (or None if there was a problem)
    """
    url = "https://api.forecast.io/forecast/{key}/{latitude},{longitude},{time}?units=si".format(
        key=_API_KEY[0], latitude=location[0], longitude=location[1], time=time
    )
    try:
        # To stop limits of API calls during development, use forecast.txt if present instead of fetching
        with open("forecast.txt") as f:
            json = loads(f.read())
    except:
        try:
            json = _fetch(url)
        except:
            return
    # Extract the pertinent data from the json
    details = {'temperature': json["currently"]["temperature"],
               'feelsLike': json["currently"]["apparentTemperature"],
               'summary': json["currently"]["summary"],
               'icon': json["currently"]["icon"],
               'windSpeed': json["currently"]["windSpeed"],
               # windBearing may not be defined if speed is 0
               'windBearing': _direction(json["currently"].get("windBearing", 0)),
               'low': json["daily"]["data"][0]["temperatureMin"],
               'high': json["daily"]["data"][0]["temperatureMax"],
               'dailySummary': json["daily"]["data"][0]["summary"],
               'sunrise': _get_time(json["daily"]["data"][0]["sunriseTime"]),
               'sunset':  _get_time(json["daily"]["data"][0]["sunsetTime"]),
               'time': _get_time(json["currently"]["time"]),
               }
    return details



