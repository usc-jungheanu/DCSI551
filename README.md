TuneSync: Your Personalized Music Dashboard Overview

TuneSync is a Streamlit-based web application that allows users to manage playlists, explore music genres, and interact with Spotify’s rich database of music. It offers features such as user authentication, playlist management, and music analytics based on mood and genre.
 
Features:
User Authentication: Secure login and signup functionalities with hashed password storage.
Music Search: Integrated search functionality with Spotify to explore new and top hits.
Playlist Management: Users can create, view, and delete playlists.
Mood Analysis: Analyze the mood of songs in a playlist using Spotify’s audio features.

Prerequisites:
Python 3.6 or higher
MySQL Server
Spotify API credentials

Installation:
Clone the repository to your local machine:
 

git clone https://github.com/yourusername/tunesync.git
cd tunesync

Install the required Python packages:
pip install -r requirements.txt

Configuration:
Create a .env file in the project root directory and update it with your MySQL and Spotify API credentials:
 
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

Running the Application
To run the app, execute the following command in the terminal:
 
streamlit run app.py

This will start the Streamlit server, and you should be able to access the web application by navigating to http://localhost:8501 in your web browser.
 
App Structure:

app.py: The main Python script to run the Streamlit app.

modules: Contains Python scripts for different functionalities (authentication, database operations, Spotify API integration).


Database Schema:
Refer to schema.sql for details on the database schema used for user and playlist management.
  
Project Link: https://github.com/usc-jungheanu/DSCI551
