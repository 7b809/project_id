import json
import time
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os

# MongoDB connection URL
MONGO_URL = os.getenv("MONGO_URL")  # Ensure you have set this environment variable
client = MongoClient(MONGO_URL)
db = client["tmdb_data"]  # Database name
collection = db["tv_shows_links"]  # Collection name

# Function to process the TV shows from the JSON file
def process_tvshows_from_json(json_file_path):
    # Load the data from the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as file:
        tvshows_data = json.load(file)
        tvshows_data = tvshows_data[400:401]  # Processing a specific range for now

    try:
        # Iterate over each TV show in the data
        for tv_show in tvshows_data:
            tv_id = tv_show["id"]
            title = tv_show["title"]
            seasons = tv_show["extra_data"].get("seasons", [])

            print(f"Processing TV show: {title} (ID: {tv_id})")

            # Initialize a dictionary to store TV show data
            tv_show_data = {
                "tv_id": tv_id,
                "title": title,
                "episodes": []
            }

            # Iterate through seasons
            for season in seasons:
                season_number = season["season_number"]
                episode_count = season["episode_count"]

                # Skip season 0
                if season_number < 1:
                    continue

                print(f"  Season {season_number}, Episodes: {episode_count}")

                # Iterate through episodes
                for episode in range(1, episode_count + 1):
                    url = f"https://vidsrcme.vidsrc.icu/embed/tv?tmdb={tv_id}&season={season_number}&episode={episode}&autoplay=1"
                    print(f"    Requesting URL: {url}")

                    try:
                        response = requests.get(url)
                        response.raise_for_status()

                        # Parse the HTML content
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Extract the iframe element (main hash source)
                        iframe_element = soup.find('iframe', id='player_iframe')
                        iframe_src = iframe_element['src'] if iframe_element else None

                        # Extract server hashes
                        server_elements = soup.select(".servers")
                        server_hashes = []

                        for server in server_elements:
                            server_hash = server.get('data-hash')
                            if server_hash:
                                server_hashes.append(server_hash)

                        # Ensure the first hash is the main hash
                        if server_hashes and iframe_src:
                            # Add episode data to TV show data
                            tv_show_data["episodes"].append({
                                f"{season_number}_{episode}": {
                                    "links": server_hashes[0]
                                },
                                "iframe_src": iframe_src,
                            })

                    except Exception as e:
                        print(f"      Failed to load URL {url}: {str(e)}")

                    # Add a small delay between requests
                    time.sleep(2)

            # Insert the TV show's data into MongoDB
            collection.insert_one(tv_show_data)

            print(f"Data for {title} (ID: {tv_id}) saved to MongoDB.")

    except Exception as e:
        print(f"Error during processing: {str(e)}")

# Main Execution
if __name__ == "__main__":
    # Provide the path to the JSON file
    json_file_path = "file.json"
    process_tvshows_from_json(json_file_path)
