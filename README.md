<p align="center">
  <img src="https://github.com/jtcourtemarche/youtube-de-locke/blob/ba8a3cc274b8c6fc0b7bf3160a4d079ccf3f56e0/static/images/logo.png" alt="youtube-de-locke" width="539" />
</p>

Website built on Flask that synchronizes Youtube videos using websockets.

```
# You must create an api.py file with variables 
# 	API_KEY -> Youtube API key
#	SECRET_KEY -> Secret key for Flask

# Setup
pip install -r requirements.txt 

python 
>> import manage
>> manage.init_db()
>> manage.add_user('username', 'password')
>> exit()

# Run locally
flask run

# Run w/ gunicorn 
gunicorn app:app --bind 0.0.0.0:5000 --reload -k "geventwebsocket.gunicorn.workers.GeventWebSocketWorker" 
```
