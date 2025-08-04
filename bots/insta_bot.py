from instagrapi import Client
import random

USERNAME = "smartsasta_"
PASSWORD = "Jay@1000"

hashtags = ["#dealsoftheday", "#onlineshopping", "#smartshopping", "#sasta", "#budgetfriendly"]
videos = ["assets/videos/video1.mp4", "assets/videos/video2.mp4"]
captions = [
    "🔥 Unbelievable Price! Check this product now 👇",
    "📦 Deal of the Day - Grab Before It's Gone!"
]

cl = Client()
cl.login(USERNAME, PASSWORD)

video = random.choice(videos)
caption = random.choice(captions) + "\n\n" + " ".join(random.sample(hashtags, 4)) + "\n\nAffiliate Link in Bio 🔗"

cl.video_upload(video, caption)
