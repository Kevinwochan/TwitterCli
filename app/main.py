from fastapi import FastAPI
import pickle
from config import TWEETS_SAVE_FILE

app = FastAPI()

@app.get("/")
async def root():
    tweets = []
    with open(TWEETS_SAVE_FILE, 'rb') as f:
        try:
            while True:
                tweets.append(pickle.load(f))
        except EOFError:
            pass

    return tweets