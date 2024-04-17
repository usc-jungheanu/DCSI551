import streamlit as st
from streamlit_option_menu import option_menu
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
import bcrypt
import uuid
from streamlit_modal import Modal
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import concurrent.futures
from collections import defaultdict
import hashlib
import random
import streamlit.components.v1 as components
from PIL import Image
import altair as alt
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.preprocessing import normalize


if 'sql_command' not in st.session_state:
    st.session_state['sql_command'] = ""


def modify_song(song_id):
    # Set the session state flag for this specific song to True
    st.session_state[f'modify_{song_id}'] = True


##################   DATABASE SETUP & MANAGEMENT   ########################


# MySQL Connection for DB1 "TuneSyncAdmin":
def connect_to_mysql_db1():
    try:
        db1_connection = mysql.connector.connect(
            host="database-1.cj26uo6s41hg.us-west-2.rds.amazonaws.com", 
            user="admin",
            password="RusticRatio60090",
            database="TuneSyncAdmin",  
            port= 3306
        )
        if db1_connection.is_connected():
            # st.write("Successfully connected to MySQL database DB1")
            # You can perform database operations here using db1_connection
            return db1_connection
    except mysql.connector.Error as e:
        # st.write(f"Error connecting to MySQL database DB1: {e}")
        return None
    

# MySQL Connection for DB2 "TuneSyncCustomers":
def connect_to_mysql_db2():
    try:
        db2_connection = mysql.connector.connect(
            host="database-1.cj26uo6s41hg.us-west-2.rds.amazonaws.com", 
            user="admin",
            password="RusticRatio60090",
            database="TuneSyncCustomers",  
            port= 3306
        )
        if db2_connection.is_connected():
            # st.write("Successfully connected to MySQL database DB2")
            # You can perform database operations here using db1_connection
            return db2_connection
    except mysql.connector.Error as e:
        st.write(f"Error connecting to MySQL database DB2: {e}")
        return None
    
# Ensure to close the MySQL connections when done
def close_mysql_connection(connection):
    if connection is not None and connection.is_connected():
        connection.close()
        # st.write("MySQL connection is closed")

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def hash_email(email):
    if '@' in email:
        _, domain = email.split('@', 1)
        domain = domain.lower()  # Normalize the domain to lowercase for consistency
        hasher = hashlib.sha256()
        hasher.update(domain.encode('utf-8'))
        domain_hash_hex = hasher.hexdigest()
        tunesync_hash_hex = hashlib.sha256('tunesync.com'.encode('utf-8')).hexdigest()
        if domain_hash_hex == tunesync_hash_hex:
            return 'db1'
        else:
            return 'db2'
    else:
        return None  # Handle the case where the email format is incorrect


# # Function to insert a new user into the correct database based on their email domain
# def insert_user(username, password, email):
#     hashed_password = hash_password(password).decode('utf-8')  # Make sure to hash the password
#     usertype = "admin" if email.endswith("@tunesync.com") else "customer"

#     # Decide which database to use based on email domain
#     db_connection = connect_to_mysql_db1() if usertype == "admin" else connect_to_mysql_db2()
    
#     if db_connection is not None:
#         try:
#             cursor = db_connection.cursor()
#             insert_query = """
#                 INSERT INTO users (username, password, email, usertype, created_at)
#                 VALUES (%s, %s, %s, %s, NOW())
#             """
#             # Execute the insert operation
#             cursor.execute(insert_query, (username, hashed_password, email, usertype))
#             db_connection.commit()  # Don't forget to commit the transaction
#             print(f"User created successfully as {usertype}")  # Or use st.success() if using Streamlit
#         except mysql.connector.Error as e:
#             print(f"Error inserting user into database: {e}")  # Or use st.error()
#         finally:
#             cursor.close()
#             db_connection.close()


def insert_user(username, password, email):
    hashed_password = hash_password(password).decode('utf-8')  # Make sure to hash the password
    database_key = hash_email(email)

    if database_key == 'db1':
        db_connection = connect_to_mysql_db1()
    elif database_key == 'db2':
        db_connection = connect_to_mysql_db2()
    else:
        return False, "Invalid email format."

    if db_connection is not None:
        try:
            cursor = db_connection.cursor()
            insert_query = """
                INSERT INTO users (username, password, email, usertype, created_at)
                VALUES (%s, %s, %s, 'customer', NOW())
            """
            cursor.execute(insert_query, (username, hashed_password, email))
            db_connection.commit()
            return True, "User created successfully."
        except mysql.connector.Error as e:
            return False, f"Error inserting user into database: {e}"
        finally:
            cursor.close()
            db_connection.close()
    else:
        return False, "Database connection failed."


# # authenticate user for password reset / forgot password
# def authenticate_user(username, password):
#     for db_connection in [connect_to_mysql_db1(), connect_to_mysql_db2()]:
#         if db_connection:
#             try:
#                 cursor = db_connection.cursor()
#                 cursor.execute("SELECT password, usertype FROM users WHERE username = %s", (username,))
#                 result = cursor.fetchone()
#                 if result:
#                     stored_password, usertype = result
#                     stored_password = stored_password.encode('utf-8')
#                     if bcrypt.checkpw(password.encode('utf-8'), stored_password):
#                         return True, usertype  # Authentication successful, return True and usertype
#                     else:
#                         print(f"Password mismatch for user {username}.")
#                 else:
#                     print(f"No password found for user {username}.")
#             except mysql.connector.Error as e:
#                 print(f"Database error during authentication for user {username}: {e}")
#             finally:
#                 cursor.close()
#                 db_connection.close()
#     print(f"User {username} not found in any database.")
#     return False, None  # Authentication failed, return False and None for usertype

def authenticate_user(username, password):
    for db_connection in [connect_to_mysql_db1(), connect_to_mysql_db2()]:
        if db_connection:
            try:
                cursor = db_connection.cursor()
                cursor.execute("SELECT password, usertype FROM users WHERE username = %s", (username,))
                result = cursor.fetchone()
                if result:
                    stored_password, usertype = result
                    stored_password = stored_password.encode('utf-8')
                    if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                        return True, usertype  # Authentication successful, return True and usertype
                    else:
                        print(f"Password mismatch for user {username}.")
                else:
                    print(f"No password found for user {username}.")
            except mysql.connector.Error as e:
                print(f"Database error during authentication for user {username}: {e}")
            finally:
                cursor.close()
                db_connection.close()
    print(f"User {username} not found in any database.")
    return False, None  # Authentication failed, return False and None for usertype



