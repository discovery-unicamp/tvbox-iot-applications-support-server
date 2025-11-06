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
log_file = '/home/unicamp/photo_collection/telegrambot_1day.log'
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



def send_image_url_to_telegram(image_source, caption=""):
    """Send an image to Telegram chat - accepts both local file paths and URLs"""
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    if image_source.startswith(('http://', 'https://')):
        # It's a URL
        payload = {
            'chat_id': chat_id,
            'photo': image_source,
            'caption': caption
        }
        response = requests.post(url, data=payload)
    else:
        # It's a local file
        with open(image_source, 'rb') as image_file:
            files = {'photo': image_file}
            data = {'chat_id': chat_id, 'caption': caption}
            response = requests.post(url, files=files, data=data)
    
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

days = '40'

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
# Convert each _value to binary string and expand into columns
def expand_to_spots(value, bit_length):
    binary_str = bin(int(value))[2:].zfill(bit_length)
    return list(map(int, binary_str))
### get data influx

query_api = write_client.query_api()
query = f"""from(bucket: "ic2_parking_twin")
|> range(start: -{days}d)
"""
df = query_api.query_data_frame(query, org="")

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
logger.info(f'selected weeks: {selected_weeks}')
week_number =unique_weeks[-1]
today_date = datetime.now().strftime("%Y-%m-%d")  # or "%d/%m/%Y" if you prefer

# Run all visualizations
print("Generating weekly hour distribution visualizations...")

def create_weekly_comparison_dashboard(df,selected_weeks,week_number):
    print(f'\n\ndashboard is running\n\n')
    fig = plt.figure(figsize=(18, 12))
    
    # Plot 1: Weekly total hours heatmap (CORRECTED)
    weekly_totals_minutes = df[df["week_id"].isin(selected_weeks)].groupby("week_id")[spot_cols].sum().sum(axis=1)
    weekly_totals_hours = weekly_totals_minutes / 60  # Convert to hours
    
    ax1 = plt.subplot2grid((2, 2), (0, 0))
    weekly_totals_hours.plot(kind='bar', ax=ax1, color='steelblue', alpha=0.8)
    ax1.set_title('Total Occupied Hours by Week', fontweight='bold')
    ax1.set_ylabel('Total Hours')
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Hourly distribution across weeks (CORRECTED)
    ax2 = plt.subplot2grid((2, 2), (0, 1))
    hourly_totals_minutes = df[df["week_id"].isin(selected_weeks)].groupby(["week_id", "hour"])[spot_cols].sum().sum(axis=1)
    hourly_totals_hours = hourly_totals_minutes / 60  # Convert to hours
    hourly_totals_hours = hourly_totals_hours.reset_index()
    
    for week in selected_weeks:
        week_data = hourly_totals_hours[hourly_totals_hours["week_id"] == week]
        ax2.plot(week_data["hour"], week_data[0], label=week, marker='o', linewidth=2)
    
    ax2.set_title('Hourly Occupation Patterns by Week', fontweight='bold')
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Total Occupied Hours')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Grouped spot weekly bars (REPLACED)
    ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=2)
    
    # Calculate total occupied HOURS for each spot and week
    spot_weekly_minutes = df[df["week_id"].isin(selected_weeks)].groupby(["week_id"])[spot_cols].sum()
    spot_weekly_hours = spot_weekly_minutes / 60  # Convert to hours
    
    # Transpose and reset index
    plot_data = spot_weekly_hours.T.reset_index()
    plot_data["spot_num"] = plot_data["index"].str.extract('(\d+)').astype(int)
    plot_data = plot_data.sort_values("spot_num")
    
    bar_width = 0.2
    x_pos = np.arange(BIT_LENGTH)
    
    for i, week in enumerate(selected_weeks):
        ax3.bar(x_pos + i * bar_width, plot_data[week], 
               width=bar_width, label=week, alpha=0.8)
    
    ax3.set_xlabel('Parking Spot')
    ax3.set_ylabel('Total Occupied Hours')
    ax3.set_title('Total Occupied Hours per Spot - Weekly Comparison', 
                fontsize=14, fontweight='bold')
    ax3.set_xticks(x_pos + bar_width * (len(selected_weeks)-1)/2)
    ax3.set_xticklabels([f'Spot {i+1}' for i in range(BIT_LENGTH)])
    ax3.legend(title='Week')
    ax3.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    
    # plt.suptitle('Weekly Occupation Analysis Dashboard', fontsize=16, fontweight='bold')
    plt.suptitle(f'Weekly Occupation Analysis Dashboard: {week_number}, Generated {today_date} by tv box 2', fontsize=16, fontweight='bold')#,y=1.05)
    plt.savefig('/home/unicamp/photo_collection/weekly_occupation_dashboard.png')
    plt.tight_layout()
    # plt.show()
    plt.close()


# Dashboard for comprehensive view
create_weekly_comparison_dashboard(df,selected_weeks,week_number)



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

send_image_url_to_telegram('/home/unicamp/photo_collection/weekly_occupation_dashboard.png')

