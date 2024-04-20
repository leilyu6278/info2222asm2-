
from flask import Flask, request, jsonify, session
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session
from models import *
from sqlalchemy.exc import SQLAlchemyError
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
load_dotenv()

# creates the database directory
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

conn = psycopg2.connect(
    dbname="info2222-asm2",
    user="leilyu",
    password="LVlei20030808",
    host="info2222-asm2.cf62i6ik4art.ap-southeast-2.rds.amazonaws.com",
    port="5432"
)

# "database/main.db" specifies the database file
# change it if you wish
# turn echo = True to display the sql output
engine = create_engine(DATABASE_URL, echo=False)

# Create a session local class
# Create a session local class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# initializes the database
Base.metadata.create_all(engine)

# inserts a user to the database
def insert_user(username: str, password_hash: str, salt='default_salt'):
    with Session(engine) as session:
        user = User(username=username, password_hash=password_hash, salt=salt)
        session.add(user)
        session.commit()

# get a user from the database
def get_user(username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        return user

# get friend from database
def get_friends(user_id):
    with SessionLocal() as session:
        # query for friends where the user is the first user in the friendship
        friends_1 = session.query(User.username).join(
            Friend, User.id == Friend.user_id_2
        ).filter(Friend.user_id_1 == user_id).all()

        # the second
        friends_2 = session.query(User.username).join(
            Friend, User.id == Friend.user_id_1
        ).filter(Friend.user_id_2 == user_id).all()

        # Store the user name in the collection to remove duplicates
        friends_combined = set(f.username for f in friends_1 + friends_2)
        print(friends_combined)
        return list(friends_combined)


# add a friend for the given user
def add_friend(user_id: int, friend_username: str):
    with SessionLocal() as session:
        # Query the database to find the user associated with the given friend username
        friend = session.query(User).filter(
            User.username == friend_username).first()

        # If the friend user does not exist, return an error message and False indicating failure
        if not friend:
            return "User not found", False

        if user_id == friend.id:
            return "Cannot add yourself as a friend", False

        # Check if there is already a friendship between the two users
        existing_friendship = session.query(Friend).filter(
            (Friend.user_id_1 == user_id) & (Friend.user_id_2 == friend.id) |
            (Friend.user_id_1 == friend.id) & (Friend.user_id_2 == user_id)
        ).first()

        # If there is an existing friendship, return an error message and False indicating failure
        if existing_friendship:
            return "Already friends", False

        # Create a new friendship by adding entries in the Friend table for both user
        session.add_all([
            Friend(user_id_1=user_id, user_id_2=friend.id),
            Friend(user_id_1=friend.id, user_id_2=user_id)
        ])
        session.commit()

        return "Friend added successfully", True



# send request to friend
def send_friend_request(sender_id: int, receiver_username: str):
    with SessionLocal() as session:
        friend = session.query(User).filter(
            User.username == receiver_username).first()
        if not friend:
            return "User not found", False
        print(sender_id)
        print(friend.id)
        if sender_id == friend.id:
            return "Cannot add yourself as a friend", False

        existing_friendship = session.query(Friend).filter(
            (Friend.user_id_1 == sender_id) & (Friend.user_id_2 == friend.id) |
            (Friend.user_id_1 == friend.id) & (Friend.user_id_2 == sender_id)
        ).first()

        if existing_friendship:
            return "Already friends", False
        try:
            receiver = session.query(User).filter_by(
                username=receiver_username).first()
            if not receiver:
                return "Receiver not found", False

            # Check if a friend request has already been sent
            if session.query(FriendRequest).filter_by(sender_id=sender_id, receiver_id=receiver.id).first():
                return "Friend request already sent", False

            # Create a new friend request object
            new_request = FriendRequest(
                sender_id=sender_id, receiver_id=receiver.id)
            session.add(new_request)
            session.commit()
            return "Friend request sent successfully", True
        except Exception as e:
            session.rollback()
            return f"Error sending friend request: {str(e)}", False


def get_received_friend_requests(user_id):
    """
    Get received friend requests for a user.

    Parameters:
    - user_id: The ID of the user.

    Returns:
    - A list of dictionaries representing the received friend requests.
    """
    try:
        cursor = conn.cursor()
        query = sql.SQL("""
            SELECT friend_requests.id, sender.username AS sender_username
            FROM friend_requests
            INNER JOIN users AS sender ON friend_requests.sender_id = sender.id
            WHERE friend_requests.receiver_id = %s
        """)
        cursor.execute(query, (user_id,))
        received_requests = [{'id': row[0], 'sender_username': row[1]} for row in cursor.fetchall()]
        return received_requests
    except psycopg2.Error as e:
        print("Error fetching received friend requests:", e)
        return []


# Add other database functions as needed...

# retrieves all friend requests sent to and made by a user
# return one for received requests and another for sent requests
def get_friend_requests(user_id: int):
    with SessionLocal() as session:
        try:
            # Retrieve all friend requests received by the user
            received_requests = session.query(FriendRequest)\
                                       .filter(FriendRequest.receiver_id == user_id)\
                                       .all()
            # Retrieve all friend requests sent by the user
            sent_requests = session.query(FriendRequest)\
                                   .filter(FriendRequest.sender_id == user_id)\
                                   .all()
            return received_requests, sent_requests
        except Exception as e:
            session.rollback()
            return f"Failed to fetch friend requests: {str(e)}", None

# updates the status of a friend request based on user action (accept or reject)
def update_friend_request(request_id: int, new_status: str):
    with SessionLocal() as session:
        try:
            # Find a specific friend request by ID
            friend_request = session.query(FriendRequest)\
                                    .filter(FriendRequest.id == request_id)\
                                    .one_or_none()
            if not friend_request:
                return "Request not found", False

            # Update the status of your friend request
            friend_request.status = new_status

            if new_status == "Reject":
                friend_request = session.query(FriendRequest).filter(FriendRequest.id == request_id).one_or_none()
                if not friend_request:
                    return "Request not found", False
                if friend_request.sender_id == friend_request.receiver_id:
                    return "Cannot add yourself as a friend", False
                # Delete friend request
                session.delete(friend_request)
                session.commit()
            return "Request successful update", True
        except Exception as e:
            session.rollback()
            return f"Error updating request: {str(e)}", False


def accept_friend_request(request_id: int):
    with SessionLocal() as session:
        try:
            # Get a friend request
            friend_request = session.query(FriendRequest).filter(FriendRequest.id == request_id).one_or_none()
            if not friend_request:
                return "Request not found", False
            if friend_request.sender_id == friend_request.receiver_id:
                return "Cannot add yourself as a friend", False
            # Adds the friend request to the friends table
            friendship_1 = Friend(user_id_1=friend_request.sender_id, user_id_2=friend_request.receiver_id)
            friendship_2 = Friend(user_id_1=friend_request.receiver_id, user_id_2=friend_request.sender_id)
            session.add_all([friendship_1, friendship_2])

            # Delete friend request
            session.delete(friend_request)
            session.commit()

            return "Add friends successfully", True
        except Exception as e:
            session.rollback()
            return f"An error occurred while processing a friend request: {str(e)}", False

#test whether connect or not
if __name__ == "__main__":
    with SessionLocal() as session:
        print("The database Connection successful!")