def user_exists(username):
    for db_connection in [connect_to_mysql_db1(), connect_to_mysql_db2()]:
        if db_connection is not None:
            try:
                cursor = db_connection.cursor()
                cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE username = %s)", (username,))
                exists = cursor.fetchone()[0]
                if exists:
                    return True
            except mysql.connector.Error as e:
                print(f"Error checking user existence: {e}")
            finally:
                cursor.close()
                db_connection.close()
    return False

def send_password_reset_request(username):
    if user_exists(username):  # Using the above function to check existence
        for db_connection in [connect_to_mysql_db1(), connect_to_mysql_db2()]:
            if db_connection is not None:
                try:
                    cursor = db_connection.cursor()
                    cursor.execute("SELECT email FROM users WHERE username = %s", (username,))
                    result = cursor.fetchone()
                    if result:
                        email = result[0]
                        reset_link = f"http://your-app-url/reset_password?user={username}"
                        send_password_reset_email(email, reset_link)
                        return True
                except mysql.connector.Error as e:
                    print(f"Database error during password reset: {e}")
                finally:
                    cursor.close()
                    db_connection.close()
    else:
        print("Username does not exist.")
    return False

def update_user_password(username, new_password):
    hashed_password = hash_password(new_password).decode('utf-8')
    for db_connection in [connect_to_mysql_db1(), connect_to_mysql_db2()]:
        if db_connection is not None:
            try:
                cursor = db_connection.cursor()
                update_query = "UPDATE users SET password = %s WHERE username = %s"
                cursor.execute(update_query, (hashed_password, username))
                db_connection.commit()
                return True
            except mysql.connector.Error as e:
                print(f"Database error: {e}")
            finally:
                cursor.close()
                db_connection.close()
    return False


# def fetch_user_info(username):
#     """ Fetch user information from the database. """
#     connection = connect_to_mysql_db2()  # Assuming this function connects to your database
#     if connection is not None:
#         try:
#             cursor = connection.cursor()
#             cursor.execute("SELECT user_id, username, email, usertype, created_at FROM users WHERE username = %s", (username,))
#             user_info = cursor.fetchone()
#             if user_info:
#                 return {
#                     "user_id": user_info[0],
#                     "username": user_info[1],
#                     "email": user_info[2],
#                     "usertype": user_info[3],
#                     "created_at": user_info[4]
#                 }
#         except mysql.connector.Error as e:
#             st.error("Error fetching user info: {}".format(e))
#         finally:
#             cursor.close()
#             connection.close()
#     return None


def fetch_user_info_from_db(connection, username):
    if connection is not None:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT user_id, username, email, usertype, created_at FROM users WHERE username = %s", (username,))
            user_info = cursor.fetchone()
            if user_info:
                return {
                    "user_id": user_info[0],
                    "username": user_info[1],
                    "email": user_info[2],
                    "usertype": user_info[3],
                    "created_at": user_info[4]
                }
        except mysql.connector.Error as e:
            st.error("Database error when fetching user info: {}".format(e))
        finally:
            cursor.close()
            connection.close()
    return None


# def fetch_user_info(username):
#     """ Fetch user information from the appropriate database. """
#     # First check in db1
#     connection = connect_to_mysql_db1()
#     user_info = fetch_user_info_from_db(connection, username)
#     if user_info is not None:
#         return user_info
    
#     # If not found in db1, check in db2
#     connection = connect_to_mysql_db2()
#     return fetch_user_info_from_db(connection, username)

def fetch_user_info(username):
    if not username:  # Check if username is None or empty
        return None  # Return None to indicate no user info could be fetched

    # Define a list of database connections to iterate through
    db_connections = [connect_to_mysql_db1(), connect_to_mysql_db2()]

    for db_connection in db_connections:
        if db_connection:
            try:
                cursor = db_connection.cursor()
                query = "SELECT user_id, username, email, usertype, created_at FROM users WHERE username = %s"
                print("Executing query:", query)
                cursor.execute(query, (username,))
                result = cursor.fetchone()
                if result:
                    user_info = {
                        'user_id': result[0],  # Make sure to include user_id in your result fetch
                        'username': result[1],
                        'email': result[2],
                        'usertype': result[3],
                        'created_at': result[4]
                    }
                    print("User info fetched successfully:", user_info)
                    return user_info
                else:
                    print("No user found with username:", username)
            except mysql.connector.Error as e:
                print(f"Database error when fetching user info: {e}")
            finally:
                cursor.close()
                db_connection.close()
        else:
            print("Failed to connect to database.")
    
    print("Failed to retrieve user details for username:", username)
    return None


def show_profile():
    """ Show user profile information. """
    username = st.session_state['user_info']['username'] if st.session_state['user_info'] else 'Username'
    user_info = fetch_user_info(username)

    if user_info:
        st.markdown("### Profile Information")
        st.markdown("----")
        
        # Displaying user information
        st.subheader(f"Username: {user_info['username']}")
        st.text(f"Email: {user_info['email']}")
        st.text(f"Account Type: {user_info['usertype']}")
        st.text(f"User ID: {user_info['user_id']}")
        st.text(f"Created On: {user_info['created_at']}")

    else:
        st.error("Failed to retrieve user details.")



# Setup email exchange for pw reset/ etc
def send_password_reset_email(recipient_email, reset_link):
    sender_email = "support@tunesync.com"
    app_password = "ktis exxb yhoq ltqs"  # Use the App Password you generated earlier
    
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Password Reset Request"
    
    body = f"Please click the following link to reset your password: {reset_link}"
    msg.attach(MIMEText(body, 'plain'))
    
    # Send the email via Gmail's SMTP server
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, app_password)
        server.send_message(msg)
    
    print(f"Password change confirmation email sent to {recipient_email}")


############### ADMIN MANAGEMENT ###############################

