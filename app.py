"""
ACEest Fitness & Performance - Flask Web Application
======================================================
A lightweight fitness-club management API/web app that lets a gym
coach register members, assign a training program, and automatically
calculate estimated daily calories and BMI. It also tracks weekly
adherence (workout attendance) for each member.

This module exposes both:
  * A simple server-rendered UI (GET /)
  * A JSON REST API used by the UI (and covered by the Pytest suite)

Run locally:
    python app.py

Run with gunicorn (production):
    gunicorn --bind 0.0.0.0:5000 app:app
"""

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Domain data: training programs and their approximate calorie multipliers
# (kcal per kg of bodyweight per day) - derived from the original desktop
# ACEest Fitness application.
# ---------------------------------------------------------------------------
PROGRAMS = {
    "Fat Loss": {
        "factor": 22,
        "workout": "Squats, HIIT cardio, bench press, deadlifts, active recovery",
        "diet": "High protein, moderate carb, calorie deficit",
    },
    "Muscle Gain": {
        "factor": 35,
        "workout": "5x5 strength split: squat, bench, deadlift, press, rows",
        "diet": "High protein, calorie surplus",
    },
    "Beginner": {
        "factor": 26,
        "workout": "Full body circuit: air squats, ring rows, push-ups",
        "diet": "Balanced macronutrient meals",
    },
}

# ---------------------------------------------------------------------------
# In-memory data store.
# A real deployment would replace this with a database (see the SQLite
# implementation in earlier project iterations). Keeping it in-memory here
# makes the app trivially easy to containerize and unit test without any
# external state or file permissions issues.
# ---------------------------------------------------------------------------
members = {}


def _bmi_category(bmi: float) -> str:
    """Return the standard WHO BMI category for a given BMI value."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _compute_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 2)


# ---------------------------------------------------------------------------
# UI routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Render the member-management dashboard."""
    return render_template("index.html", programs=list(PROGRAMS.keys()))


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    """Simple health-check endpoint used by Docker/CI/monitoring."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/programs", methods=["GET"])
def get_programs():
    """Return all available training programs."""
    return jsonify(PROGRAMS), 200


@app.route("/api/members", methods=["GET"])
def list_members():
    """Return all registered members."""
    return jsonify(list(members.values())), 200


@app.route("/api/members", methods=["POST"])
def add_member():
    """Register a new member and calculate their calorie target / BMI."""
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    program = data.get("program")
    age = data.get("age")
    weight = data.get("weight")
    height = data.get("height")  # optional, in cm

    if not name or not program:
        return jsonify({"error": "'name' and 'program' are required fields"}), 400

    if program not in PROGRAMS:
        message = f"Unknown program '{program}'. Valid options: {list(PROGRAMS.keys())}"
        return jsonify({"error": message}), 400

    try:
        age = int(age)
        weight = float(weight)
    except (TypeError, ValueError):
        return jsonify({"error": "'age' must be an integer and 'weight' a number"}), 400

    if age <= 0 or weight <= 0:
        return jsonify({"error": "'age' and 'weight' must be positive values"}), 400

    bmi = None
    bmi_category = None
    if height not in (None, ""):
        try:
            height = float(height)
            if height <= 0:
                raise ValueError
            bmi = _compute_bmi(weight, height)
            bmi_category = _bmi_category(bmi)
        except (TypeError, ValueError):
            return jsonify({"error": "'height' must be a positive number in cm"}), 400

    calories = round(weight * PROGRAMS[program]["factor"])

    member = {
        "name": name,
        "age": age,
        "weight": weight,
        "height": height,
        "program": program,
        "calories": calories,
        "bmi": bmi,
        "bmi_category": bmi_category,
        "adherence_log": [],
    }
    members[name] = member
    return jsonify(member), 201


@app.route("/api/members/<string:name>", methods=["GET"])
def get_member(name):
    """Fetch a single member's profile."""
    member = members.get(name)
    if not member:
        return jsonify({"error": f"Member '{name}' not found"}), 404
    return jsonify(member), 200


@app.route("/api/members/<string:name>", methods=["DELETE"])
def delete_member(name):
    """Remove a member from the system."""
    if name not in members:
        return jsonify({"error": f"Member '{name}' not found"}), 404
    del members[name]
    return jsonify({"message": f"Member '{name}' deleted"}), 200


@app.route("/api/members/<string:name>/progress", methods=["POST"])
def log_progress(name):
    """Log a weekly adherence percentage (0-100) for a member."""
    if name not in members:
        return jsonify({"error": f"Member '{name}' not found"}), 404

    data = request.get_json(silent=True) or {}
    adherence = data.get("adherence")

    try:
        adherence = int(adherence)
    except (TypeError, ValueError):
        return jsonify({"error": "'adherence' must be an integer between 0 and 100"}), 400

    if not (0 <= adherence <= 100):
        return jsonify({"error": "'adherence' must be between 0 and 100"}), 400

    members[name]["adherence_log"].append(adherence)
    return jsonify(members[name]), 200


@app.route("/api/bmi", methods=["POST"])
def calculate_bmi():
    """Stateless BMI calculator endpoint."""
    data = request.get_json(silent=True) or {}

    try:
        weight = float(data.get("weight"))
        height = float(data.get("height"))
    except (TypeError, ValueError):
        return jsonify({"error": "'weight' (kg) and 'height' (cm) are required numbers"}), 400

    if weight <= 0 or height <= 0:
        return jsonify({"error": "'weight' and 'height' must be positive"}), 400

    bmi = _compute_bmi(weight, height)
    return jsonify({"bmi": bmi, "category": _bmi_category(bmi)}), 200


if __name__ == "__main__":
    # debug=True is fine for local development; the Docker image runs
    # this via gunicorn instead (see Dockerfile).
    app.run(host="0.0.0.0", port=5000, debug=True)
