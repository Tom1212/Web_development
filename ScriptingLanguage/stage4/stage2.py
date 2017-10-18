import sys, os, re
from forecast import forecast
from csv import DictReader
from datetime import datetime, timedelta
from time import mktime

_HMT = re.compile(r"^(\d+):(\d+)($|[ap]m$)")
_DAYS = {'mon':1, 'tue':2, 'wed':3, 'thu':4, 'fri':5, 'sat':6, 'sun':7,
        'tod':-1, 'now':-1, 'tom':-2, 'nex':-8}

def format(start, end, time):
    return "%s to %s %02d:%02d" % (_stop_ids[start].name, _stop_ids[end].name, time // 60, time % 60)

class Station(object):

    def __init__(self, name, location, id, aka):
        """
        Create a station object
        :param name: The name of the station
        :param location: The latitude and longitude of the station
        :param id: The station id
        :param aka: Also known as (appears in () after the station name)
        :return:
        """
        self.name = name
        self.location = location
        self.id = id
        self.aka = aka
        self.routes = []

    def __str__(self):
        """
        A string representation
        :return: "id: name (aka) @ location"
        """
        return "%s:%s (%s) @ %s" % (self.id, self.name, self.aka, self.location)

    def add_route(self, route):
        """
        Add a route to the list of routes for this station
        :param route: The route to add
        :return: None
        """
        self.routes.append(route)

    def travel(self, destination, time):
        """
        Find a route to destination starting after time
        :param destination: Where to?
        :param time: What time are we leaving?
        :return: Textual description, Time of Arrival
        """
        arrival = None
        best = None
        # Go through all the routes for this station
        for route in self.routes:
            # Get a route from this station to the destination
            directions = route.travel(self.id, destination.id, time)
            # We found a route
            if directions:
                # If it was the first one, or arrives earlier then update the best
                if not arrival or directions[0] < arrival:
                    arrival, best = directions

        # If we have an arrival time
        if arrival:
            # Format the arrival time
            arrival_time = "%02d:%02d" % (arrival // 60, arrival % 60)
            # Format the route
            details = [format(start, end, time) for start, end, time in best]
        else:
            # We don't have a route from here to there
            arrival_time = "--:--"
            details = ["No route found"]
        # Format for html
        return "<br/>\n".join(details), arrival_time

class Route(object):

    def __init__(self, stops):
        """
        A route consisting of a series of stops
        :param stops: A tuple of the stops
        :return: None
        """
        self.route = stops
        self.stops = set(stops)
        self.schedule = []

    def __str__(self):
        """
        Returns a string representation with origin and destination
        :return: "{origin} to {destination}"
        """
        origin = _stop_ids[self.route[0]]
        destination = _stop_ids[self.route[-1]]
        return "%s to %s" % (origin.name, destination.name)

    def add(self, schedule):
        """
        Add a schedule (the order of stops is fixed, so just need the times)
        :param schedule: A tuple of stop ids, times (in minutes after midnight)
        :return: None
        """
        self.schedule.append([time for stop, time in schedule])

    def travel(self, origin, destination, time):
        """
        Find a route from the origin to the destination leaving after the time
        :param origin: Where are we starting from?
        :param destination: Where are we heading to?
        :param time:
        :return:
        """
        # Is the destination in this route
        if destination in self.stops:
            # Find out whether it is before this stop or after it
            start = self.route.index(origin)
            end = self.route.index(destination)
            # If the destination is after the start then we have a valid route
            if start < end:
                # Now find the first one after the time
                for times in self.schedule:
                    # We assume that the first time that is greater than start time will get there first
                    if times[start] > time:
                        # Return the arrival time and the path taken
                        return times[end], [(origin, destination, times[start])]
        else:
            return

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
    # The name is the everything after the ( apart from the final )
    aka = stop[bracket+1:-1]
    # (temporarily closed) occurs before Railyway Station so we want the name before that
    index = min(stop.index(' ('), stop.index(' Railway Station'))
    # Remove Railway Station from the name
    name = stop[:index]
    station = Station(name, location, int(data['stop_id']), aka)
    return station


def skip_bom(f):
    """
    Skip the byte order mark (Unicode thing) if present
    :param f: The binary file that we've opened
    :return: The file is advanced past the byte order mark
    """
    if ord(f.read(1)) == 239:   # File starts with 3 bytes, the first being 239 for unicode
        f.read(2)
    else:
        # We need to go back to the beginning since we read a byte that we didn't need to
        f.seek(0)


def add_route(routes, schedule):
    """
    Add a schedule to the routes
    :param routes: Dictionary (the key is a tuple of the stop ids)
    :param schedule: A list of tuples with stop id, time (minutes after midnight)
    :return: None
    """
    # Get all the stops as a tuple
    stops = tuple([stop for stop, time in schedule])
    # Check if the route exists already
    route = routes.get(stops)
    if not route:
        # New route, so add to the dictionary
        route = Route(stops)
        routes[stops] = route
        # Add this route to all the stations contained in the route
        for stop in stops:
            _stop_ids[stop].add_route(route)
        #print route, schedule
    # Add the times to the route
    route.add(schedule)

def _load():
    """
    Load all the stops into a dictionary
    :return: A dictionary of stop name (lower case) -> location (latitude, longitude)
    """
    stops = {}
    stop_ids = {}

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

    # Use join so that code works irrespective of platform
    file = os.path.join("google_transit", "stops.txt")

    # lats and lons are for determing the minimum and maximum ranges
    # (for debug only to ensure map will cover area)
    lats = []
    lons = []
    # Open the file as a binary
    with open(file, "rb") as f:
        skip_bom(f)
        # Read each entry as a dictionary
        csv = DictReader(f)
        for data in csv:
            # Get the list of station names and the location
            station = _parse(data)
            # Add entries for each station
            stops[station.name] = station
            stop_ids[station.id] = station
            lat, lon = station.location
            # So the extent of the latitude and longitude can be calculated
            lats.append(lat)
            lons.append(lon)
    #print "%s,%s - %s,%s" % (max(lats), min(lons), min(lats), max(lons))

    # Go through all the stops and add the aka if it doesn't already exist
    # Since this is a different dictionary we don't have a problem with modifying
    # during iteration
    for id in stop_ids:
        station = stop_ids[id]
        # If there isn't a stop already with that name, add it using the aka name
        if station.aka not in stops:
            stops[station.aka] = station

    return stops, stop_ids, closest

# Load the station names and locations on the map
_stops, _stop_ids, _closest = _load()

def _load_routes():

    routes = {}

    # Use join so that code works irrespective of platform
    file = os.path.join("google_transit", "stop_times.txt")

    # Open the file as a binary
    with open(file, "rb") as f:
        # Skip byte order mark (if present)
        skip_bom(f)
        # Read each entry as a dictionary
        csv = DictReader(f)
        # Each trip has an id, so initialize with none
        trip = None
        # The stops and times of each stop
        schedule = []
        for data in csv:
            # Started a new route
            if trip != data['trip_id']:
                # Did we already have a route? If so lets add it
                if schedule:
                    # Add the route
                    add_route(routes, schedule)
                    # And start a new schedule
                    schedule = []
                # We are starting a new route
                trip = data['trip_id']

            # Get the hours minutes and seconds from the arrival time
            h, m, s = map(int, data['arrival_time'].split(':'))
            # Add the stop and time to the schedule
            schedule.append((int(data['stop_id']), h * 60 + m))

        # Add the last route
        add_route(routes, schedule)

    return routes

_routes = _load_routes()

def station_names():
    # Sort the stations into alphabetical order
    return sorted(_stops.keys())

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


def process(args):
    """
    Process the arguments and returns the weather
    :param args: The arguments are in the format returned by command line
    :return: The weather dictionary or None if error
    """
    # Command line needs 2 arguments at least to be valid, display help if it isn't
    if len(args) < 3:
        return help(args)
    # Get the matching station for the station name
    station = _stops.get(args[1])
    # If not a valid station we didn't find the station
    if not station:
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
    weather = forecast(station.location, unix)
    if weather:
        # Get the location that matches (to convert to canonical version
        weather['location'] = station.name
        weather['id'] = station.id
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
    :param query: The requested station id
    :return: The x, y posirion on the map
    """
    # Find the station referred to
    station = _stop_ids[int(query)]
    # Do we already have a location for it?
    if station.name in _closest:
        return _closest[station.name]

    # Let's find the closest position on the map

    # The closest station
    closest = None
    # The closest distance
    closest_distance = 9e9
    # Get the laritude and longitude
    lat, lon = station.location

    for name in _stops:
        # No point checking if we don't have an xy
        if name not in _closest:
            continue
        # Get the latitude and longitude of the station
        lat_diff, lon_diff = _stops[name].location
        lat_diff -= lat
        lon_diff -= lon
        # Find the distance (squared)
        distance = lat_diff * lat_diff + lon_diff * lon_diff
        # We only care about the closest, so we don't need to square root
        if distance < closest_distance:
            # Best so far
            closest_distance = distance
            closest = name

    # Cache the result
    _closest[station.name] = _closest[closest]

    # Return the x, y location on the map
    return _closest[closest]


def route(origin, destination, weather):
    """
    Find the earliest time you can get to destination from origin
    :param origin: The station id where the journey commences
    :param destination: The station id where the journey terminates
    :param weather:
    :return:
    """
    start = _stops[origin]
    end = _stops[destination]
    h,m = _parse_time(weather['time'])
    time = h * 60 + m
    weather['route'], weather['arrive'] = start.travel(end, time)
    weather['destination'] = end.id
    weather['destination_station'] = end.name
