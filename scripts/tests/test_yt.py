from youtube_comment_downloader import *
import itertools

downloader = YoutubeCommentDownloader()
url = "https://youtu.be/NXkxjN6r4o8"
print(f"Testing URL: {url}")

try:
    comments = downloader.get_comments_from_url(url, sort_by=SORT_BY_POPULAR)
    for comment in itertools.islice(comments, 5):
        print(f"[{comment['author']}]: {comment['text']}")
except Exception as e:
    print(f"Error: {e}")