def manage_playlists_and_users():
    # st.header("Admin Dashboard")
    selected = option_menu(
        menu_title="Admin Operations",
        options=["Manage Playlists", "Manage Users"],
        icons=["music-note-list", "person-fill"],
        orientation="horizontal",
    )

    if selected == "Manage Playlists":
        manage_playlists()
    elif selected == "Manage Users":
        manage_users()

def manage_playlists():
    tab1, tab2 = st.tabs(["Customers", "Admins"])
    with tab1:
        playlist_crud("customer")
    with tab2:
        playlist_crud("admin")

def manage_users():
    tab1, tab2 = st.tabs(["Customers", "Admins"])
    with tab1:
        user_crud("customer")
    with tab2:
        user_crud("admin")


def playlist_crud(user_type):
    st.subheader(f"Manage Playlists for {user_type.title()}s")
    users = fetch_users_by_type(user_type)  # Fetch users by type (customer or admin)
    user_options = [(user['username'], user['user_id']) for user in users]
    selected_user = st.selectbox('Select User', user_options, format_func=lambda x: x[0])

    if selected_user:
        user_id = selected_user[1]  # Get the user ID from the selection
        playlists = fetch_playlists_by_user(user_id)  # Fetch playlists for selected user

        operation = st.selectbox('Choose operation', ['Create', 'View', 'Delete'], key=f"{user_type}_operation")

        if operation == 'Create':
            playlist_name = st.text_input('Playlist Name', key=f"{user_type}_create_playlist_name")
            if st.button('Create Playlist', key=f"{user_type}_create_playlist_button"):
                create_result, sql_command = create_playlist(playlist_name, user_id, user_type)
                if create_result:
                    st.success('Playlist created!')
                    with st.expander("See SQL Command"):
                        st.code(sql_command)
                else:
                    st.error("Failed to create playlist.")

        elif operation == 'View':
            if playlists:
                df = pd.DataFrame(playlists, columns=['Playlist ID', 'Playlist Name'])
                st.write(df.to_html(index=False, escape=False), unsafe_allow_html=True)  # Display dataframe without index
            else:
                st.write("No playlists found.")

        elif operation == 'Delete':
            playlist_options = [(p[1], p[0]) for p in playlists]  # Assuming p[1] is playlist name and p[0] is playlist ID
            selected_playlist = st.selectbox(
                'Select Playlist to Delete',
                playlist_options,
                format_func=lambda x: x[0],
                key=f"{user_type}_delete_playlist_select_{selected_user[1]}"  # unique key using user_type and user_id
            )
            if st.button('Delete Playlist', key=f"{user_type}_delete_playlist_button_{selected_user[1]}"):
                delete_result, sql_command = delete_playlist(selected_playlist[1])  # Assuming selected_playlist[1] has the playlist ID
                if delete_result:
                    st.success('Playlist deleted!')
                    with st.expander("See SQL Command"):
                        st.code(sql_command)
                else:
                    st.error("Failed to delete playlist.")

def fetch_users_by_type(user_type):
    if user_type == "admin":
        return fetch_users_from_db1()  # Fetch from Admin database
    else:
        return fetch_users_from_db2() 


def fetch_users_from_db1():
    """Fetch users from the admin database."""
    db_connection = connect_to_mysql_db1()
    if db_connection:
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT user_id, username FROM users")  # Adjust the query based on your table structure
            users = [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]
            return users
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            db_connection.close()
    else:
        st.error("Failed to connect to the admin database.")
    return []

def fetch_users_from_db2():
    """Fetch users from the customer database."""
    db_connection = connect_to_mysql_db2()
    if db_connection:
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT user_id, username FROM users")  # Adjust the query based on your table structure
            users = [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]
            return users
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            db_connection.close()
    else:
        st.error("Failed to connect to the customer database.")
    return []




def user_crud(user_type):
    st.subheader("Manage Users")
    option = st.selectbox("Select Operation", ["Create", "View", "Update", "Delete"])

    if option == "Create":
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type='password')
        if st.button("Create User"):
            with st.spinner("Creating User..."):
                create_user(username, email, password)
                st.success(f"User '{username}' created!")

    elif option == "View":
        with st.spinner("Fetching Users..."):
            users = fetch_users()
            st.write(pd.DataFrame(users, columns=['User ID', 'Username', 'Email', 'Role']))

    elif option == "Update":
        user_id = st.text_input("User ID to Update")
        new_email = st.text_input("New Email")
        if st.button("Update User"):
            with st.spinner("Updating User..."):
                update_user(user_id, new_email)
                st.success(f"User ID {user_id} updated!")

    elif option == "Delete":
        user_id = st.text_input("User ID to Delete")
        if st.button("Delete User"):
            with st.spinner("Deleting User..."):
                delete_user(user_id)
                st.success(f"User ID {user_id} deleted!")


def fetch_all_users():
    db_connection = connect_to_mysql_db1()  # Assuming admin operations are in DB1
    if db_connection:
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT user_id, username FROM users")
            users = cursor.fetchall()
            return users  # Returns a list of tuples (user_id, username)
        except mysql.connector.Error as e:
            print(f"Error fetching users: {e}")
        finally:
            cursor.close()
            db_connection.close()
    return []


def create_admin_playlist(playlist_name, user_id):
    db_connection = connect_to_mysql_db1()  # Assuming DB connection function
    try:
        cursor = db_connection.cursor()
        insert_query = "INSERT INTO playlists (playlist_name, user_id) VALUES (%s, %s)"
        cursor.execute(insert_query, (playlist_name, user_id))
        db_connection.commit()
        return True, cursor.statement  # Return success and the SQL command
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False, ""  # Return failure and empty SQL command
    finally:
        cursor.close()
        db_connection.close()


def fetch_playlists_by_user(user_id):
    playlists = []  # Initialize an empty list to store playlists from both databases

    # Fetch from the first database (e.g., Admin DB)
    db_connection = connect_to_mysql_db1()
    playlists += fetch_playlists_for_user(db_connection, user_id)

    # Fetch from the second database (e.g., Customer DB)
    db_connection = connect_to_mysql_db2()
    playlists += fetch_playlists_for_user(db_connection, user_id)

    return playlists


