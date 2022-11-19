from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Loads Environment Variables
load_dotenv()

# Connect To Mongo DB
cluster = MongoClient(os.getenv("mongodbconnectionstring"))
mongo = cluster['BlastGaming']