#!/usr/bin/python3
import requests
from datetime import datetime, timezone, timedelta
import time
import logging
import os
from logging.handlers import TimedRotatingFileHandler
import traceback
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np


# Setup logging
log_file = '/home/unicamp/photo_collection/telegrambot_10min.log'
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

handler = TimedRotatingFileHandler(
    log_file, 
    when='midnight',  # Rotate logs daily
    interval=1,       # Interval in days
    backupCount=7     # Keep logs for 7 days
)
handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def send_image_to_telegram(image_path, caption=""):
    """Send an image to Telegram chat"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    with open(image_path, 'rb') as image_file:
        files = {'photo': image_file}
        data = {'chat_id': chat_id, 'caption': caption}
        
        response = requests.post(url, files=files, data=data)
    
    if response.status_code == 200:
        logger.info("Image sent successfully")
        return True
    else:
        logger.info(f"Failed to send image: {response.status_code} - {response.text}")
        return False

def send_image_url_to_telegram(image_url, caption=""):
    """Send an image from URL to Telegram chat"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    payload = {
        'chat_id': chat_id,
        'photo': image_url,
        'caption': caption
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        logger.info("Image sent successfully")
        return True
    else:
        logger.info(f"Failed to send image: {response.status_code} - {response.text}")
        return False

