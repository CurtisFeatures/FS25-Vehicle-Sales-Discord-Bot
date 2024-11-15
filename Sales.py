"""
Script Name: Sales.py

Description:
    Farming Simulator 2025 Vehicle Sale Monitor
A project to track and display vehicles for sale in Farming Simulator 2025. It includes a web page generator that lists vehicles from both base game and mods, and a Discord bot that posts updates about new or updated vehicles to a channel, including images and specs.

Author: Jamie Curtis
Date Created: 14/11/2024
Last Updated: 14/11/2024
GitHub Repository: https://github.com/CurtisFeatures/FS25-Vehicle-Sales-Discord-Bot/
"""


import zipfile
import xml.etree.ElementTree as ET
import os
from PIL import Image
import logging

# Define paths
sales_xml_path = r'C:\Users\Administrator\Documents\My Games\FarmingSimulator2025\savegame1\sales.xml'
data_base_path = r'C:\Program Files (x86)\Farming Simulator 2025\data'
mods_base_path = r'C:\Users\Administrator\Documents\My Games\FarmingSimulator2025\mods'
output_html = 'vehicles_on_sale.html'
png_path = r'C:\DiscordBots1\Sales\Images'

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure the output folder exists
os.makedirs(png_path, exist_ok=True)

# Function to convert DDS to PNG
def convert_dds_to_png(dds_path, output_folder):
    try:
        with Image.open(dds_path) as dds_image:
            png_path = os.path.join(output_folder, os.path.basename(dds_path).replace('.dds', '.png'))
            dds_image.save(png_path, 'PNG')
            logging.info(f"Converted DDS to PNG: {png_path}")
            return png_path
    except Exception as e:
        logging.error(f"Error converting DDS to PNG at {dds_path}: {e}")
        return None

# Function to extract DDS from ZIP and convert to PNG
def extract_dds_from_zip(zip_ref, dds_filename, output_folder):
    try:
        logging.info(f"Checking for DDS file: {dds_filename} inside ZIP")
        
        # Check if the DDS filename exists in the zip contents
        zip_contents = zip_ref.namelist()
        logging.info(f"ZIP contains the following files: {zip_contents}")
        
        if dds_filename in zip_contents:
            zip_ref.extract(dds_filename, output_folder)
            dds_path = os.path.join(output_folder, dds_filename)
            logging.info(f"Extracted DDS file {dds_filename} to {dds_path}")
            return convert_dds_to_png(dds_path, output_folder)
        else:
            logging.warning(f"DDS file {dds_filename} not found inside ZIP.")
            return None
    except Exception as e:
        logging.error(f"Error extracting DDS from ZIP: {e}")
        return None


# Function to locate and parse a referenced XML file from ZIP or normal path
def parse_vehicle_details(xml_filename, output_folder):
    if xml_filename.startswith('$moddir$'):
        # Remove the $moddir$ placeholder from the filename
        xml_filename = xml_filename.replace('$moddir$', '').strip()
        
        mod_folder = xml_filename.split('/')[0]  # Get the mod folder name (this part is after "$moddir$")
        xml_filename_cleaned = xml_filename.split('/')[1]  # Now we have the correct file name (e.g., series7810.xml)
        
        # Construct the path to the mod ZIP file
        mod_file_path = os.path.join(mods_base_path, mod_folder + '.zip')
        
        if os.path.exists(mod_file_path):
            logging.info(f"Reading from ZIP file: {mod_file_path}")
            
            try:
                with zipfile.ZipFile(mod_file_path, 'r') as zip_ref:
                    zip_contents = zip_ref.namelist()
                    logging.info(f"Contents of ZIP: {zip_contents}")
                    
                    # Look for the cleaned XML file name (series7810.xml) in the ZIP contents
                    if xml_filename_cleaned in zip_contents:
                        with zip_ref.open(xml_filename_cleaned) as xml_file:
                            vehicle_tree = ET.parse(xml_file)
                            vehicle_root = vehicle_tree.getroot()

                            # Check if there is a DDS file in the ZIP that should be converted
                            image_path = extract_dds_from_zip(zip_ref, 'store_series7810.dds', output_folder)
                            if image_path:
                                logging.info(f"Image extracted and converted: {image_path}")
                            else:
                                logging.warning(f"No image extracted for {xml_filename_cleaned}.")

                            return extract_vehicle_details_from_xml(vehicle_root, output_folder, mod_file_path, zip_ref)
                    else:
                        logging.error(f"XML file {xml_filename_cleaned} not found in {mod_file_path}")
            except Exception as e:
                logging.error(f"Error reading from ZIP file {mod_file_path}: {e}")
        else:
            logging.error(f"Mod file {mod_file_path} not found.")
    elif xml_filename.startswith('data/'):
        file_path = os.path.join(data_base_path, xml_filename[5:])
        if os.path.exists(file_path):
            vehicle_tree = ET.parse(file_path)
            vehicle_root = vehicle_tree.getroot()
            return extract_vehicle_details_from_xml(vehicle_root, output_folder, file_path)
    return None

