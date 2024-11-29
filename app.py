from flask import Flask, send_file, request, render_template, jsonify
import json
import os
import uuid
from werkzeug.routing import BaseConverter

app = Flask(__name__)
class UUID(BaseConverter):
    regex = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
app.url_map.converters['uuid'] = UUID
app.config['TEMPLATES_AUTO_RELOAD'] = True

DATA_PATH = './data/'

def load_data(filename):
    with open(os.path.join(DATA_PATH, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(filename, data):
    with open(os.path.join(DATA_PATH, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/login', methods=['POST'])
def login():
    user = request.get_json()
    passengers = load_data('passengers.json')
    bookings = load_data('bookings.json')

    passenger = next((p for p in passengers if p['username'] == user['username'] and p['password'] == user['password']), None)
    if passenger:
        booking = next((b for b in bookings if b['passengerId'] == passenger['id']), None)
        if booking:
            return jsonify(success=True, flightId=booking['flightId'])
    return jsonify(success=False)

@app.route('/register', methods=['POST'])
def register():
    user = request.get_json()
    passengers = load_data('passengers.json')
    bookings = load_data('bookings.json')

    passenger_id = str(uuid.uuid4())
    booking_id = str(uuid.uuid4())

    new_passenger = {
        'id': passenger_id,
        'username': user['username'],
        'password': user['password'],
        'firstname': user.get('firstname', ''),
        'lastname': user.get('lastname', ''),
        'patronymic': user.get('patronymic', ''),
        'birthdate': user.get('birthdate', ''),
        'series': user.get('series', '')
    }
    passengers.append(new_passenger)
    save_data('passengers.json', passengers)

    new_booking = {
        'id': booking_id,
        'passengerId': passenger_id,
        'flightId': None,
        'isRegistered': False,
        'seat': None
    }
    bookings.append(new_booking)
    save_data('bookings.json', bookings)

    return '', 200

@app.route('/api/bookings/<uuid:id>')
def get_flight(id) -> str:
    bookings = load_data('bookings.json')
    flights = load_data('flights.json')
    passengers = load_data('passengers.json')

    booking = next((b for b in bookings if b['id'] == str(id)), None)
    if not booking:
        return 'Booking not found', 404

    flight = next((f for f in flights if f['id'] == booking['flightId']), {})
    passenger = next((p for p in passengers if p['id'] == booking['passengerId']), {})

    result = {
        **booking,
        'flight': flight,
        'passenger': passenger
    }
    return result

@app.route('/api/passengers/<uuid:id>')
def get_passenger(id) -> str:
    passengers = load_data('passengers.json')
    passenger = next((p for p in passengers if p['id'] == str(id)), None)
    return passenger if passenger else ('Passenger not found', 404)

@app.route('/api/passengers/validate', methods=['POST'])
def validate_passenger() -> str:
    data = request.get_json()
    passengers = load_data('passengers.json')

    passenger = next((p for p in passengers if
                      p['firstname'] == data['firstname'] and
                      p['lastname'] == data['lastname'] and
                      p['patronymic'] == data['patronymic'] and
                      p['birthdate'] == data['birthdate'] and
                      p['series'] == data['series']), None)
    return 'True' if passenger else 'False'

# Complete passenger registration
@app.route('/api/bookings/<uuid:id>', methods=['POST'])
def finish_registration(id) -> str:
    data = request.get_json()
    bookings = load_data('bookings.json')

    for booking in bookings:
        if booking['id'] == str(id):
            booking['isRegistered'] = True
            booking['seat'] = int(data['seat'])
            save_data('bookings.json', bookings)

            route_list = get_flight(id)
            with open(f'./{id}.txt', 'w') as f:
                f.write(str(route_list))
            return 'True'

    return 'Booking not found', 404

# Return form for entering passport data
@app.route('/passport')
def passport():
    context = {}
    context['id'] = request.args['flight']
    return render_template('passport.html', context=context)

# Return interface for starting registration
@app.route('/booking')
def booking():
    flight_id = request.args.get('flight')
    if not flight_id:
        return 'Flight ID is required', 400

    bookings = load_data('bookings.json')
    flights = load_data('flights.json')
    passengers = load_data('passengers.json')

    booking = next((b for b in bookings if b['id'] == flight_id), None)
    if not booking:
        return 'Booking not found', 404

    flight = next((f for f in flights if f['id'] == booking['flightId']), {})
    passenger = next((p for p in passengers if p['id'] == booking['passengerId']), {})

    context = {
        'id': booking['id'],
        'company': 'Lufthasa',
        'path': f"{flight.get('origin', '')} - {flight.get('destination', '')}",
        'from': flight.get('origin', ''),
        'to': flight.get('destination', ''),
        'timefrom': flight.get('departureTime', ''),
        'timeto': flight.get('arrivalTime', ''),
        'firstname': passenger.get('firstname', ''),
        'lastname': passenger.get('lastname', ''),
        'patronymic': passenger.get('patronymic', ''),
    }

    return render_template('booking.html', context=context)

# Return form for seat selection
@app.route('/seat')
def seat():
    context = {}
    bookings = load_data('bookings.json')
    context['id'] = request.args['flight']
    flight_id = next((b['flightId'] for b in bookings if b['id'] == context['id']), None)
    if not flight_id:
        return 'Flight not found', 404

    occupied_seats = [b['seat'] for b in bookings if b['flightId'] == flight_id and b['seat'] is not None]
    context['seats'] = [True] * 256
    for seat in occupied_seats:
        context['seats'][seat] = False
    return render_template('seat.html', context=context)

# Return form for entering booking number (main page)
@app.route('/')
def main():
    return render_template('main.html')

@app.route('/route')
def route():
    context = {}
    context['id'] = request.args['flight']
    flights = load_data('flights.json')
    flight = next((f for f in flights if f['id'] == context['id']), None)
    if not flight:
        return 'Flight not found', 404
    context['origin'] = flight['origin']
    context['destination'] = flight['destination']
    context['departureTime'] = flight['departureTime']
    context['arrivalTime'] = flight['arrivalTime']
    return render_template('route.html', context=context)

@app.route('/choose_route')
def choose_route():
    flights = load_data('flights.json')
    return render_template('choose_route.html', flights=flights)

@app.route('/download/<uuid:id>')
def download(id):
    file_path = f'./{id}'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, attachment_filename=f'{id}')
    else:
        return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=False, port=3400)