from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import socket
import os
import psycopg2
import json
from datetime import datetime

# -----------------------------
# CREATE FLASK APP
# -----------------------------
app = Flask(__name__, template_folder="templates")
CORS(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_fallback_key")

DATABASE_URL = os.environ.get("DATABASE_URL")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnosis_history (
            id SERIAL PRIMARY KEY,
            symptoms TEXT,
            diagnosis TEXT,
            confidence TEXT,
            reason TEXT,
            next_action TEXT,
            obd_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# Initialize table on startup
init_db()


# -----------------------------
# OBD LIB CHECK
# -----------------------------
try:
    import obd
    OBD_LIB_AVAILABLE = True
except Exception:
    OBD_LIB_AVAILABLE = False


# -----------------------------
# NETWORK CHECK
# -----------------------------
def wifi_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


# -----------------------------
# REAL OBD (BLUETOOTH)
# -----------------------------
def get_real_obd_data():
    if not OBD_LIB_AVAILABLE:
        return None

    try:
        connection = obd.OBD()
        if not connection.is_connected():
            return None

        rpm = connection.query(obd.commands.RPM)
        voltage = connection.query(obd.commands.CONTROL_MODULE_VOLTAGE)
        temp = connection.query(obd.commands.COOLANT_TEMP)

        return {
            "source": "BLUETOOTH",
            "rpm": rpm.value.magnitude if rpm.value else None,
            "voltage": voltage.value.magnitude if voltage.value else None,
            "temperature": temp.value.magnitude if temp.value else None
        }
    except Exception:
        return None


# -----------------------------
# FINAL DATA SELECTOR
# -----------------------------
def get_obd_data():
    real = get_real_obd_data()
    if real:
        return real

    if wifi_available():
        return {
            "source": "WIFI",
            "voltage": 13.6,
            "rpm": 800,
            "temperature": 92
        }

    return {
        "source": "SIMULATED",
        "voltage": 12.1,
        "rpm": 780,
        "temperature": 94
    }


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "EbudhouAI backend running with PostgreSQL"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    symptoms = data.get("symptoms", "").lower()

    obd_data = get_obd_data()

    diagnosis = "System Normal"
    confidence = "80%"
    next_action = "No action required"
    reason = "No abnormal data detected"

    if (
        "battery" in symptoms
        or "low voltage" in symptoms
        or (obd_data.get("voltage") and obd_data["voltage"] < 11.5)
    ):
        diagnosis = "Weak or Failing Battery"
        confidence = "92%"
        next_action = "Check battery terminals or replace battery"
        reason = "Low voltage detected or battery-related symptoms"

    elif (
        "not starting" in symptoms
        or "starter" in symptoms
        or "not working" in symptoms
        or "engine not" in symptoms
        or "click" in symptoms
        or "crank" in symptoms
    ):
        diagnosis = "Starter Motor or Ignition Issue"
        confidence = "88%"
        next_action = "Inspect starter motor, ignition switch, and wiring"
        reason = "No-start or starter-related symptoms detected"

    elif (
        "overheat" in symptoms
        or "too hot" in symptoms
        or (obd_data.get("temperature") and obd_data["temperature"] > 105)
    ):
        diagnosis = "Engine Overheating"
        confidence = "90%"
        next_action = "Stop engine immediately and check coolant system"
        reason = "High engine temperature detected"

    elif (
        "stall" in symptoms
        or "shut off" in symptoms
        or (obd_data.get("rpm") and obd_data["rpm"] < 500)
    ):
        diagnosis = "Engine Stalling Issue"
        confidence = "85%"
        next_action = "Check fuel system and idle control"
        reason = "Low RPM or stalling symptoms detected"

    # -----------------------------
    # SAVE TO DATABASE
    # -----------------------------
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diagnosis_history
        (symptoms, diagnosis, confidence, reason, next_action, obd_data, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """, (
        symptoms,
        diagnosis,
        confidence,
        reason,
        next_action,
        json.dumps(obd_data),
        datetime.utcnow()
    ))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "diagnosis": diagnosis,
        "confidence": confidence,
        "reason": reason,
        "next_action": next_action,
        "obd": obd_data
    })


@app.route("/history")
def history():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM diagnosis_history ORDER BY created_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    history_list = []
    for row in rows:
        history_list.append({
            "id": row[0],
            "symptoms": row[1],
            "diagnosis": row[2],
            "confidence": row[3],
            "reason": row[4],
            "next_action": row[5],
            "obd": row[6],
            "created_at": row[7]
        })

    return jsonify(history_list)


# -----------------------------
# LOCAL DEV ONLY
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5090))
    app.run(host="0.0.0.0", port=port)
