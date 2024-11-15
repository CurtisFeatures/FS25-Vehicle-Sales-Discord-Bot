"""
Script Name: DiscordIntigration.py

Description:
    Farming Simulator 2025 Vehicle Sale Monitor
A project to track and display vehicles for sale in Farming Simulator 2025. It includes a web page generator that lists vehicles from both base game and mods, and a Discord bot that posts updates about new or updated vehicles to a channel, including images and specs.

Author: Jamie Curtis
Date Created: 14/11/2024
Last Updated: 15/11/2024
Version: 1.1
GitHub Repository: https://github.com/CurtisFeatures/FS25-Vehicle-Sales-Discord-Bot/
"""


import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
import os
import json
import time
import asyncio

# Set up bot token and channel ID
TOKEN = 'TOKEN_HERE'
CHANNEL_ID = '245652463546345634563456'  # Replace with your Discord channel ID

# Set up image base URL
BASE_URL = 'https://YOUR-DOMAIN-HERE/'  # URL where images are stored

# Set up bot client
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# JSON file to keep track of posted vehicles
POSTED_VEHICLES_FILE = 'posted_vehicles.json'

# Load posted vehicles data
def load_posted_vehicles():
    if os.path.exists(POSTED_VEHICLES_FILE):
        with open(POSTED_VEHICLES_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save posted vehicles data
def save_posted_vehicles(data):
    with open(POSTED_VEHICLES_FILE, 'w') as file:
        json.dump(data, file, indent=4)

# Check if a vehicle should be posted
def should_post(vehicle, posted_vehicles):
    current_time = time.time()
    vehicle_name = vehicle['name']
    
    if vehicle_name not in posted_vehicles:
        return True  # New vehicle

    last_posted = posted_vehicles[vehicle_name]['last_posted']
    last_chance_posted = posted_vehicles[vehicle_name].get('last_chance_posted', False)

    # Check if it's a regular post (24 hours)
    if current_time - last_posted > 86400:
        return True

    # Check if it qualifies as a last chance post and hasn't been posted as one yet
    if vehicle['time_left'] <= 1 and not last_chance_posted:
        return True

    return False

# Function to send the vehicle data to Discord
async def send_vehicle_data(vehicle):
    channel = bot.get_channel(int(CHANNEL_ID))
    image_url = BASE_URL + os.path.basename(vehicle['image'])
    
    # Create an embed to send to Discord
    embed = discord.Embed(title=vehicle['name'], description=vehicle['specs'], color=0x00ff00)
    embed.add_field(name="Price", value=f"£{vehicle['price']}", inline=False)
    embed.add_field(name="Age", value=f"{vehicle['age']} ", inline=True)
    embed.add_field(name="Damage", value=f"{vehicle['damage']}", inline=True)
    embed.add_field(name="Wear", value=f"{vehicle['wear']}", inline=True)
    embed.add_field(name="Operating Time", value=f"{vehicle['operating_time']} ", inline=True)
    embed.add_field(name="Time Left", value=f"{vehicle['time_left_old']} ", inline=True)
    embed.add_field(name="Brand", value=vehicle['brand'], inline=True)
    embed.add_field(name="Category", value=vehicle['category'], inline=True)
    embed.set_image(url=image_url)

    # Send the embed message
    await channel.send(embed=embed)

# Function to parse HTML and extract vehicle data
def parse_html(file_path):
    with open(file_path, 'r', encoding='ISO-8859-1') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    vehicles = []
    vehicle_cards = soup.find_all('div', class_='vehicle-card')
    
    for card in vehicle_cards:
        vehicle = {}
        vehicle['name'] = card.find('div', class_='vehicle-title').text.strip()
        
        details = card.find_all('div', class_='vehicle-details')
        for detail in details:
            text = detail.get_text(strip=True)
            if 'Price' in text:
                vehicle['price'] = text.split('£')[1].strip()
            elif 'Age' in text:
                vehicle['age'] = text.split(':')[1].strip()
            elif 'Damage' in text:
                vehicle['damage'] = text.split(':')[1].strip()
            elif 'Wear' in text:
                vehicle['wear'] = text.split(':')[1].strip()
            elif 'Operating Time' in text:
                vehicle['operating_time'] = text.split(':')[1].strip()
            elif 'Time Left' in text:
                vehicle['time_left_old'] = text.split(':')[1].strip()
            elif 'Brand' in text:
                vehicle['brand'] = text.split(':')[1].strip()
            elif 'Category' in text:
                vehicle['category'] = text.split(':')[1].strip()
            elif 'Specs' in text:
                # Check if there's text after "Specs: "
                if len(text.split('Specs: ')) > 1:
                    vehicle['specs'] = text.split('Specs: ')[1].strip()
                else:
                    vehicle['specs'] = "N/A"  # Assign a default value if Specs is empty

        # Get the new 'time left' value
        time_left_tag = card.find('div', class_='vehicle-detailstime')
        if time_left_tag:
            vehicle['time_left'] = int(time_left_tag.text.strip())  # Convert to integer

        # Get the image source
        image_tag = card.find('img', class_='vehicle-image')
        if image_tag and 'src' in image_tag.attrs:
            vehicle['image'] = image_tag.attrs['src'].split('/')[-1]

        vehicles.append(vehicle)
    
    return vehicles

# Task to run every 60 seconds
@tasks.loop(seconds=60)
async def check_and_post_vehicles():
    posted_vehicles = load_posted_vehicles()
    vehicles = parse_html(r'C:\DiscordBots1\Sales\vehicles_on_sale.html')

    new_items_to_post = False

    for vehicle in vehicles:
        # Check if the vehicle entry exists in JSON; if not, add it before sending
        if should_post(vehicle, posted_vehicles):
            channel = bot.get_channel(int(CHANNEL_ID))

            if vehicle['name'] not in posted_vehicles:
                posted_vehicles[vehicle['name']] = {
                    'last_posted': 0,  # Initially set to 0 to allow first-time posting
                    'last_chance_posted': False
                }

            # Check if this is a last chance item (time left of 1 or less)
            if vehicle.get('time_left', 0) <= 1 and not posted_vehicles[vehicle['name']]['last_chance_posted']:
                await channel.send("LAST CHANCE SALE ITEM")
                posted_vehicles[vehicle['name']]['last_chance_posted'] = True

            # Post "NEW SALE ITEMS" message only once if there are new items
            elif not new_items_to_post:
                new_items_to_post = True
                await channel.send("NEW SALE ITEMS")

            # Post the vehicle details
            await send_vehicle_data(vehicle)

            # Update last posted time and save to JSON
            posted_vehicles[vehicle['name']]['last_posted'] = time.time()
            save_posted_vehicles(posted_vehicles)

# Event to start the loop once the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    check_and_post_vehicles.start()  # Start the loop

# Run the bot
bot.run(TOKEN)
