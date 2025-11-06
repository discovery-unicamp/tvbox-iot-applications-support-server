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
import matplotlib.pyplot as plt
# import csv
# import ast

# Setup logging
log_file = '/home/unicamp/photo_collection/telegrambot_1hour.log'
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
minutes_tolerance = 200#10
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

days = '30'

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
# Convert each _value to binary string and expand into columns
def expand_to_spots(value, bit_length):
    binary_str = bin(int(value))[2:].zfill(bit_length)
    return list(map(int, binary_str))
query_api = write_client.query_api()
query = f"""from(bucket: "ic2_parking_twin")
|> range(start: -{days}d)
"""
df = query_api.query_data_frame(query, org="Unicamp")

df = preprocess_subset(df,device='e10')



# Ensure datetime and sort
df["_time"] = pd.to_datetime(df["_time"]) - pd.Timedelta(hours=3)
df = df.sort_values("_time")

# Define bit length
BIT_LENGTH = 16


spot_cols = [f"spot_{i+1}" for i in range(BIT_LENGTH)]
df[spot_cols] = df["_value"].apply(lambda v: pd.Series(expand_to_spots(v, BIT_LENGTH)))

# Extract time features
df["date"] = df["_time"].dt.date
df["hour"] = df["_time"].dt.hour
df["minute"] = df["_time"].dt.minute
df["day_of_week"] = df["_time"].dt.day_name()
df["day_of_week_num"] = df["_time"].dt.dayofweek
df["is_weekend"] = df["day_of_week_num"] >= 5  # 5=Saturday, 6=Sunday
df["week_number"] = df["_time"].dt.isocalendar().week
df["year"] = df["_time"].dt.year
df["week_id"] = df["year"].astype(str) + "-W" + df["week_number"].astype(str).str.zfill(2)


# Get recent weeks for comparison
unique_weeks = sorted(df["week_id"].unique())
selected_weeks = unique_weeks[-5:-1]  # Last 4 weeks
week_number =unique_weeks[-1]


# Run all visualizations
print("Generating weekly hour distribution visualizations...")



# Dashboard for comprehensive view
# create_weekly_comparison_dashboard(df,selected_weeks,week_number)


# Get the SECOND last day
unique_dates = sorted(df["date"].unique())
print(f'unique dates: {unique_dates}')
print(f'unique_dates[-2]: {unique_dates[-2]}')
if len(unique_dates) >= 2:
    second_last_date = unique_dates[-2]
    second_last_day_data = df[df["date"] == second_last_date]#.copy()
    second_last_day_name = second_last_day_data["day_of_week"].iloc[0]
    second_last_is_weekend = second_last_day_data["is_weekend"].iloc[0]
else:
    print("Not enough dates for comparison.")
    exit()

print(f"📅 Analyzing occupation for: {second_last_date} ({second_last_day_name})")
print(f"📊 Day type: {'Weekend' if second_last_is_weekend else 'Weekday'}")

# Calculate occupied minutes and hours for the second last day
second_last_day_total_minutes = second_last_day_data[spot_cols].sum()
second_last_day_total_hours = second_last_day_total_minutes / 60

# Get historical data from previous 2 weeks of the same type (weekday/weekend)
historical_data = df[df["date"] < second_last_date]#.copy()

# Filter for same day type (weekday/weekend) from previous 2 weeks
target_weeks = sorted(historical_data["week_number"].unique())[-3:]  # Last 2 weeks, beside this one
# historical_same_type = historical_data[
#     (historical_data["is_weekend"] == second_last_is_weekend) & 
#     (historical_data["week_number"].isin(target_weeks))
# ]

if second_last_is_weekend:
    # Compare only with weekends of last 2 weeks
    historical_same_type = historical_data[
        (historical_data["is_weekend"]) &
        (historical_data["week_number"].isin(target_weeks))
    ]
else:
    # Compare only with weekdays of last 2 weeks
    historical_same_type = historical_data[
        (~historical_data["is_weekend"]) &   # filter out Sat/Sun
        (historical_data["week_number"].isin(target_weeks))
    ]
filtered_unique_dates = sorted(historical_same_type["date"].unique())
print(f'\nfiltered unique dates:\n {filtered_unique_dates}')

# print(f'unique dates: {unique_dates}')
# display(historical_data)
print(f"📈 Comparing with previous {len(target_weeks)} {'weekends' if second_last_is_weekend else 'weekdays'}")

if historical_same_type.empty:
    print("❌ Not enough historical data for comparison")
    exit()

# Calculate historical statistics (daily totals in hours)
historical_daily_totals = historical_same_type.groupby("date")[spot_cols].sum() / 60
historical_means = historical_daily_totals.mean()
historical_stds = historical_daily_totals.std()

