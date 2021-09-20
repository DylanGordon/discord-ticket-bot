import random
import requests
import mysql.connector
import os
import string
from dotenv import load_dotenv

# Loads Environment Variables
load_dotenv()

# Connect To Database
try:
    db = mysql.connector.connect(host=os.getenv('host'), user=os.getenv('user'), passwd=os.getenv('pass'), database=os.getenv('database'),port=os.getenv('port'),autocommit=True,buffered=True)
    cursor = db.cursor()
except mysql.connector.Error as err:
    print(err)

# Function To Shorten URLS
def shorten(url):
    api = "https://url-shortener-production.rapid-edu.workers.dev/create"
    headers = {"Content-Type": "application/json"}
    code = ''.join(random.choice(string.digits) for i in range(12))
    data = {"code": code, "target": url}
    requests.post(url=api, json=data, headers=headers)
    return 'https://url.rpd.gg/'+code