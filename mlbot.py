import praw
import sqlite3
import time
import datetime
import re
import feedparser


SUBREDDIT = "machinelearning"
USERAGENT = "shortscience"
SS_XML = "http://www.shortscience.org/rss-all.xml"
SUBMISSIONLIMIT = 100
COMMENTLIMIT = 100
LINK = re.compile('arxiv\.org/abs/([0-9]+\.[0-9]+)')
WAIT = 30


r = praw.Reddit(USERAGENT)
subreddit = r.subreddit(SUBREDDIT)
sqldb = sqlite3.connect("mlbot.db")
cursor = sqldb.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS replied(id TEXT)')
cursor.execute('CREATE INDEX IF NOT EXISTS replied_index ON replied(id)')




def getDate(submission):
    time = submission.created
    return datetime.datetime.fromtimestamp(time)

def checkSubmissions(subreddit, feed):
    for i in list(subreddit.new(limit=SUBMISSIONLIMIT)):
        print (i)
        if (containsLink(i.selftext) or containsLink(i.url)) \
                and not isReplied(i.id) \
                and (checkSS(getLinkIDs(i.selftext), feed) or checkSS(getLinkIDs(i.url), feed)):
            replySubmission(i, feed)


def checkComments(subreddit, feed):
    for i in list(subreddit.comments(limit=COMMENTLIMIT)):
        print (i)
        if containsLink(i.body) and not isReplied(i.id) and checkSS(getLinkIDs(i.body), feed):
            replyComment(i, feed)


def checkSS(arxivids, feed):
    for i in arxivids:
        for j in feed.entries:
            if "shortscience_arxivid" in j:
                if j["shortscience_arxivid"] == i:
                    return True
    return False

def getSSLink(arxivid, feed):
    for i in feed.entries:
        if "shortscience_arxivid" in i:
            if i["shortscience_arxivid"] == arxivid:
                return "http://www.shortscience.org/paper?bibtexKey=" + i["shortscience_bibtexkey"]
    return None

def containsLink(text):
    match = LINK.findall(text)
    return len(match) > 0

def getLinkIDs(text):
    match = LINK.findall(text)
    return match

def getSummary(arxivid, feed):
    score = -1
    summary = ""
    for i in feed.entries:
        if "shortscience_arxivid" in i:
            if i["shortscience_arxivid"] == arxivid and int(i["shortscience_votes"]) > score:
                score = int(i["shortscience_votes"])
                summary = i["summary"]
    summary = summary.replace("\n", "\n\n")
    return summary

def isReplied(id):
    cursor.execute('SELECT * FROM replied WHERE ID=?', [id])
    if cursor.fetchone():
        return True
    return False

def makeReplied(id):
    cursor.execute('INSERT INTO replied VALUES(?)', [id])
    sqldb.commit()

def replyComment(post, feed):
    linkids = []
    reply = "I am a bot! You linked to a paper that has a summary on ShortScience.org!"
    for i in getLinkIDs(post.body):
        if i not in linkids and checkSS([i], feed):
            linkids.append(i)
    for i in linkids:
        reply += "\n\n" + getSSLink(i, feed)
        reply += "\n\n**Summary Preview:**\n\n" + getSummary(i, feed)
    try:
        post.reply(reply)
    except praw.exceptions.APIException as e:
        print (e)
        time.sleep(WAIT)
        pass
    else:
        makeReplied(post.id)

def replySubmission(post, feed):
    linkids = []
    reply = "I am a bot! You linked to a paper that has a summary on ShortScience.org!"
    for i in getLinkIDs(post.selftext):
        if i not in linkids and checkSS([i], feed):
            linkids.append(i)
    for i in getLinkIDs(post.url):
        if i not in linkids and checkSS([i], feed):
            linkids.append(i)
    for i in linkids:
        reply += "\n\n" + getSSLink(i, feed)
        reply += "\n\n**Summary Preview:**\n\n" + getSummary(i, feed)
    try:
        post.reply(reply)
    except praw.exceptions.APIException as e:
        print (e)
        time.sleep(WAIT)
        pass
    else:
        makeReplied(post.id)

while True:
    feed = feedparser.parse(SS_XML)
    checkSubmissions(subreddit, feed)
    checkComments(subreddit, feed)
    time.sleep(WAIT)
