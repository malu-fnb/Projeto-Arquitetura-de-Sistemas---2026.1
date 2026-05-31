import os
import time
import threading
from datetime import timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
)

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "iot-secret-dev-key-2024")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = False          
app.config["JWT_COOKIE_CSRF_PROTECT"] = False    

jwt = JWTManager(app)

USERS = {
    "admin": "admin123",
    "operador": "operador456",
}

iot_data_store: list[dict] = []
data_lock = threading.Lock()
MAX_RECORDS = 200


def dashboard_protected(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(locations=["cookies"])
        except Exception:
            return redirect(url_for("login_page"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Recebe credenciais e retorna JWT."""
    body = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400

    if USERS.get(username) != password:
        return jsonify({"error": "Credenciais inválidas"}), 401

    token = create_access_token(identity=username)

    response = jsonify({"message": "Login realizado com sucesso", "username": username})
    
    response.set_cookie(
        "access_token_cookie",
        value=token,
        httponly=True,
        samesite="Lax",
        max_age=7200,
    )
    return response, 200


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    response = jsonify({"message": "Logout realizado"})
    response.delete_cookie("access_token_cookie")
    return response, 200

@app.route("/dashboard")
@dashboard_protected
def dashboard():
    username = get_jwt_identity()
    return render_template("dashboard.html", username=username)

@app.route("/api/data", methods=["GET"])
@jwt_required(locations=["cookies"])
def get_data():
    """Retorna os últimos registros IoT para o dashboard."""
    with data_lock:
        records = list(reversed(iot_data_store[-MAX_RECORDS:]))
    return jsonify({"records": records, "total": len(records)}), 200


@app.route("/api/data/ingest", methods=["POST"])
@jwt_required(locations=["headers"])   
def ingest_data():
    """
    Endpoint chamado pelo middleware para enviar dados dos sensores.
    O middleware deve incluir: Authorization: Bearer <token>
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Payload JSON inválido"}), 400

    record = {
        "timestamp": body.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "device_id": body.get("device_id", "desconhecido"),
        "topic": body.get("topic", ""),
        "payload": body.get("payload", {}),
        "received_at": time.time(),
    }

    with data_lock:
        iot_data_store.append(record)
        if len(iot_data_store) > MAX_RECORDS:
            iot_data_store.pop(0)

    return jsonify({"message": "Dado recebido", "id": len(iot_data_store)}), 201


@app.route("/api/data/stats", methods=["GET"])
@jwt_required(locations=["cookies"])
def get_stats():
    """Estatísticas rápidas para os cards do dashboard."""
    with data_lock:
        total = len(iot_data_store)
        devices = list({r["device_id"] for r in iot_data_store})
        last_ts = iot_data_store[-1]["timestamp"] if iot_data_store else None

    return jsonify({
        "total_messages": total,
        "active_devices": len(devices),
        "devices": devices,
        "last_message": last_ts,
    }), 200


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "iot-dashboard"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)