def fetch_playlists_for_user(db_connection, user_id):
    if db_connection:
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT playlist_id, playlist_name FROM playlists WHERE user_id = %s", (user_id,))
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Database error in {db_connection.database}: {e}")
            return []
        finally:
            cursor.close()
            db_connection.close()
    else:
        return []




def fetch_admin_playlists(db_connection):
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT playlist_id, playlist_name FROM playlists")
        playlists = cursor.fetchall()
        return playlists  # This will return a list of tuples (playlist_id, playlist_name)
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return []  # Return an empty list on error
    finally:
        cursor.close()

def delete_admin_playlist(playlist_id):
    db_connection = connect_to_mysql_db1()
    try:
        cursor = db_connection.cursor()
        delete_query = "DELETE FROM playlists WHERE playlist_id = %s"
        cursor.execute(delete_query, (playlist_id,))
        db_connection.commit()
        return cursor.rowcount > 0, cursor.statement  # Return success/failure and the SQL command
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False, ""  # Return failure and empty SQL command
    finally:
        cursor.close()
        db_connection.close()

def create_user(username, email, password, db_connection):
    try:
        cursor = db_connection.cursor()
        hashed_password = hash_password(password).decode('utf-8')
        insert_query = "INSERT INTO users (username, password, email, created_at) VALUES (%s, %s, %s, NOW())"
        cursor.execute(insert_query, (username, hashed_password, email))
        db_connection.commit()
        st.success("User created successfully!")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()

def fetch_users(db_connection):
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT user_id, username, email, usertype FROM users")
        users = cursor.fetchall()
        return users  # Returns a list of tuples with all user fields
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return []
    finally:
        cursor.close()

def update_user(user_id, email, db_connection):
    try:
        cursor = db_connection.cursor()
        update_query = "UPDATE users SET email = %s WHERE user_id = %s"
        cursor.execute(update_query, (email, user_id))
        db_connection.commit()
        if cursor.rowcount > 0:
            st.success("User updated successfully!")
        else:
            st.warning("No user found with the provided ID.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()

def delete_user(user_id, db_connection):
    try:
        cursor = db_connection.cursor()
        delete_query = "DELETE FROM users WHERE user_id = %s"
        cursor.execute(delete_query, (user_id,))
        db_connection.commit()
        if cursor.rowcount > 0:
            st.success("User deleted successfully!")
        else:
            st.warning("No user found with the provided ID.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()


######## SPOTIFY API CONFIGURATION AND SEARCH FUNCTION IMPLEMENTATION ###########

# Spotify Credentials
client_id = 'ee25b9c5e4fb4221a09e60fe877e63a2'
client_secret = '33be200e61ad4caa9fa61b8331c00421'

# Initialize Spotipy with user credentials
sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id, client_secret))

# Playlist ID for Spotify's "Today's Top Hits"
todays_top_hits_id = '37i9dQZF1DXcBWIGoYBM5M' 
new_music_playlist_id = '37i9dQZF1DX4JAvHpjipBk'


 # Function to get audio features and classify moods
def get_audio_features_for_playlist(playlist_id):
    track_ids = [track['track']['id'] for track in sp.playlist_tracks(playlist_id)['items'] if track['track']]
    features = sp.audio_features(track_ids)
    return features

def classify_moods(features):
    mood_counts = {'Energetic': 0, 'Calm': 0, 'Sad': 0, 'Happy': 0}
    for feature in features:
        if feature:
            if feature['energy'] > 0.7 and feature['valence'] > 0.5:
                mood_counts['Energetic'] += 1
            elif feature['energy'] < 0.4 and feature['valence'] < 0.5:
                mood_counts['Calm'] += 1
            elif feature['valence'] < 0.3:
                mood_counts['Sad'] += 1
            else:
                mood_counts['Happy'] += 1
    return mood_counts

def create_mood_chart(mood_counts):
    mood_df = pd.DataFrame(list(mood_counts.items()), columns=['Mood', 'Count'])
    return alt.Chart(mood_df).mark_bar().encode(
        x='Mood:N',
        y='Count:Q',
        color='Mood:N',
        tooltip=['Mood', 'Count']
    )


def get_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    while results:
        tracks.extend(results['items'])
        results = sp.next(results)
    return tracks

def get_genre_counts(tracks):
    genre_count = defaultdict(int)
    artist_ids = set()
    for item in tracks:
        track = item.get('track')
        if track:
            for artist in track['artists']:
                artist_ids.add(artist['id'])

    # Fetch genres in batches to minimize API calls
    artist_ids = list(artist_ids)
    for i in range(0, len(artist_ids), 50):  # Spotify API allows up to 50 ids per request
        artists = sp.artists(artist_ids[i:i+50])['artists']
        for artist in artists:
            for genre in artist['genres']:
                genre_count[genre] += 1
    return genre_count

def get_spotify_embed_html(playlist_id):
    return f'<iframe src="https://open.spotify.com/embed/playlist/{playlist_id}?utm_source=generator" width="100%" height="380" frameborder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe>'

def show_homepage():
    st.title("Playlist Dashboard")

    # Simulate real-time listener count
    listener_count_today_hits = random.randint(25000, 75000)
    listener_count_new_music = random.randint(5000, 10000)

    # Setup for "Today's Top Hits"
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h3 style='font-size: 22px;'>Today's Top Hits ({listener_count_today_hits} Active Users)</h3>", unsafe_allow_html=True)

        todays_top_hits_html = get_spotify_embed_html('37i9dQZF1DXcBWIGoYBM5M')
        st.markdown(todays_top_hits_html, unsafe_allow_html=True)

    features_today_hits = get_audio_features_for_playlist('37i9dQZF1DXcBWIGoYBM5M')
    mood_counts_today_hits = classify_moods(features_today_hits)
    chart_today_hits = create_mood_chart(mood_counts_today_hits)

    with col2:
        st.write('\n\n')
        st.write('\n\n') 
        st.write('\n\n')
        st.write('\n\n')   
        st.write('\n\n')
        st.write('\n\n')
        st.write('\n\n')
        st.altair_chart(chart_today_hits, use_container_width=True)

    # Setup for "New Music Playlist"
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"<h3 style='font-size: 22px;'>New Music Playlist ({listener_count_new_music} Active Users)</h3>", unsafe_allow_html=True)
        new_music_playlist_html = get_spotify_embed_html('37i9dQZF1DX4JAvHpjipBk')
        st.markdown(new_music_playlist_html, unsafe_allow_html=True)

    features_new_music = get_audio_features_for_playlist('37i9dQZF1DX4JAvHpjipBk')
    mood_counts_new_music = classify_moods(features_new_music)
    chart_new_music = create_mood_chart(mood_counts_new_music)

    with col4:
        st.write('\n\n')
        st.write('\n\n') 
        st.write('\n\n')
        st.write('\n\n')   
        st.write('\n\n')
        st.write('\n\n')
        st.write('\n\n')
        st.altair_chart(chart_new_music, use_container_width=True)
        
