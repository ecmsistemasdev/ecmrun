import os

from flask import Flask, render_template, redirect, request, jsonify, flash

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


port = int(os.environ.get("PORT", 5000))
if __name__ == "__main__":
    app.run(debug=True)

