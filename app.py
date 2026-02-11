from flask import Flask, request, jsonify, render_template
import socket
import os

app = Flask(__name__)

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
        connection = obd.OBD()  # auto connect
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


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    symptoms = data.get("symptoms", "").lower()

    obd_data = get_obd_data()

    diagnosis = "System Normal"
    confidence = "80%"
    next_action = "No action required"
    reason = "No abnormal data detected"

    if "battery" in symptoms or (obd_data.get("voltage") and obd_data["voltage"] < 11.5):
        diagnosis = "Weak or Failing Battery"
        confidence = "92%"
        next_action = "Check terminals or replace battery"
        reason = "Low voltage or battery-related symptoms"

    elif "not starting" in symptoms or "click" in symptoms:
        diagnosis = "Starter Motor Issue"
        confidence = "86%"
        next_action = "Check starter motor and ignition switch"
        reason = "No-start condition with clicking sound"

    elif "overheat" in symptoms or (obd_data.get("temperature") and obd_data["temperature"] > 105):
        diagnosis = "Engine Overheating"
        confidence = "90%"
        next_action = "Stop engine and check coolant"
        reason = "High engine temperature detected"

    return jsonify({
        "diagnosis": diagnosis,
        "confidence": confidence,
        "reason": reason,
        "next_action": next_action,
        "obd": obd_data
    })


# -----------------------------
# LOCAL DEV ONLY
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5090))
    app.run(host="0.0.0.0", port=port)
