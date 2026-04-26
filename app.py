from flask import Flask, render_template
from flask_restx import Api, Resource, fields
import requests
import logging
import sys
from utils.recommender import recommend_outfit

app = Flask(__name__, template_folder='templates', static_folder='static')
api = Api(app, version='1.0', title='Fit Recommender API', doc='/docs', prefix='/api')

# Logging setup
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

ns = api.namespace('outfits', path='/', description='Recommendation operations')

location_model = api.model('Location', {
    'latitude': fields.Float(required=False, description='Latitude'),
    'longitude': fields.Float(required=False, description='Longitude'),
})

recommend_model = api.model('RecommendRequest', {
    'location': fields.Nested(location_model, required=False),
    'manual_temp_c': fields.Float(required=False, description='Manual temperature in Celsius'),
    'manual_condition': fields.String(required=False, description='Manual short condition (clear,rain,snow,cloudy)'),
    'occasion': fields.String(required=False, description='Occasion e.g. Casual, Formal, Sport'),
    'sex': fields.String(required=False, description='Sex: male/female/other'),
    'age': fields.Integer(required=False, description='Age in years')
})


def fetch_weather_from_open_meteo(lat, lon):
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {'latitude': lat, 'longitude': lon, 'current_weather': True}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        cw = data.get('current_weather') or {}
        return {
            'temp_c': cw.get('temperature'),
            'weather_code': cw.get('weathercode')
        }
    except Exception as e:
        app.logger.warning('Weather fetch failed: %s', e)
        return None


@ns.route('/recommend')
class Recommend(Resource):
    @ns.expect(recommend_model)
    def post(self):
        payload = api.payload or {}
        app.logger.info('Received recommend request: %s', payload)

        temp = None
        weather_code = None

        loc = payload.get('location')
        if loc and loc.get('latitude') is not None and loc.get('longitude') is not None:
            w = fetch_weather_from_open_meteo(loc['latitude'], loc['longitude'])
            if w:
                temp = w.get('temp_c')
                weather_code = w.get('weather_code')

        # manual override
        if temp is None and payload.get('manual_temp_c') is not None:
            temp = payload.get('manual_temp_c')
        if weather_code is None and payload.get('manual_condition'):
            cond = payload.get('manual_condition').lower()
            mapping = {'clear': 0, 'cloudy': 3, 'rain': 61, 'snow': 71}
            weather_code = mapping.get(cond, 3)

        if temp is None:
            return {'error': 'No temperature available. Provide location or manual_temp_c.'}, 400

        occasion = payload.get('occasion', 'Casual')
        sex = payload.get('sex', 'other')
        age = payload.get('age', None)

        rec = recommend_outfit(temp_c=temp, weather_code=weather_code, sex=sex, age=age, occasion=occasion)
        app.logger.info('Recommendation generated: %s', rec)
        return rec


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('landing.html')


def log_registered_routes():
    app.logger.info('Registered routes:')
    for rule in app.url_map.iter_rules():
        app.logger.info(str(rule))


if __name__ == '__main__':
    # Print registered routes for debugging and call logger
    print('Registered routes:')
    for rule in app.url_map.iter_rules():
        print(rule)
    # also write to app logger
    log_registered_routes()
    # Disable the reloader so the printed routes appear in the serving process
    app.run(debug=True, use_reloader=False)
