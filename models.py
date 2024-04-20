'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''


from sqlalchemy import String, Integer, Column, Table, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.schema import UniqueConstraint
# from sqlalchemy.orm import Mapped, mapped_column
from typing import Dict
from sqlalchemy import create_engine


# data models
class Base(DeclarativeBase):
    pass


# association table for friendships
#friends = Table('friends', Base.metadata,
    #Column('user_id_1', Integer, ForeignKey('users.id'), primary_key=True),
    #Column('user_id_2', Integer, ForeignKey('users.id'), primary_key=True),
    #Column('created_at', TIMESTAMP, server_default=func.now())
#)


# model to store user information
class User(Base):
    __tablename__ = "users"
    
    # From template
    # username: Mapped[str] = mapped_column(String, primary_key=True)
    # password: Mapped[str] = mapped_column(String)

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(255), nullable=False, default='default_salt')  # setting default for now

    friends_1 = relationship(
        "Friend", foreign_keys="[Friend.user_id_1]", back_populates="user1")
    friends_2 = relationship(
        "Friend", foreign_keys="[Friend.user_id_2]", back_populates="user2")
    

# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        self.counter = 0
    
    def get(self):
        self.counter += 1
        return self.counter

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.dict: Dict[str, int] = {}

    def create_room(self, sender: str, receiver: str) -> int:
        room_id = self.counter.get()
        self.dict[sender] = room_id
        self.dict[receiver] = room_id
        return room_id
    
    def join_room(self,  sender: str, room_id: int) -> int:
        self.dict[sender] = room_id

    def leave_room(self, user):
        if user not in self.dict.keys():
            return
        del self.dict[user]

    # gets the room id from a user
    def get_room_id(self, user: str):
        if user not in self.dict.keys():
            return None
        return self.dict[user]
    

class Friend(Base):
    __tablename__ = 'friends'
    user_id_1 = Column(Integer, ForeignKey('users.id'), primary_key=True)
    user_id_2 = Column(Integer, ForeignKey('users.id'), primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user1 = relationship("User", foreign_keys=[
                         user_id_1], back_populates="friends_1")
    user2 = relationship("User", foreign_keys=[
                         user_id_2], back_populates="friends_2")



    
class FriendRequest(Base):
    __tablename__ = 'friend_requests'  # name of this table"
    id = Column(Integer, primary_key=True) # set up the primary key
    sender_id = Column(Integer, ForeignKey('users.id'),
                       nullable=False)  # Sender ID, foreign key associated with user table
    receiver_id = Column(Integer, ForeignKey('users.id'),
                         nullable=False)  # Receiver ID, also associated with the user table
    # Request status, default is "pending"
    status = Column(String(10), default='pending')
    # The creation time is automatically generated
    created_at = Column(TIMESTAMP, server_default=func.now())

# Relational property to facilitate direct access to the User object by request
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
