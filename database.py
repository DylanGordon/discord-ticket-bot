import datetime
import random
import requests
import mysql.connector
import os
import string
from datetime import timedelta
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


# Function To Convert Time Left Into Structured Time Remaining String
def getTimeLeftStructured(timeleft, hoursMinsSeconds):
    if int(hoursMinsSeconds[0]) == 0 and int(hoursMinsSeconds[1]) > 00:
        return f"**{hoursMinsSeconds[1]}** Minutes **{hoursMinsSeconds[2]}** Seconds"
    if int(hoursMinsSeconds[0]) == 0 and int(hoursMinsSeconds[1]) == 00:
        return f"**{hoursMinsSeconds[2]}** Seconds"

# Function To Edit Channel By Ticket Status
async def editChannelNameByStatus(channel, status, ticketNumber):
    # Fetch Last Time Channel Was Updated
    Q1 = f"SELECT * from entries WHERE channel_id = {channel.id} order by time_edited desc limit 2"
    cursor.execute(Q1)
    results = cursor.fetchall()

    async def editChannel():
        await channel.edit(name=f"{status}-{ticketNumber}")
        Q2 = "INSERT INTO entries (channel_id, time_edited) VALUES (%s,%s)"
        data = (channel.id, datetime.datetime.now())
        cursor.execute(Q2, data)
        db.commit()

    if len(results) < 2:
        await editChannel()
        return None

    lastEdited = results[0][1]
    editedBeforeLast = results[1][1]
    timePast = datetime.datetime.now() - lastEdited
    timePastBeforeLastEdited = datetime.datetime.now() - editedBeforeLast

    # If Channel Has Not Been Edited In 10 Minutes Or If its been 10 Minutes Since 2nd Channel Edit
    if timePast.total_seconds() >= 600 or len(results) == 2 and timePastBeforeLastEdited.total_seconds() >= 600:
        await editChannel()
        return None

    # If Channel Has Been Edited 2 Times In 10 Minutes
    if len(results) == 2 and timePast.total_seconds() < 600:
        secondsLeft = 600 - timePast.total_seconds()
        hoursMinsSeconds = str(timedelta(seconds=int(secondsLeft))).split(':')
        timeleftStructured = getTimeLeftStructured(timePast, hoursMinsSeconds)
        return timeleftStructured
