import base64
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, abort, url_for, session, jsonify, redirect
from flask_socketio import SocketIO
from flask_cors import CORS
import db
import secrets
import bcrypt

# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

# don't remove this!!
import socket_routes

load_dotenv()

import hashlib

# index page
@app.route("/")
def index():
    return render_template("index.jinja")


# login page
@app.route("/login")
def login():
    return render_template("login.jinja")


# handles user login requests 
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)

    # get the username and password from the JSON request
    username = request.json.get("username")
    password = request.json.get("password")

    # Retrieve user data from the database based on the username
    user = db.get_user(username)
    if user is None:
        return "Error: User does not exist!"
    
     # Get the salt value from the database (base64-encoded string)
    salt = user.salt
    # Generate a hash password using the salt value in the database and the password entered by the user
    if validate_password(password, user.password_hash, salt):
        # Login successful
        session['user_id'] = user.id
        return url_for('home', username=username)
    else:
        return "Error: Password does not match!"


def generate_salt():
    return base64.b64encode(os.urandom(16)).decode('utf-8')


def hash_password(password, salt):

    hasher = hashlib.sha256()
    # The salt value is first converted from the base64-encoded string back to bytes
    salt_bytes = base64.b64decode(salt.encode('utf-8'))
    hasher.update(salt_bytes)
    hasher.update(password.encode('utf-8'))
    return hasher.hexdigest()


def validate_password(input_password, stored_password, stored_salt):

    hashed_input_password = hash_password(input_password, stored_salt)
    return hashed_input_password == stored_password

    


# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")



# handles user signup requests 
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)
    username = request.json.get("username")
    password = request.json.get("password")

    # Generates the salt value and hashes the password
    salt = generate_salt()
    hashed_password = hash_password(password, salt)

    if db.get_user(username) is None:
        # Store the hashed password and salt value
        # Both the salt value and the hash password are string types
        db.insert_user(username, hashed_password, salt)
        return url_for('home', username=username)
    return "Error: User already exists!"


# route to display the add friend form
@app.route("/add-friend-form")
def add_friend_form():
    # render the add friend form template when a GET request is made to this route
    return render_template("add_friend_form.jinja")


# 200 means successful, 400 means failed
# Define a route to handle POST requests for adding friends.


# Define a route to handle POST requests for adding friends.
@app.route('/add-friend', methods=['POST'])
def add_friend():
    print("Received add friend request...")
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    if not request.is_json:
        return jsonify({'error': 'Invalid content type, expected application/json'}), 415
    data = request.get_json()
    friend_username = data.get('friend_username')
    # Add this line to confirm the value of friend_username
    print("Friend username:", friend_username)
    if not friend_username:
        return jsonify({'error': 'Missing friend username'}), 400
    user_id = session['user_id']
    message, success = db.add_friend(user_id, friend_username)
    # Add this line to confirm the message of adding a friend
    print("Add friend message:", message)
    # Add this line to confirm that you successfully added friends
    print("Add friend success:", success)
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 400


# handles sending friend requests
@app.route('/send-friend-request', methods=['POST'])
def send_friend_request():
    print("Received send friend request...")
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401

    receiver_username = request.form.get('username')
    print("Receiver username:", receiver_username)

    if not receiver_username:
        return jsonify({'error': 'Missing receiver username'}), 400

    sender_id = session['user_id']

    # Call the database function to send a friend request
    message, success = db.send_friend_request(sender_id, receiver_username)

    if not success:
        return jsonify({'error': message}), 404

    return jsonify({'message': 'Friend request sent successfully'}), 200


# Route to handle GET requests for displaying a user's received and sent friend requests
@app.route('/friend-requests')
def friend_requests():
    user_id = session.get('user_id')
    if user_id is None:
        # Handle cases where the user is not logged in, such as redirects to the login page
        return redirect(url_for('login'))

    received_requests = db.get_received_friend_requests(user_id)
    return render_template('friend_requests.jinja', received_requests=received_requests)


# Define a route to handle POST requests for responding to friend requests
@app.route('/respond-to-request', methods=['POST'])
def respond_to_request():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or no data provided'}), 400
    request_id = data.get('request_id')
    action = data.get('action')

    if not request_id or not action:
        return jsonify({'error': 'Missing request ID or action'}), 400

    if action == 'Accept':
        message, success = db.accept_friend_request(request_id)
    else:
        message, success = db.update_friend_request(request_id, action)

    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 404


# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404


@app.route("/home")
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    username = request.args.get("username", "")
    try:
        # Call the database function to get the user's friend list
        friends = db.get_friends(session['user_id'])
        print(friends)

        # Gets the friend request received by the user
        received_requests = db.get_received_friend_requests(session['user_id'])
        print(received_requests)

        return render_template("home.jinja", username=username, friends=friends, received_requests=received_requests)
    except Exception as e:
        app.logger.error(f"Failed to fetch data: {e}")
        friends = []
        received_requests = []
        return render_template("home.jinja", username=username, friends=friends, received_requests=received_requests)


if __name__ == '__main__':

    cert_path = 'localhost+2.pem'
    key_path = 'localhost+2-key.pem'
    if os.path.exists(cert_path) and os.path.exists(key_path):
        socketio.run(app, debug=True, port=5000,
                     ssl_context=(cert_path, key_path))
    else:
        print("SSL certificates not found, starting app in HTTP only.")
        socketio.run(app, debug=True, port=5000)
