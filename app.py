# from glob import glob
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from flask_mysqldb import MySQL
from configparser import ConfigParser
import tmdbsimple as tmdb
import random
import os


print("Start of app.py")


app = Flask(__name__)
config_object = ConfigParser()
config_object.read("config.ini")


tmdb.API_KEY = config_object["TMDB-LOGIN"]["APIkey"]
# tmdb.API_KEY = "fe80472bacff902901720dcdaf98e60c" # sets up the API Key in the py API

# log in to mysql account and db
app.config['MYSQL_HOST'] = 'us-cdbr-east-05.cleardb.net'
app.config['MYSQL_USER'] = 'b59a6005561b64'
app.config['MYSQL_PASSWORD'] = '6cda5fdf'
app.config['MYSQL_DB'] = 'heroku_0cdf3077be5e51c'

# set up all global vars
actor1 = "temp"
actor2 = "temp"
actor3 = "temp"
actor4 = "temp"
actor5 = "temp"
director = "temp"
movieTitle = "temp"
movieDesc = "temp"
posterPath = "temp"
movieRecommended1 = "temp"
movieRecommended2 = "temp"
movieRecommended3 = "temp"

# set up the link with TMDB and the account
auth = tmdb.Authentication()
token = auth.token_new()
print(token["expires_at"])
auth.token_validate_with_login(request_token=token['request_token'],username=config_object["TMDB-LOGIN"]["user"],password=config_object["TMDB-LOGIN"]["pass"])
if auth.success:
    try:
        print("IT WORKED!")
        print(token['request_token'])
        session = auth.session_new(request_token=token['request_token']) # sets up the session
        session_id = session['session_id']
        account = tmdb.Account(session_id) # sets up the account associated with the session
        account.info()
        list_id = account.lists()['results'][0]['id']
        movieList = tmdb.Lists(list_id, session_id) # retuns the TMDB list object
        movieArr = movieList.info()['items'] # this is the array of the movies which is returned by Get Details in API
        listSize = movieList.info()['item_count'] # this is the number of movies in the array
    except Exception as e:
        print(e)
        pass
else:
    print("¯\_(ツ)_/¯")


mysql = MySQL(app)

# a function that handles all query code with an input of the query string
def executeQuery(query, args=None):
    cursor = mysql.connection.cursor()
    cursor.execute(query, args)
    if query.upper().startswith('SELECT'):
        data = cursor.fetchone()
    else:
        mysql.connection.commit()
        data = None
    cursor.close()
    return data

#a function to either search TMDB or MySQL for today's movie
def findMovie():
    global actor1
    global actor2
    global actor3
    global actor4
    global actor5
    global director
    global movieTitle
    global movieDesc
    global posterPath
    global movieRecs
    global movieRecommended1
    global movieRecommended2
    global movieRecommended3
    today = datetime.today().strftime('%Y-%m-%d') # sets the today variable to today in the specific string format

    # selects the movie data from SQL for today's date
    row = executeQuery(f'''SELECT actor1, actor2, actor3, actor4, actor5, director, title, movieDesc, posterPath, movieRecommended1, movieRecommended2, movieRecommended3
                    from movies WHERE date=\'{today}\'''')

    # if nothing was returned, pull from TMDB
    if row == None:

        todayMovieIndex = random.randint(0, listSize-1)
        movieID = movieArr[todayMovieIndex]['id']
        todaysMovie = tmdb.Movies(movieID)
        todaysMovieInfo = todaysMovie.info()
        movieTitle = todaysMovieInfo['original_title']
        credits = todaysMovie.credits()
        
        movieDesc = todaysMovieInfo["tagline"]
        posterPath = todaysMovieInfo["poster_path"]
        movieRecs = todaysMovie.recommendations()
        movieRecommended1 = movieRecs['results'][0]["original_title"]
        movieRecommended2 = movieRecs['results'][1]["original_title"]
        movieRecommended3 = movieRecs['results'][2]["original_title"]
        
        # these are ordered in 3rd billed, 4th billed, 5th billed, 2nd billed, 1st billed, director
        actor1 = credits['cast'][2]['name']
        actor2 = credits['cast'][3]['name']
        actor3 = credits['cast'][4]['name']
        actor4 = credits['cast'][1]['name']
        actor5 = credits['cast'][0]['name']
        directorFound = False
        i = 0
        while not directorFound:
            job = credits['crew'][i]['job']
            if job == 'Director':
                director = credits['crew'][i]['name']
                directorFound = True
            i += 1
        
        # delete from the list
        test = movieList.remove_item(media_id=movieID)
        print(test['status_message'])

        # then insert into SQL
        executeQuery(f'''INSERT INTO movies(title, actor1, actor2, actor3, actor4, actor5, director, date, movieDesc, posterPath, movieRecommended1, movieRecommended2, movieRecommended3)
             VALUES (\'{movieTitle}\',\'{actor1}\',\'{actor2}\',\'{actor3}\',\'{actor4}\',\'{actor5}\',\'{director}\',\'{today}\', \'{movieDesc}\' , \'{posterPath}\', \'{movieRecommended1}\', \'{movieRecommended2}\', \'{movieRecommended3}\')''')
        
    else:

        # otherwise, pull the data from the row into the global variables

        actor1 = row[0]
        actor2 = row[1]
        actor3 = row[2]
        actor4 = row[3]
        actor5 = row[4]
        director = row[5]
        movieTitle = row[6]
        movieDesc = row[7]
        posterPath = "https://image.tmdb.org/t/p/w185" + row[8]
        movieRecommended1 = row[9]
        movieRecommended2 = row[10]
        movieRecommended3 = row[11]


