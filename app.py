from flask import Flask,jsonify
from flask_cors import CORS
from dotenv import load_dotenv


app = Flask(__name__)
CORS(app)
load_dotenv()

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Military API!"}),200



if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5050,debug=True)