# Function to extract vehicle details from XML
def extract_vehicle_details_from_xml(vehicle_root, output_folder, file_path, zip_ref=None):
    store_data = vehicle_root.find('storeData')
    name = store_data.findtext('name', 'Unknown') if store_data is not None else 'Unknown'

    # Check if <specs> exists in the current XML and format them
    specs = ""
    if store_data is not None and store_data.find('specs') is not None:
        specs = store_data.find('specs')
        specs = " ".join([f"{spec.tag}: {spec.text}" for spec in specs])

    # Extract brand and category from storeData
    brand = store_data.findtext('brand', 'Unknown') if store_data is not None else 'Unknown'
    category = store_data.findtext('category', 'Unknown') if store_data is not None else 'Unknown'

    # Get the image path
    image_path = store_data.findtext('image', '')
    
    if image_path:
        # Handle image path correctly based on its prefix (e.g., $data, data, Mods)
        if image_path.startswith('$data/'):
            image_path = image_path.replace('$data/', '')  # Remove $data/
            image_path = os.path.join(data_base_path, image_path)  # Add base path
        
        elif image_path.startswith('data/'):
            image_path = image_path[5:]  # Remove the 'data/' part
            image_path = os.path.join(data_base_path, image_path)  # Add base path
        
        elif image_path.startswith('Mods/'):
            image_path = image_path[5:]  # Remove 'Mods/'
            image_path = os.path.join(mods_base_path, image_path)  # Add mods base path
        
        # Handle possible DDS to PNG conversion
        png_image_path = image_path.replace('.dds', '.png')
        if not os.path.exists(png_image_path):
            dds_image_path = image_path.replace('.png', '.dds')
            if os.path.exists(dds_image_path):
                logging.info(f"Found DDS image: {dds_image_path}")
                png_image_path = convert_dds_to_png(dds_image_path, output_folder)
                if png_image_path:
                    image_path = png_image_path
                else:
                    logging.warning(f"Failed to convert DDS to PNG for {dds_image_path}")
            else:
                logging.warning(f"DDS file not found: {dds_image_path}")
        else:
            logging.info(f"PNG image already exists: {png_image_path}")

    # Return details as a dictionary
    return {
        'name': name,
        'specs': specs,
        'brand': brand,
        'category': category,
        'image': image_path,
        'file_path': file_path
    }




# Parse the sales XML file
tree = ET.parse(sales_xml_path)
root = tree.getroot()

# Start HTML content
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vehicles on Sale</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .vehicle-card { border: 1px solid #ccc; padding: 10px; margin: 10px; }
        .vehicle-title { font-size: 1.2em; font-weight: bold; }
        .vehicle-details { margin-top: 5px; }
        .vehicle-image { width: 100px; height: auto; }
    </style>
</head>
<body>

<h1>Vehicles on Sale</h1>
<div id="vehicleContainer">
"""

# Process each item in the sales XML
for item in root.findall('item'):
    filename = item.get('xmlFilename')
    price = item.get('price')
    age = item.get('age')
    damage = item.get('damage')
    wear = item.get('wear')
    time_left = item.get('timeLeft')
    operating_time_minutes = float(item.get('operatingTime', 0))
    operating_time_hours = round(operating_time_minutes / 60, 1)

    vehicle_details = parse_vehicle_details(filename, output_folder=png_path)
    name = vehicle_details['name'] if vehicle_details else 'Unknown Vehicle'
    specs = vehicle_details['specs'] if vehicle_details else ''
    brand = vehicle_details['brand'] if vehicle_details else 'Unknown Brand'
    category = vehicle_details['category'] if vehicle_details else 'Unknown Category'
    image_path = vehicle_details['image'] if vehicle_details else ''
    file_path = vehicle_details['file_path'] if vehicle_details else 'File not found'

    if vehicle_details:
        html_content += f"""
        <div class="vehicle-card">
            <div class="vehicle-title">{vehicle_details['name']}</div>
            <div class="vehicle-details">Price: £{float(price):,.2f}</div>
            <div class="vehicle-details">Age: {age} years</div>
            <div class="vehicle-details">Damage: {float(damage) * 100:.1f}%</div>
            <div class="vehicle-details">Wear: {float(wear) * 100:.1f}%</div>
            <div class="vehicle-details">Operating Time: {operating_time_hours} hours</div>
            <div class="vehicle-details">Time Left: {time_left} hours</div>
        <div class="vehicle-detailstime">{time_left}</div>
            <div class="vehicle-details">Brand: {vehicle_details['brand']}</div>
            <div class="vehicle-details">Category: {vehicle_details['category']}</div>
            <div class="vehicle-details">Specs: {vehicle_details['specs']}</div>
            <div class="vehicle-details">
                <a href="https://YOUR-DOMAIN-HERE/{os.path.basename(vehicle_details['image'])}" target="_blank">
            <img src="{os.path.join(png_path, os.path.basename(vehicle_details['image']))}" alt="{vehicle_details['name']} image" class="vehicle-image" />
        </a>
            </div>
        </div>
        """

# Close HTML tags
html_content += """
</div>
</body>
</html>
"""

# Save HTML to file
with open(output_html, 'w') as f:
    f.write(html_content)

logging.info(f"HTML file generated successfully at {output_html}")
