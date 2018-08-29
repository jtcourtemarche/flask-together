# youtube de locke
Website built on Flask that synchronizes Youtube videos using websockets.

```
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
gunicorn --bind 0.0.0.0:5000 --reload -k "geventwebsocket.gunicorn.workers.GeventWebSocketWorker" 
```