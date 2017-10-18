import sys, os, re
from forecast import forecast
from csv import DictReader
from datetime import datetime, timedelta
from time import mktime

_HMT = re.compile(r"^(\d+):(\d+)($|[ap]m$)")
_DAYS = {'mon':1, 'tue':2, 'wed':3, 'thu':4, 'fri':5, 'sat':6, 'sun':7,
        'tod':-1, 'now':-1, 'tom':-2, 'nex':-8}

def _parse(data):
    """
    Parse an entry from the csv file "stops.txt"
    :param data:
    :return:
    """
    # The location is a tuple of latitude and longitude
    location = float(data['stop_lat']), float(data['stop_lon'])

    # The name of the stop
    stop = data['stop_name']

    # The format is Station name (AKA), so find the last (
    bracket = stop.rindex('(')
    stations = set()
    # The name is the everything after the ( apart from the final )
    name = stop[bracket+1:-1]
    # Add the station
    stations.add(name)
    # And the lower case version for consistent access
    stations.add(name.lower())
    # Remove Railway Station if it exists
    if ' Railway Station' in stop:
        index = stop.index(' Railway Station')
        # Remove Railway Station from the name
        name = stop[:index]
        if '(' not in name:     # Avoid (temporarily closed) entries
            stations.add(name)
            # Add the lower case version
            stations.add(name.lower())
    return stations, location

def _load():
    """
    Load all the stops into a dictionary
    :return: A dictionary of stop name (lower case) -> location (latitude, longitude)
    """
    stops = {}
    # Use join so that code works irrespective of platform
    file = os.path.join("google_transit", "stops.txt")

    # lats and lons are for determing the minimum and maximum ranges
    # (for debug only to ensure map will cover area)
    lats = []
    lons = []
    # Open the file as a binary
    with open(file, "rb") as f:
        # Read each entry as a dictionary
        csv = DictReader(f)
        for data in csv:
            # Get the list of station names and the location
            stations, location = _parse(data)
            # Add entries for each station
            for station in stations:
                stops[station] = location
                lat, lon = location
                # So the extent of the latitude and longitude can be calculated
                lats.append(lat)
                lons.append(lon)
    #print "%s,%s - %s,%s" % (max(lats), min(lons), min(lats), max(lons))

    # Find the closest stations
    closest = {}
    with open("closest.txt") as f:
        for line in f:
            # If comma is present then read the line
            if "," in line:
                # Get the station, x, y from file
                station, x, y = line.strip().split(",")
                # Store in dictionary
                closest[station] = int(x), int(y)

    return stops, closest

# Load the station names and locations on the map
_stops, _closest = _load()

def station_names():
    # Get the list of the stations (lower case versions are assumed to be aliases)
    stations = [name for name in _stops if name != name.lower()]
    # Sort the stations into alphabetical order
    stations.sort()
    return stations

def days():
    """
    Get the list of days (from the current day, use Today, Tomorrow, then day names)
    :return:
    """
    date = datetime.now()
    first = date.weekday()
    dow = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
    # Fill in the days of the week from the current day
    values = [dow[(first + n) % 7] for n in range(7)]
    # Replace the first 2 values
    values[0] = "Today"
    values[1] = "Tomorrow"
    return values

def help(args, error=None):
    """
    Display help for the command line
    :param args: The command line (to ge the name of the program)
    :return: Dictionary with error
    """
    return {"error": error}

def _parse_time(time):
    """
    Converts time from hh:mm{am|pm} format into h, m
    :param time: time as string
    :return: h, m OR None if unable to parse
    """
    try:
        if time.lower() == "now":
            current = datetime.now()
            return current.hour, current.minute
        # Get the time
        time_match = _HMT.match(time.lower())
        # Time does not match the schema
        if not time_match:
            return
        else:
            # Get the hours
            h = int(time_match.group(1))
            # And the minutes
            m = int(time_match.group(2))
            # Am if AM is present
            am = time_match.group(3).startswith("a")
            # Pm if PM is present
            pm = time_match.group(3).startswith("p")
            # 12 AM is 0 in 24 hour format
            if am and h == 12:
                h = 0
            # 1pm - 11pm = 13:00 - 23:00
            if pm and h != 12:
                h += 12
            if h < 0 or h > 23 or m < 0 or m > 59:
                return
            return h, m
    except:
        return


