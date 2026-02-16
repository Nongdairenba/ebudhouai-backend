from flask import Flask, request, jsonify, render_template
import random

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()

        # Get user input safely
        rpm = data.get("rpm", 0)
        voltage = data.get("voltage", 0)
        temperature = data.get("temperature", 0)

        # Simple AI logic (you can improve later)
        if voltage < 12:
            diagnosis = "Battery voltage is low. Check battery or charging system."
        elif temperature > 100:
            diagnosis = "Engine overheating detected."
        elif rpm < 500:
            diagnosis = "Engine RPM too low. Possible stalling issue."
        else:
            diagnosis = "Vehicle parameters look normal."

        # OBD Data (FIXED with source field)
        obd_data = {
            "source": "Manual Input",
            "rpm": rpm,
            "voltage": voltage,
            "temperature": temperature
        }

        response = {
            "status": "success",
            "diagnosis": diagnosis,
            "obd": obd_data
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
