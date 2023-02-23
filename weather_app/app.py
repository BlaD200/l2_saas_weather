import datetime as dt
import json
from os import getenv
from typing import Callable

import requests
from flask import Flask, jsonify, request


# create your API token, and set it up in Postman collection as part of the Body section
API_TOKEN = getenv('API_TOKEN')
# you can get API keys for free here - https://www.weatherapi.com/my/
WEATHER_API_KEY = getenv('WEATHER_API_KEY')

app = Flask(__name__)

url_base_url = 'http://api.weatherapi.com/v1'


def get_current_weather(q: str, lang: str = None):
    """
    Return the current weather for the given parameters.

    `q` could be the following:
        * Latitude and Longitude (Decimal degree) e.g: q=48.8567,2.3508
        * city name e.g.: q=Paris

    :param q: Query parameter based on which data is sent back.
    :param lang: Optional. Returns 'condition:text' field in API in the desired language.
    :return: The current weather for the given parameters.
    """
    url_endpoint = 'current.json'
    url = f"{url_base_url}/{url_endpoint}"

    params = {
        'key': WEATHER_API_KEY,
        'q': q
    }
    if lang:
        params['lang'] = lang

    response = requests.request('GET', url, params=params)
    return json.loads(response.text)


def get_weather_forecast(q: str, days: int, lang: str = None):
    """
    Return the forecast weather for the given parameters.

    `q` could be the following:
        * Latitude and Longitude (Decimal degree) e.g: q=48.8567,2.3508
        * city name e.g.: q=Paris

    `days` parameter value ranges between 1 and 14.
        If no days parameter is provided then only today's weather is returned

    :param q: Query parameter based on which data is sent back.
    :param days: Number of days of forecast required.
    :param lang: Optional. Returns 'condition:text' field in API in the desired language.
    :return: The weather forecast for the given parameters.
    """
    url_endpoint = 'forecast.json'
    url = f"{url_base_url}/{url_endpoint}"

    params = {
        'key': WEATHER_API_KEY,
        'q': q,
        'days': days
    }
    if lang:
        params['lang'] = lang

    response = requests.request('GET', url, params=params)
    return json.loads(response.text)


def get_weather_history(q: str, dt: str, end_dt: str = None, lang: str = None):
    """
    Return the history weather for the given parameters.

    `q` could be the following:
        * Latitude and Longitude (Decimal degree) e.g: q=48.8567,2.3508
        * city name e.g.: q=Paris

    `dt` and `end_dt` should be on or after 1st Jan, 2010 in yyyy-MM-dd format (i.e. dt=2010-01-01)
    `end_dt` should be greater than 'dt' parameter
        and difference should not be more than 30 days between the two dates.
    If `end_dt` isn't provided, the history weather will be returned only for `dt` date.

    :param q: Query parameter based on which data is sent back.
    :param dt: Start date, from which history weather is returned
    :param end_dt: End date, to which history weather is returned
    :param lang: Optional. Returns 'condition:text' field in API in the desired language.
    :return: The current weather for the given parameters.
    """
    url_endpoint = 'history.json'
    url = f"{url_base_url}/{url_endpoint}"

    params = {
        'key': WEATHER_API_KEY,
        'q': q,
        'dt': dt
    }
    if end_dt:
        params['end_dt'] = end_dt
    if lang:
        params['lang'] = lang

    response = requests.request('GET', url, params=params)
    return json.loads(response.text)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    @property
    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def authorize_and_validate_request(f: Callable):
    def wrapper():
        json_data = request.get_json()

        if json_data.get("token") is None:
            raise InvalidUsage("token is required", status_code=400)

        token = json_data.get("token")

        if token != API_TOKEN:
            raise InvalidUsage("wrong API token", status_code=403)

        if not json_data.get('weather'):
            raise InvalidUsage('weather params must be provided', status_code=400)

        return f()
    wrapper.__name__ = f.__name__
    return wrapper


def add_execution_time_params_to_response(f: Callable[[], dict]):
    def wrapper():
        start_dt = dt.datetime.now()
        response = f()
        end_dt = dt.datetime.now()
        execution_time_params = {
            "event_start_datetime": start_dt.isoformat(),
            "event_finished_datetime": end_dt.isoformat(),
            "event_duration": str(end_dt - start_dt),
        }
        response.update(execution_time_params)
        return response
    wrapper.__name__ = f.__name__
    return wrapper


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict)
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return '<p><h2>KMA L2: Python Saas. Weather</h2></p>'


@app.route(
    '/content/api/v1/integration/weather/current',
    methods=["POST"],
)
@authorize_and_validate_request
@add_execution_time_params_to_response
def current_weather_endpoint():
    json_data: dict = request.get_json()

    weather_params = json_data.get('weather')
    weather = get_current_weather(weather_params.get('q'), weather_params.get('lang'))

    result = {
        "weather": weather
    }

    return result


@app.route(
    '/content/api/v1/integration/weather/forecast',
    methods=["POST"],
)
@authorize_and_validate_request
@add_execution_time_params_to_response
def weather_forecast_endpoint():
    json_data: dict = request.get_json()

    weather_params = json_data.get('weather')
    weather = get_weather_forecast(
        weather_params.get('q'), weather_params.get('days'),
        weather_params.get('lang')
    )

    result = {
        "weather": weather
    }

    return result


@app.route(
    '/content/api/v1/integration/weather/history',
    methods=["POST"],
)
@authorize_and_validate_request
@add_execution_time_params_to_response
def weather_history_endpoint():
    json_data: dict = request.get_json()

    weather_params: dict = json_data.get('weather')
    weather = get_weather_history(
        weather_params.get('q'),
        weather_params.get('dt'), weather_params.get('end_dt'),
        weather_params.get('lang')
    )

    result = {
        "weather": weather
    }

    return result

