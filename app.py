import io
import csv
from flask import Flask, render_template, request, redirect, flash, jsonify, Response
from logic import analyze_traffic
from db import traffic_collection, alerts_collection, signals_collection
from simulator import toggle_simulation, get_simulation_status

app = Flask(__name__)
app.secret_key = "smart_city_secret"

@app.route("/")
def home():
    # Dashboard view data
    total_records = traffic_collection.count_documents({})
    high_traffic_zones = traffic_collection.count_documents({"congestion_level": "HIGH"})
    total_alerts = alerts_collection.count_documents({})
    
    return render_template("index.html", 
                           total_records=total_records, 
                           high_traffic_zones=high_traffic_zones,
                           total_alerts=total_alerts)

@app.route("/add", methods=["GET", "POST"])
def add_data():
    if request.method == "POST":
        try:
            signal_id = request.form.get("signal_id")
            vehicle_count = int(request.form.get("vehicle_count"))
            avg_speed = int(request.form.get("avg_speed"))
            
            analyze_traffic(signal_id, vehicle_count, avg_speed)
            flash("Traffic data added successfully!", "success")
            return redirect("/view")
        except Exception as e:
            flash(f"Error adding data: {e}", "danger")
            
    return render_template("add_data.html")

@app.route("/view")
def view_data():
    level_filter = request.args.get("level")
    query = {}
    if level_filter:
        query["congestion_level"] = level_filter.upper()
        
    data = list(traffic_collection.find(query).sort("timestamp", -1))
    return render_template("view_data.html", data=data)

@app.route("/alerts")
def alerts():
    all_alerts = list(alerts_collection.find().sort("timestamp", -1))
    return render_template("alerts.html", alerts=all_alerts)

# --- NEW ADVANCED API ROUTES ---

@app.route("/api/dashboard_data")
def api_dashboard_data():
    """Returns JSON data for charts, map, and auto-refresh"""
    # Summary stats
    stats = {
        "total_records": traffic_collection.count_documents({}),
        "high_traffic_zones": traffic_collection.count_documents({"congestion_level": "HIGH"}),
        "total_alerts": alerts_collection.count_documents({})
    }
    
    # Recent chart data (last 20 records)
    recent = list(traffic_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(20))
    # Reverse to have chronological order for chart
    recent.reverse()
    chart_labels = [r["timestamp"].strftime("%H:%M:%S") if r.get("timestamp") else "" for r in recent]
    chart_vehicles = [r["vehicle_count"] for r in recent]
    
    # Doughnut chart data
    doughnut_data = {
        "HIGH": traffic_collection.count_documents({"congestion_level": "HIGH"}),
        "MEDIUM": traffic_collection.count_documents({"congestion_level": "MEDIUM"}),
        "LOW": traffic_collection.count_documents({"congestion_level": "LOW"})
    }
    
    # Map markers data (from signals collection)
    signals = list(signals_collection.find({}, {"_id": 0}))
    
    return jsonify({
        "stats": stats,
        "chart_labels": chart_labels,
        "chart_vehicles": chart_vehicles,
        "doughnut_data": doughnut_data,
        "signals": signals
    })

@app.route("/api/simulation/toggle", methods=["POST"])
def api_toggle_simulation():
    is_active = toggle_simulation()
    return jsonify({"active": is_active})

@app.route("/api/simulation/status", methods=["GET"])
def api_simulation_status():
    return jsonify({"active": get_simulation_status()})

@app.route("/export")
def export_csv():
    # Query all data
    data = list(traffic_collection.find().sort("timestamp", -1))
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Timestamp", "Signal ID", "Location", "Vehicle Count", "Avg Speed", "Congestion Level", "Predicted Next"])
    
    for row in data:
        ts = row.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if row.get("timestamp") else "N/A"
        writer.writerow([
            ts, 
            row.get("signal_id", ""), 
            row.get("location_name", ""),
            row.get("vehicle_count", 0), 
            row.get("avg_speed", 0), 
            row.get("congestion_level", ""),
            row.get("predicted_congestion", "")
        ])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=traffic_data.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True, threaded=True)