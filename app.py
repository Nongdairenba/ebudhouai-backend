from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()

        symptoms = data.get("symptoms", "").lower()

        # Simple AI logic
        if "battery" in symptoms:
            diagnosis = "Battery issue detected."
            confidence = "85%"
            reason = "Battery-related symptom identified."
            next_action = "Check battery voltage and charging system."
        elif "overheat" in symptoms or "heat" in symptoms:
            diagnosis = "Engine overheating detected."
            confidence = "90%"
            reason = "Overheating symptom identified."
            next_action = "Inspect coolant level and radiator."
        elif "noise" in symptoms:
            diagnosis = "Abnormal engine noise detected."
            confidence = "80%"
            reason = "Noise-related symptom identified."
            next_action = "Inspect engine belts and internal components."
        else:
            diagnosis = "General vehicle inspection recommended."
            confidence = "70%"
            reason = "No specific issue keyword detected."
            next_action = "Perform full diagnostic scan."

        obd_data = {
            "source": "Manual Input",
            "voltage": "N/A",
            "rpm": "N/A",
            "temperature": "N/A"
        }

        return jsonify({
            "diagnosis": diagnosis,
            "confidence": confidence,
            "reason": reason,
            "next_action": next_action,
            "obd": obd_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