def _parse_date(date_list):
    """
    Parse a relative date
    :param date_list: {n day{s} from} day_specifier
    :return: The actual date (relative to today)
    """
    # Get the current date
    date = datetime.now()
    # Add this many days to get the actual date
    add = 0
    # If the first argument is an integer then use that as an offset for the date
    if date_list[0].isdigit():
        add = int(date_list[0])
        # Skip "day{s} from"
        date_list = date_list[3:]

    # Get the current day of the week
    today = date.isoweekday()     # Mon = 1, Tue = 2, Sun = 7
    # Get the day (- numbers are absolute, + numbers are based on day of the week)
    day = _DAYS.get(date_list[0].lower()[:3], 0)

    # If 0 then we don't recognize the word
    if not day:
        return

    # If day < 0 then relative to current day
    if day < 0:
        add += ~day           # ~n is (-n) + 1, so today = 0, tomorrow = 1, next week = 7
    # Relative to a specific day
    else:
        # If today is Friday, should Friday mean next Friday or today?
        # If you want it to mean today, then change today < day to today <= day
        if today < day:
            # Day is later in the same week
            add += day - today
        else:
            # Day is in the next week
            add += 7 + day - today

    # Modify the date
    date = date + timedelta(days=add)
    return date


def _find_location(location):
    """
    Find the name of the location
    :param location: Get the location
    :return: The canonical name of the location
    """
    for key in _stops:
        if key != key.lower() and location == _stops[key]:
            return key
    return "requested location"


def process(args):
    """
    Process the arguments and returns the weather
    :param args: The arguments are in the format returned by command line
    :return: The weather dictionary or None if error
    """
    # Command line needs 2 arguments at least to be valid, display help if it isn't
    if len(args) < 3:
        return help(args)
    # Get the matching location for the station
    location = _stops.get(args[1].lower())
    # If not a valid location we didn't find the station
    if not location:
        return help(args, "Unable to find a station called %s" % args[1])
    # Get the time as hours and minutes
    time = _parse_time(args[-1])
    # If not a valid time, display help and error message
    if not time:
        return help(args, "%s is not a valid time" % args[-1])
    if len(args) > 3:
        date = _parse_date(args[2:-1])
        if not date:
            return help(args, "I don't understand %s" % " ".join(args[2:-1]))
        # print args[2:-1], date.strftime("%A"), date.day, date.month, date.year
    else:
        date = datetime.now()
    # Combine the date and time to get the datetime
    date = date.replace(hour=time[0], minute=time[1], second=0)
    # Get the unix timecode
    unix = int(mktime(date.timetuple()))
    # Get the weather for location and time
    weather = forecast(location, unix)
    if weather:
        # Get the location that matches (to convert to canonical version
        weather['location'] = _find_location(location)
    return weather

def main(args):
    weather = process(args)
    if weather:
        print u"""
Weather for {location} at {time}
Temp: {temperature}\N{DEGREE SIGN}C Feels Like: {feelsLike}\N{DEGREE SIGN}C
Low: {low}\N{DEGREE SIGN}C High: {high}\N{DEGREE SIGN}C
Sunrise: {sunrise} Sunset: {sunset}
Wind: {windSpeed} kph from {windBearing}
Summary: {summary}""".format(**weather)
    else:
        print "Problem fetching the weather"

def test(str):
    """
    Convert the string in the same way command line arguments are handled
    :param str: The command line as a string
    :return: Acts as though main was called with a command line
    """
    # The name of the script is the first parameter, then each word as a list entry
    args = [sys.argv[0]] + str.split()
    # Quoted string should be joined (and the quotes removed)
    if args[1][0] == '"':
        args = [args[0]] + [args[1][1:] + " " + args[2][:-1]] + args[3:]
    main(args)

if __name__ == "__main__":
    # test('feltham 17:20')             # Invalid station
    # test('eltham 13:20pm')            # Invalid time
    # test('eltham now')                # Does not match the syntax but reads better than eltham now 5:20pm
    # test('eltham yesterday 5:20pm')   # Invalid date specifier
    # test('eltham today 5:20pm')       # Check relative dates
    # test('eltham tomorrow 5:20pm')
    # test('eltham monday 5:20pm')
    # test('eltham thursday 5:20pm')
    # test('eltham friday 5:20pm')
    # test('eltham saturday 5:20pm')
    # test('eltham sunday 5:20pm')
    #test('eltham 5:20pm')
    #test('"melbourne central" wednesday 5:20pm')
    #test('Hallam 2 days from tomorrow 5:20pm')
    #test('Hallam 2 days from now 5:20pm')
    main(sys.argv)


def xy(query):
    """
    Get the closest station on the map
    :param query: The requested latitude, longitude
    :return: The x, y posirion on the map
    """
    # Get the laritude and longitude
    lat_lon = query.split(",")
    # The closest station
    closest = None
    # The closest distance
    closest_distance = 9e9
    # Get the float value
    lat, lon = map(float, lat_lon)

    for location in _stops:
        # No point checking if we don't have an xy
        if location not in _closest:
            continue
        # Get the latitude and longitude of the station
        lat_diff, lon_diff = _stops[location]
        lat_diff -= lat
        lon_diff -= lon
        # Find the distance (squared)
        distance = lat_diff * lat_diff + lon_diff * lon_diff
        # We only care about the closest, so we don't need to square root
        if distance < closest_distance:
            # Best so far
            closest_distance = distance
            closest = location

    # Return the x, y location on the map
    return _closest[closest]