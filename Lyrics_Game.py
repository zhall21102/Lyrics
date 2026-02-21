import re
import time
import csv
import random
import lyricsgenius as genius
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from access_tokens import genius_CAT, spotify_auth

#GLOBAL VARIABLES
api = genius.Genius(genius_CAT)
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_auth['id'],
                                               client_secret=spotify_auth['secret'],
                                               redirect_uri=spotify_auth['redirect'],
                                               scope="user-library-read playlist-read-private playlist-read-collaborative",
                                               show_dialog=True))

#INTERNAL FUNCTIONS
def get_song(song_source):
    album   = None
    results = None
    playlist_info = None
    title   = ""
    artist  = ""
    song_array = []
    if song_source == "1":
        title = input("Title of song: ")
        artist = input("Artist of song: ")
        song_array = [[title,artist]]

    elif song_source == "2" or song_source == "3":
        playlist_file = "playlist.csv"
        if song_source == "3":
            playlist_file = input("Enter playlist file: ")
        with open(playlist_file, "r", newline='') as csvfile:
            playlistreader = csv.reader(csvfile)
            song_array = list(playlistreader)[1:]

    elif song_source == "4":
        name = input("Title of album: ")
        artist = input("Artist of album: ")
        album = api.search_album(name=name, artist=artist)
        if album:
            print(f"Found {album.name} by {album.artist}")
            for track in album.tracks:
                song_array.append([track[1].title, album.artist])

    elif song_source == "5":
        playlist = input("Enter URL of Spotify playlist: ")
        uri = playlist.split("/")[-1].split("?")[0]
        playlist_info = sp.playlist(uri)
        if playlist_info:
            print(f"Found playlist {playlist_info['name']} by {playlist_info['owner']['display_name']}")
        else:
            raise Exception("Error fetching playlist info")
        offset = 0
        limit = 100
        all_tracks = []

        # Use the manual endpoint to avoid the 403 error from a 02/11/26 Spotipy bug
        #TODO: When Spotipy is fixed, claen this code up
        while True:
            response = sp._get(f"playlists/{uri}/items", limit=limit, offset=offset)
            if response:
                items = response.get('items', [])
                if not items:
                    break

                all_tracks.extend(items)
                for item in items:
                    song_array.append([item["item"]["name"], item["item"]["artists"][0]["name"]])
                if len(items) < limit:
                    break

                offset += limit
            else:
                raise Exception("Error fetching playlist tracks")



    if len(song_array) > 1:
        shuffle = input("Would you like to shuffle the playlist? y/n\n").lower()
        if shuffle == "y":
            random.shuffle(song_array)

    return song_array

def sanitize(word):
    word = word.replace("е", "e") #Cyrillic (copyright protection?)
    return re.sub(r'[^a-zA-Z1-9 \n]', '', word)

api.remove_section_headers = True

print("""How to play:
Enter a song when prompted
Enter lyrics one word at a time
Enter "GiveUp" to end the game early

1) manual song entry
2) use playlist.csv
3) use input file
4) use an album
5) use a spotify playlist
""")
song_array = get_song(input())
for song_info in song_array:
    song = api.search_song(title=song_info[0], artist=song_info[1])

    if song:
        lyrics = song.lyrics
        print(f"Found {song.title} by {song.artist}")
    else:
        print("Song not found or lyrics could not be retrieved.")
        continue
    song_title  = song.title.replace("’", "'") #More copyright protection?
    song_artist = song.artist.replace("’", "'")

    lyric_list   = lyrics.replace(":","").split()
    lyric_set    = set(sanitize(lyrics.lower()).split())
    lyric_count  = len(lyric_set)
    total_lyrics = len(lyric_list)
    score = 0

    guessed_list = ["_____" for i in lyric_list]
    guessed_set = set()

    start = time.time()
    print(" ".join(guessed_list))

    while len(lyric_set) > 0:
        guess = sanitize(input("\nGuess a word! ").lower())
        if guess == "giveup":
            break
        guessed_set.add(guess)
        removed = False
        if guess in lyric_set:
            for i in range(len(lyric_list)):
                sanitized = sanitize(lyric_list[i].lower())
                if guess == sanitized:
                    guessed_list[i] = lyric_list[i]
                    score += 1
                    if not removed:
                        lyric_set.remove(sanitized)
                        removed = True

        print(" ".join(guessed_list))

    clock = time.time() - start
    if len(lyric_set) == 0:
        print(f"""Great work!
    Guesses: {len(guessed_set)}
    Time taken: {time.strftime('%H:%M:%S', time.gmtime(clock))}
    Accuracy: {lyric_count}/{len(guessed_set)} ({lyric_count / len(guessed_set) * 100}%)""")
        
    else:
        print(f"""Nice try!
    Unique Score:  {lyric_count-len(lyric_set)}/{lyric_count} ({(lyric_count-len(lyric_set)) / lyric_count * 100}%)
    Overall Score: {score}/{total_lyrics} ({(score) / total_lyrics * 100}%)
    Guesses: {len(guessed_set)}
    Time taken: {time.strftime('%H:%M:%S', time.gmtime(clock))}""")

    duplicate = False
    with open("score.csv", "r", newline='') as csvfile:
        scorereader = csv.reader(csvfile)
        scores = []
        for entry in scorereader:
            current = entry
            if current[0] == song_title and current[1] == song_artist:
                duplicate = True
                if int(current[2]) < lyric_count-len(lyric_set):
                    print(f"New record for this song! Previous high score: {current[2]}/{current[3]}")
                    current = [current[0], current[1], lyric_count-len(lyric_set), current[3]]
            scores.append(current)


    with open("score.csv", "w", newline='') as csvfile:
        scorewriter = csv.writer(csvfile)
        if not duplicate:
            scores.append([song_title,song_artist,lyric_count-len(lyric_set),lyric_count])
        scorewriter.writerows(scores)
    song = None