import requests
import time
import sys
import pymongo
import os

# Environment variables for sensitive data (from GitHub Secrets)
API_KEY = os.getenv("TMDB_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
BASE_URL = "https://api.themoviedb.org/3"

# Headers
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json;charset=utf-8"
}

# MongoDB Client
client = pymongo.MongoClient(MONGO_URL)
db = client["tmdb_data"]  # Database name
movies_collection = db["movies_data"]  # Collection for movies
tvshows_collection = db["tvshows_data"]  # Collection for TV shows

# Function to save batch data to MongoDB
def save_to_mongodb(collection, data, batch_size, total_key):
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        collection.insert_one({
            total_key: batch,
            "batch_start": i + 1,
            "batch_end": i + len(batch),
            "timestamp": time.time()
        })
        print(f"Saved batch {i + 1} to {i + len(batch)} to MongoDB collection '{collection.name}'.")

# Function to get movies
def get_movies(page_limit=5, batch_size=18000):
    movies = []
    for page in range(1, page_limit + 1):
        url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            for movie in data['results']:
                movies.append({
                    "id": movie.get("id"),
                    "title": movie.get("title")
                })
                if len(movies) % 100 == 0:  # Print update for every 100 movies
                    sys.stdout.write(f"\rTotal {len(movies)} movie IDs processed.")
                    sys.stdout.flush()
        else:
            print(f"Failed to fetch movies on page {page}. Status code: {response.status_code}")
        time.sleep(0.2)  # Rate limiting
    print(f"\nTotal movie IDs fetched: {len(movies)}. Saving to MongoDB.")
    save_to_mongodb(movies_collection, movies, batch_size, "movies")
    return len(movies)

# Function to get detailed TV show data
def get_tv_show_details(tv_id):
    url = f"{BASE_URL}/tv/{tv_id}?api_key={API_KEY}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        seasons = []
        for season in data.get("seasons", []):
            seasons.append({
                "season_number": season.get("season_number"),
                "episode_count": season.get("episode_count")
            })
        return {
            "total_seasons": len(seasons),
            "seasons": seasons
        }
    else:
        print(f"Failed to fetch details for TV show ID {tv_id}. Status code: {response.status_code}")
        return {
            "total_seasons": 0,
            "seasons": []
        }

# Function to get TV shows
def get_tv_shows(page_limit=5, batch_size=500):
    tv_shows = []
    for page in range(1, page_limit + 1):
        url = f"{BASE_URL}/discover/tv?api_key={API_KEY}&page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            for show in data['results']:
                show_id = show.get("id")
                show_title = show.get("name")
                extra_data = get_tv_show_details(show_id)  # Fetch additional data
                tv_shows.append({
                    "id": show_id,
                    "title": show_title,
                    "extra_data": extra_data
                })
                if len(tv_shows) % 100 == 0:  # Print update for every 100 TV shows
                    sys.stdout.write(f"\rTotal {len(tv_shows)} TV show IDs processed.")
                    sys.stdout.flush()
        else:
            print(f"Failed to fetch TV shows on page {page}. Status code: {response.status_code}")
        time.sleep(0.2)  # Rate limiting
    print(f"\nTotal TV show IDs fetched: {len(tv_shows)}. Saving to MongoDB.")
    save_to_mongodb(tvshows_collection, tv_shows, batch_size, "tv_shows")
    return len(tv_shows)

# Main Execution
if __name__ == "__main__":
    # # Fetch and save TV show data
    # total_tvshows = get_tv_shows(page_limit=9285)  # Adjust page limit as needed

    # Fetch and save movie data
    total_movies = get_movies(page_limit=47135)  # Adjust page limit as needed

    print(f"\nCompleted! Total TV shows: {total_tvshows}, Total Movies: {total_movies}")