def send_image_url_to_telegram(image_url, caption=""):
    """Send an image from URL to Telegram chat"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    payload = {
        'chat_id': chat_id,
        'photo': image_url,
        'caption': caption
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        logger.info("Image sent successfully")
        return True
    else:
        logger.info(f"Failed to send image: {response.status_code} - {response.text}")
        return False
# Config
minutes_tolerance = 10#10
seconds = 10 * 60  # check every 25 minutes

# UTC-3 timezone object
utc_minus_3 = timezone(timedelta(hours=-3))
# utc_minus_3 = timezone(timedelta(hours=+0))
# prevent flooding
consecutive_alerts = 0
max_alerts = 10

def read_token(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()
token = read_token('/home/unicamp/photo_collection/token_read_twin.txt')
org = ""
url = ''
write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

days = '1'

start_time_filter = pd.Timestamp('2025-01-01 00:06:00', tz='UTC')
end_time_filter = pd.Timestamp('2028-08-15 23:59:59', tz='UTC')

def preprocess_subset(df,
                      timecol='_time',
                      start_time_filter=start_time_filter,
                      end_time_filter=end_time_filter,
                      exclude_ids=['tvbox-tx2-07','tvbox-e10-01','tvbox-e10-02','tvbox-e10-03'],
                      device='tx2'):
    logger.info(f"Original DataFrame shape: {df.shape}")
    
    # Parse string timestamps to float values
    # df[timecol] = df[timecol].astype(float)
    
    # Convert float timestamps to nanoseconds
    # df[timecol] = df[timecol].apply(lambda x: int(x * 1e9))
    
    # Convert to datetime objects
    df[timecol] = pd.to_datetime(df[timecol], unit='ns', utc=True)
    
    logger.info(f"After datetime conversion, DataFrame shape: {df.shape}")
    
    # Add a flag column to indicate whether each row falls within the specified date range
    df['within_date_range'] = df[timecol].between(start_time_filter, end_time_filter)
    df = df.loc[df[timecol].between(start_time_filter, end_time_filter)]
    
    
    # Remove e10 luis and other excluded IDs
    if exclude_ids is not None:
        df = df[~df['pi-id'].isin(exclude_ids)]
    
    logger.info(f"After ID filtering, DataFrame shape: {df.shape}")
    
    if device == 'tx2':
        df['device_type'] = df['pi-id'].apply(lambda x: 'TX2' if 'tx2' in x else 'other')
    elif device == 'e10':
        df['device_type'] = df['pi-id'].apply(lambda x: 'E10' if 'btv' in x else 'other')
    else:
        df['device_type'] = 'other'
    
    df['model'] = df['pi-id'].apply(lambda x: 'YOLOv8n' if x.endswith('_n') else 'YOLOv10n')
    df['date'] = pd.to_datetime(df[timecol]).dt.date

    logger.info(f"Final DataFrame shape: {df.shape}")
    
    return df

### get data influx

query_api = write_client.query_api()
query = f"""from(bucket: "ic2_parking_twin")
|> range(start: -{days}d)
"""
df_prod = query_api.query_data_frame(query, org="Unicamp")

if not df_prod.empty and len(df_prod) >= 2:
    # Sort by time just to be safe
    df_sorted = df_prod.sort_values("_time")
    # df_sorted.tail(10).to_csv('parking_data.csv',index=False)
    last_time = df_sorted["_time"].iloc[-1]
    second_last_time = df_sorted["_time"].iloc[-2]
    print(last_time,'\n second last:',second_last_time)
    diff = last_time - second_last_time
    
    if diff > pd.Timedelta(minutes=5):
        logger.info(f"⚠️ Gap detected: {diff} between last two timestamps")
    else:
        logger.info('no time diff everything normal')

last_value = df_prod.loc[df_prod["_time"].idxmax(), "_value"]
print(f'last value raw: {last_value}')
binary_str = bin(int(last_value))[2:].zfill(16)
print("Binary occupancy:", binary_str)
car_count = binary_str.count('1')
print(f'car_count is {car_count}')  


# Use UTC for all comparisons to be consistent
utc_timezone = timezone.utc
with open("last_timestamp.txt","w") as f:
    # Use UTC consistently
    original_time = last_time  # This is already in UTC from InfluxDB
    logger.info(f'converted timestamp of last influx is:\n {original_time}')
    
    # Get current time in UTC for consistent comparison
    now_utc = datetime.now(utc_timezone)
    logger.info(f'now is:\n {now_utc} at UTC')
    
    f.write(str(original_time))

### telegram

# Read secrets
def read_token(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        logging.error(f"Token file not found: {file_path}")
        raise

bot_token = read_token('/home/unicamp/photo_collection/telegram_token.txt')
chat_id = ""

# Send Telegram message
def send_message_to_telegram(timestamp, minutes_diff):
    message = (
        f"Pi 3 is not sending data. "
        f"Last data was received {round(minutes_diff, 2)} minutes ago.\n"
        f"Last timestamp: {timestamp}"
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=payload)

    if response.status_code == 200:
        logger.info("Message sent successfully")
    else:
        logger.info(f"Failed to send message: {response.status_code} - {response.text}")
# Track last heartbeat day
last_heartbeat_day = None

def send_message_heartbeat_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, data=payload)

    if response.status_code == 200:
        logger.info("Message sent successfully")
    else:
        logger.info(f"Failed to send message: {response.status_code} - {response.text}")
# Main loop


# Main loop
logger.info("Retrieving timestamp from webpage...")

# Use UTC consistently for both timestamps
timestamp_str = str(original_time).strip()

# Parse the timestamp and ensure it's in UTC
timestamp = pd.to_datetime(timestamp_str).tz_convert('UTC') if pd.notna(pd.to_datetime(timestamp_str)) else None

# Get current time in UTC
now = datetime.now(utc_timezone)

if timestamp is not None:
    # Calculate difference (both in UTC)
    time_diff = now - timestamp
    minutes_diff = time_diff.total_seconds() / 60

    logger.info(f"Timestamp from server: {timestamp}")
    logger.info(f"Now (UTC): {now}")
    # UTC-3 timezone
    utc_minus_3 = timezone(timedelta(hours=-3))
    now_utc_minus_3 = datetime.now(utc_minus_3)

    logger.info(f"Now (UTC-3): {now_utc_minus_3}")
    logger.info(f"Difference: {minutes_diff:.2f} minutes")
    logger.info(f"Difference in seconds: {time_diff.total_seconds()} seconds")

    # logger.info("sending image")

    if minutes_diff > minutes_tolerance:
        logger.info("Timestamp too old — sending alert.")
        # Convert timestamp to local time for display if needed
        local_timestamp = timestamp.astimezone(timezone(timedelta(hours=-3)))
        send_message_to_telegram(local_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z'), minutes_diff)
    else:
        logger.info("Timestamp is within tolerance. Resetting alert counter.")
else:
    logger.error("Failed to parse timestamp")