# run at the start, finds today's movie then passes through all necessary info
@app.route('/')
def home():
    findMovie()
    return render_template('castle.html', title='Cast.le', actor1=actor1, actor2=actor2, actor3=actor3, actor4=actor4, actor5=actor5, director=director, movieTitle=movieTitle,movieDesc=movieDesc, posterPath=posterPath, movieRecommended1=movieRecommended1, movieRecommended2=movieRecommended2, movieRecommended3=movieRecommended3)


# check a guess that is passed through to see if it matches what is in the db
@app.route('/guess', methods=["POST"])
def checkGuess():
    guess = request.form.get("guess").lower()
    today = datetime.today().strftime('%Y-%m-%d')
    row = executeQuery(f'''SELECT * from movies WHERE UPPER(title)=UPPER(\'{guess}\') AND date=\'{today}\'''')
    if row == None:
        correct = False
    else:
        correct = True
    return jsonify(correct=correct)


# check if the log in info was correct
@app.route('/login', methods=["POST"])
def logInUser():
    username = request.form.get("username")
    password = request.form.get("password")
    row = executeQuery(f'''SELECT * from users WHERE username=\'{username}\' AND password=\'{password}\'''')
    if row == None:
        loggedIn = False
    else:
        loggedIn = True
    return jsonify(loggedIn=loggedIn)


# insert the new user into the db
@app.route('/register', methods=["POST"])
def registerUser():
    username = request.form.get("username")
    password = request.form.get("password")
    executeQuery(f'''INSERT INTO users (username, password, wins, plays, winsIn1, winsIn2, winsIn3, winsIn4, winsIn5, winsIn6) VALUES (\'{username}\', \'{password}\', 0,0,0,0,0,0,0,0)''')
    registered = True
    return jsonify(registered=registered)


# update the user's stats and then pass through the updated stats
@app.route('/updateStats', methods=["POST"])
def updateStats():
    username = request.form.get("username")
    guessNum = request.form.get("guessNum")
    gameWon = request.form.get("gameWon")
    if gameWon == "true":
        executeQuery(f'''UPDATE users SET wins = wins + 1, plays = plays + 1, winsIn{guessNum} = winsIn{guessNum} + 1 WHERE username = \'{username}\'''')
    else:
        executeQuery(f'''UPDATE users SET plays = plays + 1 WHERE username = \'{username}\'''')
    
    results = executeQuery(f'''SELECT plays, wins, winsIn1, winsIn2, winsIn3, winsIn4, winsIn5, winsIn6 from users WHERE username = \'{username}\'''')
    return jsonify(plays=results[0], wins=results[1], winsIn1=results[2], winsIn2=results[3], winsIn3=results[4], winsIn4=results[5], winsIn5=results[6], winsIn6=results[7])

@app.route('/test')
def test():
    return "test"
# run the app
# app.run(debug=True, port=3456, host='0.0.0.0')
port = int(os.getenv('PORT', 5000))
if __name__ == '__main__':
    app.run(debug=True)