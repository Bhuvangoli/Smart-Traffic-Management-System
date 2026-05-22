from datetime import datetime
from db import traffic_collection, alerts_collection, signals_collection

# Predefined coordinates for common signals for Map Integration
SIGNAL_LOCATIONS = {
    "SIG-001": {"name": "Downtown Ave", "lat": 40.7128, "lng": -74.0060},
    "SIG-002": {"name": "Broadway", "lat": 40.7580, "lng": -73.9855},
    "SIG-003": {"name": "Central Park West", "lat": 40.7829, "lng": -73.9654},
    "SIG-004": {"name": "Wall Street", "lat": 40.7060, "lng": -74.0088},
    "SIG-005": {"name": "Times Square", "lat": 40.7588, "lng": -73.9851}
}

def get_congestion(data):
    try:
        flow = data["flowSegmentData"]
        speed = flow["currentSpeed"]
        free = flow["freeFlowSpeed"]

        ratio = speed / free

        if ratio > 0.7:
            return "green"
        elif ratio > 0.4:
            return "yellow"
        else:
            return "red"

    except Exception as e:
        print("Error in get_congestion:", e)
        return "unknown"

def process_real_traffic(location_name, lat, lon, traffic_data):
    try:
        flow = traffic_data["flowSegmentData"]
        speed = flow["currentSpeed"]
        free = flow["freeFlowSpeed"]
        ratio = speed / free
        
        if ratio > 0.7:
            color = "green"
            level = "LOW"
            vehicle_count = 20
        elif ratio > 0.4:
            color = "yellow"
            level = "MEDIUM"
            vehicle_count = 60
        else:
            color = "red"
            level = "HIGH"
            vehicle_count = 120

        timestamp = datetime.now()
        
        # Save to DB
        sig_id = f"RT-{location_name.replace(' ', '').upper()[:8]}"
        record = {
            "signal_id": sig_id,
            "location_name": location_name,
            "lat": lat,
            "lng": lon,
            "vehicle_count": vehicle_count,
            "avg_speed": speed,
            "congestion_level": level,
            "predicted_congestion": level,
            "timestamp": timestamp
        }
        traffic_collection.insert_one(record)
        
        # Persist as a signal for map markers
        status = "GREEN" if level == "LOW" else ("YELLOW" if level == "MEDIUM" else "RED")
        signals_collection.update_one(
            {"signal_id": sig_id},
            {"$set": {
                "location_name": location_name,
                "lat": lat,
                "lng": lon,
                "current_status": status,
                "timer": "Live",
                "is_realtime": True
            }},
            upsert=True
        )
        
        # Generate alert if HIGH
        if level == "HIGH":
            alert_data = {
                "type": "REALTIME_HIGH_TRAFFIC",
                "signal_id": record["signal_id"],
                "location_name": location_name,
                "message": f"Real-time high traffic detected at {location_name}. Current speed: {speed}km/h (Free flow: {free}km/h).",
                "suggestion": "Suggest alternate routes in the area.",
                "severity": "WARNING",
                "timestamp": timestamp
            }
            alerts_collection.insert_one(alert_data)
            
        return color
        
    except Exception as e:
        print("Error processing real traffic:", e)
        return "unknown"

def analyze_traffic(signal_id, vehicle_count, avg_speed):
    # Determine congestion level
    if vehicle_count > 100 and avg_speed < 20:
        congestion_level = "HIGH"
    elif vehicle_count > 50:
        congestion_level = "MEDIUM"
    else:
        congestion_level = "LOW"
        
    # Check for possible accident
    is_accident = (avg_speed < 10 and vehicle_count > 80)
    
    timestamp = datetime.now()
    
    # Get location data
    location_data = SIGNAL_LOCATIONS.get(signal_id, {"name": f"Location {signal_id}", "lat": 40.7128, "lng": -74.0060})
    
    # Basic Traffic Prediction (Moving Average)
    # Get last 5 records for this signal
    recent_records = list(traffic_collection.find({"signal_id": signal_id}).sort("timestamp", -1).limit(5))
    if len(recent_records) == 5:
        avg_recent_count = sum(r["vehicle_count"] for r in recent_records) / 5
        predicted_congestion = "HIGH" if avg_recent_count > 90 else ("MEDIUM" if avg_recent_count > 45 else "LOW")
    else:
        predicted_congestion = congestion_level # Default to current
    
    # Store traffic data
    traffic_data = {
        "signal_id": signal_id,
        "location_name": location_data["name"],
        "lat": location_data["lat"],
        "lng": location_data["lng"],
        "vehicle_count": vehicle_count,
        "avg_speed": avg_speed,
        "congestion_level": congestion_level,
        "predicted_congestion": predicted_congestion,
        "timestamp": timestamp
    }
    traffic_collection.insert_one(traffic_data)
    
    # Generate alerts
    alert_type = None
    alert_msg = None
    suggestion = None
    
    if is_accident:
        alert_type = "POSSIBLE_ACCIDENT"
        alert_msg = f"Critical! Possible accident at {signal_id} ({location_data['name']}). Speed is extremely low ({avg_speed}km/h)."
        suggestion = "Divert traffic immediately to adjacent avenues."
    elif congestion_level == "HIGH":
        alert_type = "HIGH_TRAFFIC"
        alert_msg = f"High traffic detected at {signal_id} ({location_data['name']}). Vehicles: {vehicle_count}."
        alt_signal = "SIG-002" if signal_id != "SIG-002" else "SIG-003"
        suggestion = f"Consider suggesting alternate route via {alt_signal}."
    elif avg_speed < 15 and congestion_level != "HIGH":
        alert_type = "SLOW_MOVEMENT"
        alert_msg = f"Slow movement at {signal_id} despite moderate volume."
        suggestion = "Check for road works or obstructions."

    if alert_type:
        alert_data = {
            "type": alert_type,
            "signal_id": signal_id,
            "location_name": location_data["name"],
            "message": alert_msg,
            "suggestion": suggestion,
            "severity": "CRITICAL" if is_accident else "WARNING",
            "timestamp": timestamp
        }
        alerts_collection.insert_one(alert_data)
        
    # Dynamic Signal Timing logic
    signal = signals_collection.find_one({"signal_id": signal_id})
    if not signal:
        signal = {
            "signal_id": signal_id,
            "location_name": location_data["name"],
            "lat": location_data["lat"],
            "lng": location_data["lng"],
            "current_status": "RED",
            "timer": 60
        }
        signals_collection.insert_one(signal)
        
    if congestion_level == "HIGH":
        new_timer = 120 # Heavy traffic -> long green
        status = "GREEN"
    elif congestion_level == "MEDIUM":
        new_timer = 90
        status = "GREEN"
    else:
        new_timer = 60 # Normal traffic
        status = "RED" # Keep normal cycle
        
    signals_collection.update_one(
        {"signal_id": signal_id},
        {"$set": {
            "timer": new_timer, 
            "current_status": status,
            "lat": location_data["lat"],
            "lng": location_data["lng"],
            "location_name": location_data["name"]
        }}
    )
