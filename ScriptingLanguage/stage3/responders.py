#!/usr/bin/python

import stage2

def header():
	"""
	Build a header for the web page, with form for submitting data
    :return: The first part of the web page (<head><body><form></form>
	"""

	data = """<!DOCTYPE html><html lang="en"><head><title>Melbourne Stations</title>
	<!-- Latest compiled and minified CSS -->
	<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
	<!-- Optional theme -->
	<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
	<!-- Latest compiled and minified JavaScript -->
	<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script></head><body>
	<link rel="stylesheet" href="custom.css">
	<link rel="stylesheet" href="weather-icons.css">
    <link rel="stylesheet" href="weather-icons-wind.css">
    </head>
    <body>
	<div class="container">
	<h1>Welcome to Melbourne Weather</h1>
	<form action="http://127.0.0.1:34567/" method="POST" class="form-horizontal">
	<div class="form-group">
	<label for="stationName" class="col-sm-2 control-label">Station Name:</label>
	<div class="col-sm-10">
	<select name="stationName">"""
	for station in stage2.station_names():
		data += '<option>%s</option>' % station
	data += """</select>
	</div>
	</div>
	<div class="form-group">
	<label for="time" class="col-sm-2 control-label">Time:</label>
	<div class="col-sm-10">
	<input type="time" name="time" value="" size="" />
	</div>
	</div>
	<div class="form-group">"""
	for day in stage2.days():
		data += '<div class="col-sm-offset-2 col-sm-10"><div class="radio"><input type="radio" name="day" value="%s">%s</div></div>' % (day, day)
	data += """</div>
	<div class="col-sm-offset-2 col-sm-12">
	<input type="submit" value="Get the weather" class="btn btn-primary">
	</div>
	</form>
	<div class="row">&nbsp;</div>"""
	return data

def footer():
	"""
	Build the footer for the web page, with credits for fonts and Forecast.io
    :return: The end of the web page (<footer></body>)
	"""
	return """<footer><table width="100%"><th>Weather Icons by <a href="https://github.com/erikflowers/weather-icons">Erik Flowers</a></th>
	<th><a href="http://forecast.io/">Powered by Forecast</a></th></table></footer></div>
	</body></html>"""

# this is suitable for a GET - it has no parameters
def initialPage():
	"""
	Simple web page, just the form
	:return: The web page without any results
	"""
	return header() + footer()


def details(weather):
	"""
	Content for the weather part of displau
    :param weather: Dictionary with details of the weather
	:return: The web page without any results
	"""
	return """<table class="forecast bg-success"><tr><th colspan="2" class="text-center lead">Weather for {location} at {time}<th></tr>
	<tr><td>Temp: {temperature}<i class="wi wi-celsius"></i> Feels Like: {feelsLike}<i class="wi wi-celsius"></i></td><td rowspan="9"><img src="map.gif?{latitude},{longitude}" width="600" height="371"/><td></tr>
	<tr><td>Low: {low}<i class="wi wi-celsius"></i> High: {high}<i class="wi wi-celsius"></i></td></tr>
	<tr><td>Sunrise <i class="wi wi-sunrise"></i>: {sunrise} Sunset <i class="wi wi-sunset"></i>: {sunset}</td></tr>
	<tr><td>Wind: {windSpeed} kph from {windBearing} <i class="wi wi-wind.towards-{windDirection}-deg"></i></td></tr>
	<tr><td>Summary <i class="wi wi-{icon}"></i>: {summary}</td></tr>
	<tr><td></td></tr>
	<tr><td></td></tr>
	<tr><td></td></tr>
	<tr><td></td></tr>
	<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
	</table>""".format(**weather)

# this is suitable for a POST - it has a single parameter which is
# a dictionary of values from the web page form.

def respondToSubmit(formData):
	"""
	Build the web page after the user has clicked submit
	:param formData: The data entered by the user
	:return: A web page with the weather requested
	"""
	data = header()
	# The command line expected
	args = ["web", formData["stationName"], formData.get("day", "Now"), formData["time"]]

	# If no time was specified
	if not args[-1]:
		# Remove the last argument
		args = args[:-1]
		# If today is specified, then assume current time if no time is mentioned
		if args[-1] == "Today":
			args[-1] = "Now"
	# Process all the command line
	weather = stage2.process(args)
	if "error" not in weather:
		# Fill in the details from the forecast
		data += '<p class="bg-success lead">%s</p><div class="row">&nbsp;</div>' % details(weather)
	else:
		# Fill in error message
		data += '<p class="bg-danger lead">%s</p>' % weather["error"]
	# Complete the web page
	data += footer()

	return data