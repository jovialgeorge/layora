from flask import Flask, render_template, request, jsonify
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
import requests
import logging
import sys
import os
import smtplib
from email.mime.text import MIMEText
from utils.recommender import recommend_outfit

load_dotenv()

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


MAIL_TO   = 'jovialdevit@gmail.com'
MAIL_FROM = os.environ.get('MAIL_USER', '')
MAIL_PASS = os.environ.get('MAIL_PASS', '')


def _send_mail(subject, body):
    if not MAIL_FROM or not MAIL_PASS:
        app.logger.warning('Mail not configured (set MAIL_USER and MAIL_PASS env vars)')
        return False
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From']    = MAIL_FROM
    msg['To']      = MAIL_TO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=8) as s:
        s.login(MAIL_FROM, MAIL_PASS)
        s.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
    return True


@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        data    = request.get_json(silent=True) or {}
        rating  = data.get('rating')
        message = str(data.get('message', '')).strip()[:2000]
        name    = str(data.get('name', '')).strip()[:100]

        if not message and rating is None:
            return jsonify({'error': 'Nothing to send'}), 400

        try:
            rating_int = int(rating) if rating is not None else None
        except (ValueError, TypeError):
            rating_int = None

        stars  = ('★' * rating_int + '☆' * (5 - rating_int)) if rating_int else 'Not rated'
        sender = name or 'Anonymous'
        body   = f"Layora Feedback\n{'─'*30}\nFrom:    {sender}\nRating:  {stars} ({rating_int}/5)\n\n{message or '(no message)'}"

        try:
            sent = _send_mail(f'[Layora Feedback] {stars} from {sender}', body)
        except Exception as e:
            app.logger.error('Feedback mail error: %s', e)
            return jsonify({'error': 'Could not send email. Check MAIL_USER / MAIL_PASS.'}), 500

        if not sent:
            app.logger.info('Feedback (mail not configured): %s', body)

        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error('Unexpected feedback error: %s', e)
        return jsonify({'error': 'Unexpected server error.'}), 500


@app.errorhandler(404)
def not_found(_):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({'error': 'Internal server error'}), 500


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