# Calculate z-scores
z_scores = (second_last_day_total_hours - historical_means) / historical_stds
z_scores = z_scores.replace([np.inf, -np.inf], np.nan).fillna(0)

# Identify abnormal spots (occupied less than 100 hours OR statistically abnormal)
abnormal_spots = []
for spot in spot_cols:
    spot_num = int(spot.split('_')[1])
    current_hours = second_last_day_total_hours[spot]
    historical_avg = historical_means[spot]
    z_score = z_scores[spot]
    
    # Abnormality condition: less than 100 hours OR statistically abnormal (|z| > 2)
    is_abnormal = (current_hours < 1)#or (abs(z_score) > 2)
    
    if is_abnormal:
        abnormal_spots.append({
            'spot': spot_num,
            'current_hours': current_hours,
            'historical_avg': historical_avg,
            'z_score': z_score,
            'reason': 'Low hours (<1)' if current_hours < 100 else f'Statistical anomaly (z={z_score:.1f})'
        })

# Run the analysis
print(f'second_last_date is:\n {second_last_date}\n')

# create_simplified_histogram(second_last_date,historical_means,second_last_is_weekend,second_last_day_total_hours,second_last_day_name,abnormal_spots)
# print_overall_stats()
total_hours = second_last_day_total_hours.sum()
avg_per_spot = second_last_day_total_hours.mean()
max_spot = second_last_day_total_hours.idxmax()
max_hours = second_last_day_total_hours.max()
min_spot = second_last_day_total_hours.idxmin()
min_hours = second_last_day_total_hours.min()

def print_abnormal_summary():
    if not abnormal_spots:
        print(f"\n✅ ALL SPOTS NORMAL: No spots with <1 hour occupation")
        return True
    
    print(f"\n🚨 ABNORMAL SPOTS DETECTED ({len(abnormal_spots)}):")
    print("=" * 60)
    
    for abnormal in sorted(abnormal_spots, key=lambda x: x['current_hours']):
        deviation = abnormal['current_hours'] - abnormal['historical_avg']
        deviation_pct = (deviation / abnormal['historical_avg'] * 100) if abnormal['historical_avg'] > 0 else 0
        
        print(f"Spot {abnormal['spot']:2d}: {abnormal['current_hours']:6.1f} hours "
            f"(avg: {abnormal['historical_avg']:5.1f}h, "
            f"Δ: {deviation:+.1f}h [{deviation_pct:+.1f}%])")
        print(f"       → {abnormal['reason']}")
        print("-" * 60)
    return False

abnormal = print_abnormal_summary()


def create_quick_status_table():
    status_data = []
    
    for spot in spot_cols:
        spot_num = int(spot.split('_')[1])
        current_hours = second_last_day_total_hours[spot]
        historical_avg = historical_means[spot]
        z_score = z_scores[spot]
        
        status = "NORMAL"
        if current_hours < 1:
            status = "LESS THAN 1 HOUR"
        elif z_score > 2:
            status = "MORE OCCUPIED THAN USUAL"
        elif -z_score > 2:
            status = "STAT. ABNORMAL, LOW OCCUPATION"
        
        status_data.append({
            'Spot': spot_num,
            'Hours': f"{current_hours:.1f}",
            'Hist Avg': f"{historical_avg:.1f}",
            'Z-score': f"{z_score:.1f}",
            'Status': status
        })
    
    status_df = pd.DataFrame(status_data)
    print(f"\n📋 QUICK STATUS TABLE:")
    print(status_df.to_string(index=False))
    return status_df.to_string(index=False)

stats = create_quick_status_table()

with open("status_table.txt", "w") as f:
    # f.write(str(last_value))
    # f.write()
    if abnormal == True:
        f.write(f"\n✅ ALL SPOTS NORMAL: No spots with <1 hour occupation")
    else:
        f.write(f"\n🚨 ABNORMAL SPOTS DETECTED")
    f.write(f"\n📊 OVERALL STATISTICS for {second_last_date}: generated by tv box 2\n")
    f.write("=" * 50)
    f.write(f"\nTotal occupied hours: {total_hours:.1f}\n")
    f.write(f"\nAverage per spot: {avg_per_spot:.1f} hours")
    f.write(f"\nMost occupied: {max_spot} ({max_hours:.1f} hours)")
    f.write(f"\nLeast occupied: {min_spot} ({min_hours:.1f} hours)")
    f.write(f"\nSpots with <1 hour: {sum(second_last_day_total_hours < 100)}")
    f.write(f"\nSpots with statistical anomalies (|z|>2): {sum(abs(z_scores) > 2)}\n")
    f.write(stats)


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

with open("status_table.txt", "r") as f:
    lines = f.read()

send_message_heartbeat_to_telegram(lines)#.text)



