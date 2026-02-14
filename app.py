from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import psycopg2
import json
from datetime import datetime

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__, template_folder="templates")
CORS(app)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_fallback_key")
DATABASE_URL = os.environ.get("DATABASE_URL")


# -----------------------------
# Database helpers
# -----------------------------
def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)


def ensure_table_exists():
    try:
        conn = get_db_connection()
        if not conn:
            return
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
    except Exception as e:
        print("Table creation error:", e)


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "EbudhouAI backend running with PostgreSQL"})


@app.route("/analyze", methods=["POST"])
def analyze():
    ensure_table_exists()

    data = request.get_json(force=True)

    symptoms = data.get("symptoms", "").lower()

    # OBD values now come from mobile app
    rpm = data.get("rpm")
    voltage = data.get("voltage")
    temperature = data.get("temperature")

    obd_data = {
        "rpm": rpm,
        "voltage": voltage,
        "temperature": temperature
    }

    # Default diagnosis
    diagnosis = "System Normal"
    confidence = "80%"
    next_action = "No action required"
    reason = "No abnormal data detected"

    # Simple rules
    if "battery" in symptoms or (voltage is not None and voltage < 11.5):
        diagnosis = "Weak or Failing Battery"
        confidence = "92%"
        next_action = "Check battery terminals or replace battery"
        reason = "Low voltage detected"

    elif "not starting" in symptoms or "starter" in symptoms:
        diagnosis = "Starter Motor or Ignition Issue"
        confidence = "88%"
        next_action = "Inspect starter motor"
        reason = "No-start symptoms detected"

    elif "overheat" in symptoms or (temperature is not None and temperature > 105):
        diagnosis = "Engine Overheating"
        confidence = "90%"
        next_action = "Check coolant system"
        reason = "High temperature detected"

    elif "stall" in symptoms or (rpm is not None and rpm < 500):
        diagnosis = "Engine Stalling Issue"
        confidence = "85%"
        next_action = "Check fuel system"
        reason = "Low RPM detected"

    # Save to DB
    try:
        conn = get_db_connection()
        if conn:
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
    except Exception as e:
        print("Insert error:", e)

    return jsonify({
        "diagnosis": diagnosis,
        "confidence": confidence,
        "reason": reason,
        "next_action": next_action,
        "obd": obd_data
    })


@app.route("/history")
def history():
    try:
        ensure_table_exists()
        conn = get_db_connection()
        if not conn:
            return jsonify([])

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
                "created_at": row[7].isoformat()
            })

        return jsonify(history_list)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5090))
    app.run(host="0.0.0.0", port=port)
