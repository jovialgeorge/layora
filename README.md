# Layora

Simple Flask app recommending number of layers and outfit guidance based on temperature and conditions.

Quick start

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open UI at http://127.0.0.1:5000/ and API docs at http://127.0.0.1:5000/docs

Notes
- Weather is fetched from Open-Meteo (no API key required) when latitude+longitude are provided.
- Logging to `app.log` is configured.
