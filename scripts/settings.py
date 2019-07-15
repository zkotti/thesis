from future import print_function

from pymongo import MongoClient

MONGODB_SERVER = ''
MONGO_CLIENT = MongoClient(host=MONGODB_SERVER)
