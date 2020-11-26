# THE CHALLENGE

Write a Python program that monitors a twitter account.
-	The program must output text from new tweets to stdout.
-	The program must output the 5 most recent tweets right after execution, then it must check for new tweets (and display them) every 10 mins.
-	The Twitter handle will be provided as a command line argument by the user starting the program
-	Make sure to use scraping or APIs that do not require user authentication or a twitter developer account.
-	Must not use open source libraries such as Twint, Tweepy to do the heavy lifting

**Bonus round #1:** Modify your Python program to add a simple API to dump all the tweets collected so far in JSON format via a simple curl command.

**Bonus round #2:** Write a Dockerfile that encapsulates this program. The Dockerfile should expose your API and also enable the tweets to be seen via stdout.

---

# Installation & Usage (Host Machine)

``` 

pipenv install
```

or

``` 

pip3 install -r requirements.txt
```

``` 

cd app
python3 follow.py --user realdonaldtrump
```

# Installation & Usage (Docker)

``` 

docker build -t kevinwochan ./
docker run --rm --name api -p 80:80 -e USER=realdonaldtrump kevinwochan
visit http://127.0.0.1 in browser
```

---

# Architectural Overview

## Follow.py

This program interacts with the Twitter API to fetch the latest tweets made by a user

* Generates a guest token
* Uses the guest token to find the twitter handle's Twitter user identification number
* Searches for the latest tweets by the twitter handle
* Filters irrelavant tweets returned from the search using the Twitter user identificatoin number
* Save tweets that have been scraped into a pickle file

### Tweet Model

This class defines what a Tweet is and how it can be represented

* contains information like tweet_id, message, author_id, author_name, date the tweet was published

### Twitter Client

This class is responsible for interactions with the Twitter API

* handles HTTP requests
* session storage
* maintains a TwitterAPIParser instance

### Twitter API Parser

This class is responsible for parsing the shape of API responses into data models

* Converts a json of tweets into a list of Tweet models
* Converts a json of a User profile into a user identification number

## FastAPI

A lightweight API that serves the pickled file

## Docker

Allows the entire application to be deployed in a container

# Areas of Improvement

## Anonymity

Although no developer accounts or users were registered to scrape the desired data. Two tokens are required to access the twitter API. 

1. The Bearer token
2. An x-guest-token 

The x-guest-token appears to have a limited lifetime (less than the span of this two day project), while the Bearer token does not.
This has allowed me to use a hard coded Bearer token for this project but risks Twitter noticing.
Using different devices and IP addresses, i found the Bearer token was the exact same. Searching this token online revealed other users
also having the same token. So the user may not be identifiable just from the Bearer token.
I have not yet found a solution to programmatically retrieve a valid Bearer token without launching an browser.
The alternative solution i had in mind would be to launch a Browser emulator like Pypeteer, and scrape the HTML of the page for
the desired data or intercept queries to endpoints.

## Scalability

This project utilises a single pickle file to store all tweets locally. With two processes (the server and the tweet saver), reading and writing
to the same file there are potential concurrency issues. Ideally, collected tweets would be stored in a proper database as databases 
provide an easy querying interface and with concurrency controls. 

## Paginating API requests

Twitter allows queries to be broken into chunks so the client doesnt need to download all the results at once.
This is not a large of an issue since Twitter limits user's tweets to 2, 400 a day (100 per hour, 20 every 10 mins).

# Choices

## HTML scraping vs API scraping

Emulated Browers more closely resembles how a human would interact with the Twitter website and is the natural choice. However, the HTML structure of the page
could change without Twitter providing any notice where as JSON structured API responses are much easier to navigate and less likely to change.

## Flask vs Fast API

I hadn't use Fast API before this project. I'd previously used Flask and Django to build APIs. 
https://www.techempower.com/benchmarks/#section=data-r0&hw=ph&test=query&l=z8kflr-v&a=2&f=0-0-0-jz6rk-0-6bk-jz7k0-e8-18y8w-cqo-0
The above performance comparison demonstrated that FastAPI is apparently the fastest Python APi framework. Their documentation and syntax
closely resembles Flask.