# Add some space before the chart
    st.write('\n\n')  

    # Playlist IDs
    playlists = {
        "Today's Top Hits": '37i9dQZF1DXcBWIGoYBM5M',
        "New Music": '37i9dQZF1DX4JAvHpjipBk'
    }

    # Fetch and process data
    data = []
    for name, playlist_id in playlists.items():
        tracks = get_playlist_tracks(playlist_id)
        genre_counts = get_genre_counts(tracks)
        for genre, count in genre_counts.items():
            data.append({'Playlist': name, 'Genre': genre, 'Count': count})

    # Data visualization
    df = pd.DataFrame(data)
    if not df.empty:
        chart = alt.Chart(df).mark_bar().encode(
            y='Count:Q',
            x='Genre:N',
            color='Playlist:N',
            tooltip=['Genre', 'Count', 'Playlist']
        ).properties(width=700, 
                     height=500,
                     title='Genre Distribution Across Playlists')
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No data available.")

    # Additional components to add



# Function to process and return search results
def process_search_results(results):
    data = {
        'Album Cover': [],
        'Name': [],
        'Artist': [],
        'Album': [],
        'Release Date': [],
        'Preview URL': [],
        'External URL': []
    }
    for track in results['tracks']['items']:
        data['Album Cover'].append(track['album']['images'][0]['url'] if track['album']['images'] else None)
        data['Name'].append(track['name'])
        data['Artist'].append(track['artists'][0]['name'])
        data['Album'].append(track['album']['name'])
        data['Release Date'].append(track['album']['release_date'])
        data['Preview URL'].append(track.get('preview_url'))
        data['External URL'].append(track['external_urls']['spotify'])

    return pd.DataFrame(data), [track.get('preview_url') for track in results['tracks']['items']]

# def create_playlist(playlist_name, user_id, user_type=None):
#     db_connection = connect_to_mysql_db1() if user_type == 'admin' else connect_to_mysql_db2()
#     if db_connection:
#         try:
#             cursor = db_connection.cursor()
#             insert_query = "INSERT INTO playlists (playlist_name, user_id) VALUES (%s, %s)"
#             cursor.execute(insert_query, (playlist_name, user_id))
#             db_connection.commit()
#             # After a successful insert, store the SQL command in session state.
#             st.session_state['sql_command'] = cursor.statement
#             return "Playlist created successfully."
#         except mysql.connector.Error as e:
#             return f"Database error during playlist creation: {e}"
#         finally:
#             cursor.close()
#             close_mysql_connection(db_connection)

def create_playlist(playlist_name, user_id, user_type):
    db_connection = connect_to_mysql_db1() if user_type == "admin" else connect_to_mysql_db2()
    if db_connection:
        try:
            cursor = db_connection.cursor()
            insert_query = "INSERT INTO playlists (playlist_name, user_id) VALUES (%s, %s)"
            cursor.execute(insert_query, (playlist_name, user_id))
            db_connection.commit()
            return True, "Playlist created successfully."
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
            return False, ""  # Return failure and empty SQL command
        finally:
            cursor.close()
            db_connection.close()
    else:
        return False, "Failed to connect to database."



# Function to perform a unified search on Spotify
def unified_search_spotify(keyword):
    results = sp.search(q=keyword, limit=20, type='track')
    return process_search_results(results)


def display_spotify_search_results(search_keyword):
    search_results_df, preview_urls = unified_search_spotify(search_keyword)
    error_message = None  
    create_modal = Modal("SQL for Playlist Creation", key="create_sql_modal")
    add_modal = Modal("SQL for Adding Song", key="add_sql_modal")

    if not search_results_df.empty:
        for index, row in search_results_df.iterrows():
            create_modal_key = f"create_sql_modal_{index}"
            create_modal = Modal("SQL for Playlist Creation", key=create_modal_key)
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 3, 1, 1], gap='small')
                with col1:
                    if row['Album Cover']:
                        st.image(row['Album Cover'], width=105)
                with col2:
                    st.markdown(f"**{row['Name']}** by *{row['Artist']}* from the album *{row['Album']}*")
                    release_date = row.get('Release Date', 'Unknown release date')
                    st.caption(f"Released on: {release_date}")
                with col3:
                    if row.get('Preview URL'):
                        st.audio(row['Preview URL'], format='audio/mp3')
                with col4:
                    playlists = get_playlists_from_db(st.session_state['user_info']['user_id'])
                    playlist_options = [("", "Select a playlist...")] + [(p[0], p[1]) for p in playlists] + [("Create New Playlist", "Create New Playlist")]
                    playlist_choice = st.selectbox(
                        "Add to Playlist", 
                        options=[p[1] for p in playlist_options], 
                        format_func=lambda x: x if x else "Select a playlist...",
                        key=f"playlist_select_{index}"
                    )
                    
                    song_data = {
                        'Name': row['Name'],
                        'Artist': row['Artist'],
                        'Album': row['Album'],
                        'Release Date': row['Release Date'],
                        'Preview URL': row.get('Preview URL'),
                        'External URL': row['External URL'],
                        'Track ID': row.get('Track ID')
                    }
                    
                    if playlist_choice == "Create New Playlist":
                        new_playlist_name = st.text_input("New Playlist Name", key=f"new_playlist_{index}")
                        create_button_pressed = st.button("Create Playlist", key=f"create_playlist_button_{index}")
                        if create_button_pressed and new_playlist_name:
                            error_message = create_playlist(new_playlist_name, st.session_state['user_info']['user_id'], 'customer')
                            if error_message == "Playlist created successfully.":
                                st.success(error_message)
                                st.session_state['sql_command'] = f"INSERT INTO playlists (playlist_name, user_id) VALUES ('{new_playlist_name}', '{st.session_state['user_info']['user_id']}');"
                                create_modal.open()
                            else:
                                st.error(error_message) 

                    elif playlist_choice: 
                        playlist_id = next((p[0] for p in playlist_options if p[1] == playlist_choice), None)
                        add_button_pressed = st.button("Add Song", key=f"add_song_{index}")

                        add_modal = Modal("SQL for Adding Song", key=f"add_sql_modal_{index}")

                        if add_button_pressed and playlist_id:
                            error_message = add_song_to_playlist(song_data, playlist_id)
                            if error_message == "Song added!":
                                st.session_state['sql_command'] = f"INSERT INTO songs (name, artist, album, release_date, preview_url, external_url, playlist_id) VALUES ('{song_data['Name']}', '{song_data['Artist']}', '{song_data['Album']}', '{song_data['Release Date']}', '{song_data['Preview URL']}', '{song_data['External URL']}', {playlist_id});"
                                add_modal.open()

            st.markdown("---")

            if create_modal.is_open():
                with create_modal.container():
                    st.code(st.session_state.get('sql_command', ''))
            if add_modal.is_open():
                with add_modal.container():
                    st.code(st.session_state.get('sql_command', ''))    
                
    else:
        st.write("No results found.")


