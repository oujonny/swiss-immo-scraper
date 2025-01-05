from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['immo_db']
listings_collection = db['listings']