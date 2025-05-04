from flask import Flask, request, jsonify
import pandas as pd
import random
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
# Load and preprocess data
data = pd.read_excel("/Edrawsoft/Task/model1/egypt_landmarks.xlsx")
data.columns = data.columns.str.strip()

# Ensure required and optional columns exist
required_columns = ['type', 'cost', 'rating', 'latitude', 'longitude', 'description']
optional_columns = ['opening_hours', 'best_time_to_visit', 'image']
for col in required_columns + optional_columns:
    if col not in data.columns:
        data[col] = ''

# Clean and preprocess data
data.drop_duplicates(subset='name', inplace=True)
for col in required_columns:
    if data[col].isnull().sum() > 0:
        data[col] = data[col].fillna(data[col].median() if col in ['cost', 'rating'] else "Unknown")

data['cost'] = data['cost'].apply(lambda x: max(x, 0))
data['rating'] = data['rating'].apply(lambda x: min(max(x, 0), 5))
data['description'] = data['description'].apply(lambda x: " ".join(x.strip().lower().split()))
data['latitude'] = pd.to_numeric(data['latitude'], errors='coerce')
data['longitude'] = pd.to_numeric(data['longitude'], errors='coerce')
data = data.dropna(subset=['latitude', 'longitude'])
data = data[(data['latitude'].between(-90, 90)) & (data['longitude'].between(-180, 180))]

# Add recommended activities and visit duration
data['recommended_activities'] = data['type'].map({
    'Ancient Ruins': 'Guided tours, Photography, Archaeology Workshops',
    'Religious': 'Spiritual retreats, Meditation sessions, Historical exploration',
    'historic': 'Museum tours, Walking tours, Cultural storytelling',
    'Landmark': 'Art exhibitions, Scenic photography',
    'Amusement': 'Light shows, Roller coasters, Interactive games',
}).fillna('Explore and enjoy')

data['visit_duration'] = data['type'].map({
    'Ancient Ruins': '2-3.5 hours', 'Landmark': '2-4 hours', 'historic': '3-4 hours',
    'Religious': '3-4 hours', 'Amusement': '2.5-4 hours',
}).fillna('Flexible')

# Add random opening hours and best time to visit
data['opening_hours'] = data['opening_hours'].apply(lambda x: random.choice([
    "9 AM - 5 PM", "8 AM - 6 PM", "10 AM - 4 PM", "7 AM - 7 PM", "9 AM - 7 PM"]) if x == '' else x)

data['best_time_to_visit'] = data['best_time_to_visit'].apply(lambda x: random.choice([
    "Saturday - Monday", "Tuesday - Wednesday", "Thursday", "Friday - Tuesday", "Sunday - Wednesday"]) if x == '' else x)

data['image'] = data['image'].apply(lambda x: x if str(x).startswith("http") else "https://via.placeholder.com/150")

# Function to plan the trip
def plan_trip_with_airport(days, budget, daily_activities=4, food_budget_ratio=0.2, budget_tolerance=0.05):
    daily_budget = budget / days
    place_budget = daily_budget * (1 - food_budget_ratio)
    affordable_places = data[data['cost'] <= place_budget * (1 - budget_tolerance)].sort_values(by='rating', ascending=False)
    used_places, recommended_places, total_cost = set(), [], 0

    for day in range(days):
        day_plan, day_cost, used_types = [], 0, set()
        for _, place in affordable_places.iterrows():
            if pd.notnull(place['latitude']) and pd.notnull(place['longitude']) and place['name'] not in used_places:
                if day_cost + place['cost'] <= place_budget and place['type'] not in used_types:
                    day_plan.append(place)
                    day_cost += place['cost']
                    used_types.add(place['type'])
                    used_places.add(place['name'])
                    if len(day_plan) >= daily_activities:
                        break

        recommended_places.append((f"Day {day + 1}", pd.DataFrame(day_plan)))
        total_cost += day_cost

    return recommended_places, total_cost, "Cairo International Airport (CAI)", "October - April", "October"

# API endpoint
@app.route('/')
def home():
    return  "plan_trip"

@app.route('/plan_trip', methods=['POST'])
def plan_trip():
    request_data = request.get_json()
    days, budget = request_data.get('days'), request_data.get('budget')

    if not days or not budget:
        return jsonify({"error": "Please provide both 'days' and 'budget' in the request body."}), 400

    try:
        days, budget = int(days), int(budget)
    except ValueError:
        return jsonify({"error": "Invalid input. 'days' and 'budget' must be numbers."}), 400

    trip_plan, total_cost, arrival_airport, best_time_to_visit, suggested_month = plan_trip_with_airport(days, budget)

    # Build the response
    response = {
        "arrival_airport": arrival_airport,
        "best_time_to_visit": best_time_to_visit,
        "suggested_month": suggested_month,
        "trip_plan": [{
            "day": day,
            "places": [{
                "name": place['name'],
                "cost": place['cost'],
                "rating": place['rating'],
                "description": place['description'],
                "image": place['image'],
                "address": place['address'],
                "opening_hours": place['opening_hours'],
                "best_time_to_visit": place['best_time_to_visit'],
                "visit_duration": place['visit_duration'],
                "recommended_activities": place['recommended_activities']
            } for _, place in places.iterrows()]
        } for day, places in trip_plan],
        "total_cost": total_cost  # Total cost is now the last key in the response
    }

    return jsonify(response), 200

# Run the Flask app
if __name__ == '__main__':
     app.run(host="0.0.0.0", port=5000)
