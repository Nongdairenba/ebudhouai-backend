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
# DIAGNOSIS LOGIC
# -----------------------------
def diagnose_vehicle(symptoms: str, obd_data: dict):
    """
    Returns diagnosis dict:
    - diagnosis
    - confidence
    - next_action
    - reason
    """
    symptoms = symptoms.lower()
    voltage = obd_data.get("voltage", 12.5)
    rpm = obd_data.get("rpm", 800)
    temp = obd_data.get("temperature", 90)

    # Default values
    diagnosis = "System Normal"
    confidence = "80%"
    next_action = "No action required"
    reason = "No abnormal data detected"

    # Battery Issues
    if "battery" in symptoms or "low voltage" in symptoms or voltage < 11.5:
        diagnosis = "Weak or Failing Battery"
        confidence = "92%"
        next_action = "Check battery terminals or replace battery"
        reason = "Low voltage detected or battery-related symptoms"

    # Starter / No-Start Issues
    elif any(word in symptoms for word in ["not starting", "starter", "click", "crank", "engine not working"]):
        diagnosis = "Starter Motor or Ignition Issue"
        confidence = "88%"
        next_action = "Inspect starter motor, ignition switch, and wiring"
        reason = "No-start or starter-related symptoms detected"

    # Engine Overheating
    elif "overheat" in symptoms or "too hot" in symptoms or temp > 105:
        diagnosis = "Engine Overheating"
        confidence = "90%"
        next_action = "Stop engine immediately and check coolant system"
        reason = "High engine temperature detected"

    # Low RPM / Stalling
    elif "stall" in symptoms or "shut off" in symptoms or rpm < 500:
        diagnosis = "Engine Stalling Issue"
        confidence = "85%"
        next_action = "Check fuel system, ignition, and idle control"
        reason = "Low RPM or stalling symptoms detected"

    return {
        "diagnosis": diagnosis,
        "confidence": confidence,
        "next_action": next_action,
        "reason": reason
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
    symptoms = data.get("symptoms", "")
    obd_data = get_obd_data()

    diagnosis_result = diagnose_vehicle(symptoms, obd_data)
    diagnosis_result["obd"] = obd_data

    return jsonify(diagnosis_result)


# -----------------------------
# LOCAL DEV ONLY
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5090))
    app.run(host="0.0.0.0", port=port)