def run_sql_query(sql_query):
    # Use the existing database connection function
    db_connection = connect_to_mysql_db2()
    if db_connection:
        try:
            cursor = db_connection.cursor(dictionary=True)  # Fetch rows as dictionaries
            cursor.execute(sql_query)
            result = cursor.fetchall()  # Fetch all results
            if not result:
                st.error("Query executed successfully but no data was returned.")
            return pd.DataFrame(result)
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        finally:
            cursor.close()
            close_mysql_connection(db_connection)
    else:
        st.error("Failed to connect to database.")
        return pd.DataFrame()  # Return empty DataFrame if connection failed

def show_playlists(user_id):
    playlists = get_playlists_from_db(user_id)
    tab1, tab2 = st.tabs(["My Playlists", "All Songs"])

    with tab1:
        selected_playlist_name = st.selectbox('Select a playlist:', [playlist[1] for playlist in playlists])

        if selected_playlist_name:
            selected_playlist_id = next(playlist[0] for playlist in playlists if playlist[1] == selected_playlist_name)
            songs = get_songs_from_playlist(selected_playlist_id)

            for song in songs:
                song_id = song[0]
                song_name = song[1]
                artist_name = song[2]
                preview_url = song[5]

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"{song_name} - {artist_name}")
                    if preview_url:
                        st.audio(preview_url)
                with col3:
                    if st.button("Remove", key=f"remove_{song_id}"):
                        sql_command, success = remove_song_from_playlist(song_id, selected_playlist_id)
                        if success:
                            st.success("Song removed successfully!")
                            with st.popover("See SQL"):
                                st.code(sql_command)
                        else:
                            st.error("Failed to remove song.")

                st.markdown("---")  # Adds a horizontal line after each song

            if st.button("Delete Playlist", key=f"delete_{selected_playlist_id}"):
                sql_command = delete_playlist(selected_playlist_id)
                with st.expander("See SQL"):
                    st.code(sql_command)

    with tab2:
        sql_query = """
        SELECT u.username AS Username, s.name AS Song_Name, s.artist AS Artist, s.album AS Album, 
               s.release_date AS Release_Date, pl.playlist_Name, pl.created_at AS Playlist_Created_On
        FROM TuneSyncCustomers.songs s
        JOIN TuneSyncCustomers.playlists pl ON pl.playlist_id = s.playlist_id
        JOIN TuneSyncCustomers.users u ON u.user_id = pl.user_id;
        """
        result_df = run_sql_query(sql_query)
        if not result_df.empty:
            st.dataframe(result_df)
        else:
            st.write("No data to display.")

        with st.expander("See SQL"):
            st.code(sql_query)


def update_song_in_db(song_id, new_name, new_artist, new_album, new_release_date):
    db_connection = connect_to_mysql_db2()
    if db_connection:
        try:
            cursor = db_connection.cursor()
            update_query = """
                UPDATE songs
                SET name = %s, artist = %s, album = %s, release_date = %s
                WHERE song_id = %s
            """
            cursor.execute(update_query, (new_name, new_artist, new_album, new_release_date, song_id))
            db_connection.commit()
            st.success("Song updated successfully!")
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
        finally:
            cursor.close()
            close_mysql_connection(db_connection)

def remove_song_from_playlist(song_id, playlist_id):
    db_connection = connect_to_mysql_db2()  # Assuming customer data is in DB2
    if db_connection:
        try:
            cursor = db_connection.cursor()
            delete_query = f"DELETE FROM songs WHERE song_id = {song_id} AND playlist_id = {playlist_id};"
            cursor.execute(delete_query)
            db_connection.commit()
            return delete_query, True  # Return the SQL command executed and success status
        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
            return f"Database error: {e}", False  # Return the error message and failure status
        finally:
            cursor.close()
            db_connection.close()
    else:
        return "Failed to connect to database.", False  # Return the failure message and status


def delete_playlist(playlist_id):
    db_connection = connect_to_mysql_db2()
    if db_connection:
        try:
            cursor = db_connection.cursor()
            sql_commands = ""

            # Delete all songs from this playlist first
            delete_songs_query = f"DELETE FROM songs WHERE playlist_id = {playlist_id};"
            cursor.execute(delete_songs_query)
            sql_commands += "" + delete_songs_query + "\n"

            # Now, delete the playlist itself
            delete_playlist_query = f"DELETE FROM playlists WHERE playlist_id = {playlist_id};"
            cursor.execute(delete_playlist_query)
            sql_commands += "" + delete_playlist_query

            db_connection.commit()
            cursor.close()
            db_connection.close()

            return True, sql_commands

        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
            return "Error in executing SQL commands."
        finally:
            if cursor:
                cursor.close()
            if db_connection:
                db_connection.close()
    else:
        return "Failed to connect to database."




