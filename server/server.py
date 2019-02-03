from flask import Flask, jsonify
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/charitysearch"
mongo = PyMongo(app)


@app.route("/")
def home_page():
    organisations = mongo.db.organisation.find({}, limit=10)
    return jsonify({"organisations": [o for o in organisations]})
