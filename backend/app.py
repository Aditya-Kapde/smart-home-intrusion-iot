from flask import Flask, request, jsonify
from detector import detect_intrusion
from storage import save_event

app = Flask(__name__)

# 🔐 Fake user database
USERS = {
    "admin": "1234",
    "doctor": "pass"
}

# 🔑 LOGIN API
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) == password:
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 401


# 🚨 DETECT API
@app.route("/detect", methods=["POST"])
def detect():
    data = request.json
    result = detect_intrusion(data)

    if result["intrusion"]:
        save_event(result)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)