def add_song_to_playlist(song_data, playlist_id):
    db_connection = connect_to_mysql_db2()
    if not db_connection:
        return "Connection to the database failed."
    
    try:
        cursor = db_connection.cursor()
        insert_song_query = """
            INSERT INTO songs (name, artist, album, release_date, preview_url, external_url, playlist_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_song_query, (
            song_data['Name'],
            song_data['Artist'],
            song_data['Album'],
            song_data['Release Date'],
            song_data['Preview URL'],
            song_data['External URL'],
            playlist_id
        ))
        # Capture the SQL command right after executing it
        executed_sql_command = cursor.statement
        db_connection.commit()
        
        # Store the successful SQL command in session state
        st.session_state['sql_command'] = cursor.statement
        return "Song added!"
    except mysql.connector.Error as e:
        return f"Database error: {e}"
    finally:
        cursor.close()
        close_mysql_connection(db_connection)

# @st.cache_data(hash_funcs={mysql.connector.connection.MySQLConnection: id})
def get_playlists_from_db(userid):
    db_connection = connect_to_mysql_db2()  # Connect to the TuneSyncCustomers database
    if db_connection:
        try:
            cursor = db_connection.cursor()
            select_query = """
                SELECT playlist_id, playlist_name FROM playlists
                WHERE user_id = %s
            """
            cursor.execute(select_query, (userid,))
            playlists = cursor.fetchall()
            return playlists  # Returns a list of tuples (playlist_id, playlist_name)
        except mysql.connector.Error as e:
            print(f"Error fetching playlists from database: {e}")
            return []
        finally:
            cursor.close()
            close_mysql_connection(db_connection)

# @st.cache_data(hash_funcs={mysql.connector.connection.MySQLConnection: id})
def get_songs_from_playlist(playlist_id):
    db_connection = connect_to_mysql_db2()  # Connect to the TuneSyncCustomers database
    if db_connection:
        try:
            cursor = db_connection.cursor()
            select_query = """
                SELECT * FROM songs
                WHERE playlist_id = %s
            """
            cursor.execute(select_query, (playlist_id,))
            songs = cursor.fetchall()
            return songs  # Returns a list of tuples with all song fields
        except mysql.connector.Error as e:
            print(f"Error fetching songs from database: {e}")
            return []
        finally:
            cursor.close()
            close_mysql_connection(db_connection)

def get_last_inserted_playlist_id():
    db_connection = connect_to_mysql_db2()
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT LAST_INSERT_ID()")
        playlist_id = cursor.fetchone()[0]
        return playlist_id
    finally:
        cursor.close()
        close_mysql_connection(db_connection)

def update_song_in_database(song_id, new_name, new_artist):
    # Connect to the database
    db_connection = connect_to_mysql_db2()
    if db_connection:
        try:
            # Create a new cursor
            cursor = db_connection.cursor()
            # Prepare the update statement
            update_query = "UPDATE songs SET name = %s, artist = %s WHERE id = %s"
            # Execute the update statement
            cursor.execute(update_query, (new_name, new_artist, song_id))
            # Commit the changes
            db_connection.commit()
            # Close the cursor and connection
            cursor.close()
            db_connection.close()
            # Indicate success
            return "Song updated successfully."
        except mysql.connector.Error as e:
            # Handle any errors that occur
            return f"Database error: {e}"
        except Exception as e:
            # Handle any other exceptions
            return f"An error occurred: {e}"
    else:
        # Handle the case where the database connection fails
        return "Failed to connect to the database."


def create_account():
    with st.form(key='create_account_form'):
        new_username = st.text_input('Username')
        new_email = st.text_input('Email')
        new_password = st.text_input('Password', type='password')
        confirm_password = st.text_input('Confirm Password', type='password')
        submit_button = st.form_submit_button('Create Account')
        
        if submit_button:
            if new_password == confirm_password:
                hashed_password = hash_password(new_password).decode('utf-8')  # Hash the password
                usertype = "admin" if new_email.endswith("@tunesync.com") else "customer"
                # Use st.echo to display the block of code executed within this context
                code = ''' 
                def hash_email(email):
                    if '@' in email:
                        _, domain = email.split('@', 1)
                        domain = domain.lower()  # Normalize the domain to lowercase
                        hasher = hashlib.sha256()
                        hasher.update(domain.encode('utf-8'))
                        domain_hash_hex = hasher.hexdigest()
                        tunesync_hash_hex = hashlib.sha256('tunesync.com'.encode('utf-8')).hexdigest()
                        if domain_hash_hex == tunesync_hash_hex:
                            return 'db1'
                        else:
                            return 'db2'
                    else:
                        return None  # Handles incorrect formatting
                '''   
                st.code(code, language='python')
                with st.echo(): 
                    if new_email.endswith("@tunesync.com"):
                        db_connection = connect_to_mysql_db1()
                        db_type = "TuneSyncAdmin (DB1)"
                    else:
                        db_connection = connect_to_mysql_db2()
                        db_type = "TuneSyncCustomers (DB2)"

                    if db_connection:
                        try:
                            cursor = db_connection.cursor()
                            insert_query = """
                                INSERT INTO users (username, password, email, usertype, created_at)
                                VALUES (%s, %s, %s, %s, NOW())
                            """
                            cursor.execute(insert_query, (new_username, hashed_password, new_email, usertype))
                            db_connection.commit()
                            st.success(f"User created successfully in {db_type}!")
                        except mysql.connector.Error as e:
                            st.error(f"Error inserting user into database: {e}")
                        finally:
                            cursor.close()
                            db_connection.close()
                    else:
                        st.error('Database connection failed.')
            else:
                st.error('Passwords do not match.')




# Function to insert a new user into the correct database based on their email domain
def insert_user(username, password, email):
    hashed_password = hash_password(password).decode('utf-8')  # Make sure to hash the password
    usertype = "admin" if email.endswith("@tunesync.com") else "customer"

    # Decide which database to use based on the user's email domain
    db_connection = connect_to_mysql_db1() if usertype == "admin" else connect_to_mysql_db2()
    
    if db_connection is not None:
        try:
            cursor = db_connection.cursor()
            insert_query = """
                INSERT INTO users (username, password, email, usertype, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            # Execute the insert operation
            cursor.execute(insert_query, (username, hashed_password, email, usertype))
            db_connection.commit()  # Don't forget to commit the transaction
            return True, f"User created successfully as {usertype}"  # Return success status and message
        except mysql.connector.Error as e:
            return False, f"Error inserting user into database: {e}"  # Return failure status and message
        finally:
            cursor.close()
            db_connection.close()
    else:
        return False, 'Database connection failed.'  # Return failure status and message




# Function to handle forgot password
def forgot_password():
    with st.form(key='forgot_password_form'):
        forgot_username = st.text_input('Username')
        submit_button = st.form_submit_button(label='Reset Password')

        if submit_button:
            user_info = fetch_user_info(forgot_username)
            if user_info and user_info.get('email'):
                reset_link = f"http://your-app-url/reset_password?token=generated_token"
                send_password_reset_email(user_info['email'], reset_link)
                st.success('A password reset link has been sent to your email address.')
            else:
                st.error("The username entered does not exist or cannot retrieve email.")

# Function to handle reset password
def reset_password():
    with st.form(key='reset_password_form'):
        reset_username = st.text_input('Username')
        reset_token = st.text_input('Reset Token')  # This should be the token you sent via email
        new_password = st.text_input('New Password', type='password')
        confirm_new_password = st.text_input('Confirm New Password', type='password')
        submit_button = st.form_submit_button(label='Change Password')

        if submit_button:
            user_info = fetch_user_info(reset_username)
            if user_info and user_info.get('reset_token') == reset_token:
                if new_password == confirm_new_password:
                    hashed_new_password = hash_password(new_password).decode('utf-8')
                    update_user_password(reset_username, hashed_new_password)
                    # Optionally send confirmation email here
                    st.success('Your password has been updated successfully.')
                else:
                    st.error("The new passwords do not match.")
            else:
                st.error("Invalid username or reset token.")


def login_user():
    with st.form(key='login_form_unique'):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        if submit_button:
            authenticated, usertype = authenticate_user(username, password)
            if authenticated:
                # print(f"User {username} authenticated as {usertype} from {db_key}")
                user_info = fetch_user_info(username)
                if user_info:
                    st.session_state['authentication_status'] = True
                    st.session_state['user_info'] = user_info
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Failed to retrieve user details after authentication.")
            else:
                st.error("Invalid username or password.")





# # Function to handle login
# def login_user():
#     with st.form(key='login_form_unique'):
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         submit_button = st.form_submit_button("Login")
#         if submit_button:
#             authenticated, usertype = authenticate_user(username, password)
#             if authenticated:
#                 user_info = fetch_user_info(username)
#                 if user_info:
#                     # Store user information in the session state
#                     st.session_state['authentication_status'] = True
#                     st.session_state['user_info'] = user_info
#                     st.success("Login successful!")
#                     # Redirect the user based on UserType
#                     if usertype == 'admin':
#                         # Redirect to admin interface
#                         st.rerun()  # Rerun the app which will now detect the user as logged in
#                     else:
#                         # Redirect to customer interface
#                         st.rerun()  # Rerun the app which will now detect the user as logged in
#                 else:
#                     st.error("Failed to retrieve user details.")
#             else:
#                 st.error("Invalid username or password.")




# Initialize session state variables if they don't exist.
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {'user_id': None, 'username': None, 'email': None, 'usertype': None}
if 'page' not in st.session_state:
    st.session_state['page'] = 'Login'

st.sidebar.title("TuneSync 🎧")

# Define the sidebar using option_menu
def render_sidebar():
    with st.sidebar:
        # Create a title for the sidebar
        st.header("Navigation")
        
        # Define the menu items based on authentication status
        if st.session_state.get('authentication_status'):
            # If authenticated, check the user's type
            usertype = st.session_state['user_info'].get('usertype')

            # Admin tools
            if usertype == 'admin':
                options = ["Homepage", "Systems", "Profile", "Logout"]
            # User features
            elif usertype == 'customer':
                options = ["Homepage", "My Playlists", "Search Music", "Profile", "Logout"]
        else:
            # Options for non-authenticated users
             options = ["Login", "Create Account"]
            # options = ["Login", "Create Account", "Forgot Password", "Reset Password"]
        
        # Create the option menu
        choice = option_menu(None, options, icons=["house", "book", "person", "box-arrow-right"], menu_icon="cast", default_index=0, orientation="vertical")
        
        # Update the page based on the selection
        st.session_state['page'] = choice
        
        # Additional functionality for logout
        if choice == 'Logout':
            st.session_state['authentication_status'] = None
            st.session_state['user_info'] = {'usertype': None}
            st.session_state['page'] = 'Login'
            st.experimental_rerun()

# Call the function to render the sidebar
render_sidebar()

# Main app logic based on the current page
if st.session_state.get('authentication_status'):
    if st.session_state['page'] == 'Homepage':
        show_homepage()
    if st.session_state['page'] == 'Systems' and st.session_state['user_info']['usertype'] == 'admin':
        manage_playlists_and_users()
        pass
    # elif st.session_state['page'] == 'Systems' and st.session_state['user_info']['usertype'] == 'admin':
    #     show_systems()
    #     pass
    elif st.session_state['page'] == 'Profile':
        show_profile()
    elif st.session_state['page'] == 'My Playlists' and st.session_state['user_info']['usertype'] == 'customer':
        show_playlists(st.session_state['user_info']['user_id'])
    elif st.session_state['page'] == 'Search Music' and st.session_state['user_info']['usertype'] == 'customer':
        st.markdown("""
        ### Discover and Curate Music
        Search for tracks, listen to previews, and add your favorites to playlists directly from Spotify's extensive library.
        """, unsafe_allow_html=True)
        search_keyword = st.text_input("Enter search keyword:", key='spotify_search')
        if search_keyword:
            display_spotify_search_results(search_keyword)
else:
    if st.session_state['page'] == 'Login':
        login_user()
    elif st.session_state['page'] == 'Create Account':
        create_account()


