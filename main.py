from flask import Flask, request, render_template
import json
import requests
import redis

app = Flask(__name__)

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def get_weather_data(datasize):
    with open('weather_api_key.json', "r") as file:
        api_key = json.load(file)
    location = 'UK'
    base_url = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline'
    url = f"{base_url}/{location}?unitGroup=metric&key={api_key}"

    response = requests.get(url)
    data = response.json()

    if datasize == 'all':
        return data
    elif datasize == 'small':
        return data['resolvedAddress'], data['currentConditions']['temp'], data['currentConditions']['conditions']
    elif datasize == 'day':
        return data['days'][0]

def get_specific_data(location):
    with open('weather_api_key.json', "r") as file:
        api_key = json.load(file)
    base_url = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline'
    url = f"{base_url}/{location}?unitGroup=metric&key={api_key}"
    response = requests.get(url)
    try:
        data = response.json()
        return data['currentConditions']
    except ValueError:  # includes simplejson.decoder.JSONDecodeError
        print('Decoding JSON has failed')

@app.route('/home', methods=['GET', 'POST'])
def home_side():

    result = None
    source = None
    error = None

    if request.method == 'POST':
        user_input = request.form.get('user_input').strip()
        if not user_input:
            error = 'Input cannot be empty.'
            return render_template('home.html', error=error)
        else:
            cache_key = f"weather:{user_input.lower()}"

            cached_data = redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                source = 'Cache'
            else:
                with open('weather_api_key.json', "r") as file:
                    api_key = json.load(file)
                base_url = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline'
                url = f"{base_url}/{user_input}?unitGroup=metric&key={api_key}"
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    redis_client.setex(cache_key, 3600, json.dumps(data))# Store data in cache with expiration (e.g., 1 hour)
                    source = 'API'
                except requests.exceptions.RequestException as e:
                    error = 'An error occurred while fetching data.'
                    print(f"Error: {e}")
                    return render_template('home.html', error=error)
            try:
                temperature = data['currentConditions']['temp']
                conditions = data['currentConditions']['conditions']
                result = f"Current temperature in {user_input} is {temperature}°C with {conditions}."
            except KeyError:
                error = 'Could not retrieve weather data.'
                return render_template('home.html', error=error)

    return render_template('home.html', result=result, source=source, error=error)

if __name__ == "__main__":
    app.run(debug=True)