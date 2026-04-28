from flask import Flask, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

JSON_FILE = 'espacios.json'

@app.route('/api/espacios', methods=['GET'])
def get_espacios():
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            return jsonify(data)
    except FileNotFoundError:
        return jsonify({"espacios": []})

if __name__ == '__main__':
    print("Mock Vision Service running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
