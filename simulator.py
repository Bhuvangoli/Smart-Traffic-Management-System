import threading
import time
import random
from logic import analyze_traffic, SIGNAL_LOCATIONS

SIMULATION_ACTIVE = False
_simulation_thread = None

def _run_simulation():
    global SIMULATION_ACTIVE
    signals = list(SIGNAL_LOCATIONS.keys())
    while SIMULATION_ACTIVE:
        signal_id = random.choice(signals)
        
        # Simulate different scenarios based on random weights
        scenario = random.choices(
            ["normal", "high_traffic", "accident"],
            weights=[0.7, 0.2, 0.1]
        )[0]
        
        if scenario == "normal":
            vehicle_count = random.randint(10, 60)
            avg_speed = random.randint(30, 60)
        elif scenario == "high_traffic":
            vehicle_count = random.randint(80, 150)
            avg_speed = random.randint(10, 25)
        else: # accident
            vehicle_count = random.randint(85, 120)
            avg_speed = random.randint(0, 9)
            
        analyze_traffic(signal_id, vehicle_count, avg_speed)
        
        # Wait a few seconds before next record
        time.sleep(random.randint(5, 10))

def toggle_simulation():
    global SIMULATION_ACTIVE, _simulation_thread
    if SIMULATION_ACTIVE:
        SIMULATION_ACTIVE = False
        return False
    else:
        SIMULATION_ACTIVE = True
        _simulation_thread = threading.Thread(target=_run_simulation, daemon=True)
        _simulation_thread.start()
        return True

def get_simulation_status():
    return SIMULATION_ACTIVE
