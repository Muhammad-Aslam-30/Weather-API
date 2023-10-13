import requests
import logging
import argparse
from tabulate import tabulate
from dataclasses import dataclass

SPOTS_LAT_LONG = {
    #'Altenteil Fehmarn': (54.4667, 11.1333),
    'Ammersee': (48.0011, 11.1333),
    'Bodensee': (47.6667, 9.1667),
    'Chiemsee': (47.8667, 12.35),
    'Comer See': (46.0167, 9.2667),
    'Gardasee': (45.6667, 10.7),
    'Silvaplana See': (46.4411, 9.7667),
    'Starnberger See': (47.9667, 11.35),
    'Tegernsee': (47.7, 11.7333),
    'Walchensee': (47.6, 11.3667),
}

weather_code_ranges = {
    (0, 0): "Sunny",
    (1, 10): "Mainly Clear",
    (11, 30): "Partly Cloudy",
    (31, 70): "Mostly Cloudy",
    (71, 75): "Foggy",
    (76, 80): "Light Rain",
    (81, 85): "Moderate Rain",
    (86, 90): "Heavy Rain",
    (91, 95): "Rain with Thunder",
    (96, 96): "Thunderstorm with Slight Hail",
    (97, 97): "Thunderstorm with Hail",
    (98, 98): "Sleet Showers",
    (99, 99): "Thunderstorm with Heavy Hail",
}

@dataclass
class Coordinates:
    latitude: float
    longitude: float

class WeatherAPI:

    def __init__(self, api_url) -> None:
            self.api_url = api_url
            self.max_windspeed = 0
            self.windspeed_based_locations = []
            self.result = []

    def _make_api_request(self, coordinates, offset_hours, location):
        try:
            response = requests.get(
                f"https://{self.api_url}/v1/forecast",
                params={
                    "latitude": coordinates.latitude,
                    "longitude": coordinates.longitude,
                    "hourly": "temperature_2m,weathercode,windspeed_10m",
                }
            )

            response.raise_for_status()

            parsed_data = response.json()
            hourly = parsed_data['hourly']
            windspeed = hourly['windspeed_10m'][offset_hours]
            weathercode = hourly['weathercode'][offset_hours]
            temperature = hourly['temperature_2m'][offset_hours]

            return windspeed, weathercode, temperature
        
        except requests.RequestException as e:
            #logging.error(f"Error while making API request for location: {location}")
            return None

    def get_best_location(self, offset_hours):
        for location, coordinates_data in SPOTS_LAT_LONG.items():
            coordinates = Coordinates(*coordinates_data)
            # Requesting API to get weathercode, windspeed and temperature
            wind_weather = self._make_api_request(coordinates, offset_hours, location)
            if wind_weather is not None:
                windspeed, weathercode, temperature = wind_weather
                min_windspeed_range = self.max_windspeed - 5
                max_windspeed_range = self.max_windspeed + 5
                if windspeed >= max_windspeed_range:
                    self.max_windspeed = windspeed
                    self.windspeed_based_locations = [(weathercode, location, windspeed, temperature)]
                elif windspeed >= min_windspeed_range and windspeed <= max_windspeed_range:
                    self.windspeed_based_locations.append((weathercode, location, windspeed, temperature))

        if not self.windspeed_based_locations:
            logging.warning("No suitable location found")
            return "No location has been found"

        # "result" list contains locations from the list "windspeed_based_locations" based on least weather code  
        self.result = []
        self.windspeed_based_locations.sort()
        min_weathercode = self.windspeed_based_locations[0][0]
        self.result.append((self.windspeed_based_locations[0][2], self.windspeed_based_locations[0][1], self.windspeed_based_locations[0][0], self.windspeed_based_locations[0][3]))
        for wcode_loc in self.windspeed_based_locations[1:]:
            if wcode_loc[0] < min_weathercode:
                self.result = []    
                self.result.append((wcode_loc[2], wcode_loc[1], wcode_loc[0], wcode_loc[3]))
            elif wcode_loc[0] == min_weathercode:
                self.result.append((wcode_loc[2], wcode_loc[1], wcode_loc[0], wcode_loc[3]))
        #self.result = sorted(self.result)
        return sorted(self.result)
    
class DisplayTable:

    def create_table(self, result):
        # Prepare data for the table
        table_data = []
        for i in range(len(result)-1, -1, -1):
            entry = result[i]
            windspeed, location, weathercode, temperature = entry
            # Determine weather description based on weather code
            for code_range, description in weather_code_ranges.items():
                if code_range[0] <= weathercode <= code_range[1]:
                    weather_description = description
                    break
            else:
                weather_description = "Unknown"
            table_data.append([location, windspeed, weather_description, temperature])

        # Create and return the table as a string
        headers = ["Location", "Wind (km/h)", "Weather", "Air (℃)"]
        table = tabulate(table_data, headers, tablefmt="grid")
        return table

def main():
    parser = argparse.ArgumentParser(description="Find the best location based on wind speed and weather code")
    parser.add_argument("offset_hours", type=int, help="Offset hours for the API request")
    args = parser.parse_args()
    # To Request API
    api_url = "api.open-meteo.com" 
    weather_call = WeatherAPI(api_url)
    result = weather_call.get_best_location(args.offset_hours)
    # To create table output in the CLI
    table_formatter = DisplayTable()
    table = table_formatter.create_table(result)
    print(table)
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()