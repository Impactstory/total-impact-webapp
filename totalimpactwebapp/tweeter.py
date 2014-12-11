from totalimpactwebapp import json_sqlalchemy
from util import commit
from util import cached_property
from util import dict_from_dir
from totalimpactwebapp import db
from birdy.twitter import AppClient, TwitterApiError, TwitterRateLimitError, TwitterClientError

from collections import defaultdict
import os
import datetime
import logging
logger = logging.getLogger('ti.tweeter')

# from https://github.com/inueni/birdy/issues/7
# to overrride JSONObject
class AppDictClient(AppClient):
    @staticmethod
    def get_json_object_hook(data):
        return data


def handle_all_user_lookups(user_dicts_from_twitter, tweeters):
    dicts_by_screen_name = defaultdict(str)
    for user_dict in user_dicts_from_twitter:
        screen_name = user_dict["screen_name"]
        dicts_by_screen_name[screen_name.lower()] = user_dict

    i = 0
    for tweeter in tweeters:
        i += 1
        if tweeter.screen_name.lower() in dicts_by_screen_name.keys():
            user_dict = dicts_by_screen_name[screen_name.lower()]
            tweeter.set_attributes_from_twitter_data(user_dict)
            # print i, "updated tweeter", tweeter, tweeter.last_collected_date
        else:
            tweeter.set_as_deleted()
        db.session.merge(tweeter)

    return True


def get_and_save_tweeter_followers(tweeters):

    client = AppDictClient(
        os.getenv("TWITTER_CONSUMER_KEY"),
        os.getenv("TWITTER_CONSUMER_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN")
    )

    logger.exception(u"Length of tweeters {num}".format(
         num=len(tweeters)))

    # print "length of tweeters", len(tweeters)

    screen_names_string = ",".join([tweeter.screen_name for tweeter in tweeters])
    # print "\n".join([tweeter.screen_name for tweeter in tweeters])

    try:
        response = client.api.users.lookup.post(screen_name=screen_names_string)
        handle_all_user_lookups(response.data, tweeters)
    except TwitterApiError, e:
        logger.exception("TwitterApiError error, skipping")
    except TwitterClientError, e:
        logger.exception("TwitterClientError error, skipping")
    except TwitterRateLimitError, e:
        logger.exception("TwitterRateLimitError error, skipping")
        # not totally sure what else I should do here.  retry somehow, or catch on cleanup run?

    commit(db)

    return


# example payload from twitter:  https://dev.twitter.com/rest/reference/get/users/lookup

class Tweeter(db.Model):
    screen_name = db.Column(db.Text, primary_key=True)
    followers = db.Column(db.Integer)
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    last_collected_date = db.Column(db.DateTime())   #alter table tweeter add last_collected_date timestamp
    is_deleted = db.Column(db.Boolean)  # alter table tweeter add is_deleted bool

    def __init__(self, **kwargs):
        if not "last_collected_date" in kwargs:
            self.last_collected_date = datetime.datetime.utcnow()
        super(Tweeter, self).__init__(**kwargs)


    def set_attributes_from_altmetric_post(self, post):
        self.followers = post["author"].get("followers", 0)
        self.name = post["author"].get("name", self.screen_name)
        self.description = post["author"].get("description", "")
        self.image_url = post["author"].get("image", None)
        # don't update last_collected date, because altmetric data is from old tweet
        return self

    def set_attributes_from_twitter_data(self, data):
        self.followers = data.get("followers_count", 0)
        self.name = data.get("name", self.screen_name)
        self.description = data.get("description", "")
        self.image_url = data.get("profile_image_url", None)
        self.last_collected_date = datetime.datetime.utcnow()
        return self

    def set_as_deleted(self):
        self.is_deleted = True
        self.last_collected_date = datetime.datetime.utcnow()
        return self

    def __repr__(self):
        return u'<Tweeter {screen_name} {followers}>'.format(
            screen_name=self.screen_name, 
            followers=self.followers)

    def to_dict(self):
        attributes_to_ignore = [
            "tweet"
        ]
        ret = dict_from_dir(self, attributes_to_ignore)
        return ret


# example
# [
#   {
#     "name": "Twitter API",
#     "profile_sidebar_fill_color": "DDEEF6",
#     "profile_background_tile": false,
#     "profile_sidebar_border_color": "C0DEED",
#     "profile_image_url": "http://a0.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
#     "location": "San Francisco, CA",
#     "created_at": "Wed May 23 06:01:13 +0000 2007",
#     "follow_request_sent": false,
#     "id_str": "6253282",
#     "profile_link_color": "0084B4",
#     "is_translator": false,
#     "default_profile": true,
#     "favourites_count": 24,
#     "contributors_enabled": true,
#     "url": "http://dev.twitter.com",
#     "profile_image_url_https": "https://si0.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png",
#     "utc_offset": -28800,
#     "id": 6253282,
#     "profile_use_background_image": true,
#     "listed_count": 10713,
#     "profile_text_color": "333333",
#     "lang": "en",
#     "followers_count": 1198334,
#     "protected": false,
#     "profile_background_image_url_https": "https://si0.twimg.com/images/themes/theme1/bg.png",
#     "geo_enabled": true,
#     "description": "The Real Twitter API. I tweet about API changes, service issues and happily answer questions about Twitter and our API. Don't get an answer? It's on my website.",
#     "profile_background_color": "C0DEED",
#     "verified": true,
#     "notifications": false,
#     "time_zone": "Pacific Time (US & Canada)",
#     "statuses_count": 3331,
#     "status": {
#       "coordinates": null,
#       "created_at": "Fri Aug 24 16:15:49 +0000 2012",
#       "favorited": false,
#       "truncated": false,
#       "id_str": "239033279343382529",
#       "in_reply_to_user_id_str": "134727529",
#       "text": "@gregclermont no, there is not. ^TS",
#       "contributors": null,
#       "retweet_count": 0,
#       "id": 239033279343382529,
#       "in_reply_to_status_id_str": "238933943146131456",
#       "geo": null,
#       "retweeted": false,
#       "in_reply_to_user_id": 134727529,
#       "place": null,
#       "source": "<a href="//sites.google.com/site/yorufukurou/\"" rel="\"nofollow\"">YoruFukurou</a>",
#       "in_reply_to_screen_name": "gregclermont",
#       "in_reply_to_status_id": 238933943146131456
#     },
#     "profile_background_image_url": "http://a0.twimg.com/images/themes/theme1/bg.png",
#     "default_profile_image": false,
#     "friends_count": 31,
#     "screen_name": "twitterapi",
#     "following": true,
#     "show_all_inline_media": false
#   },
#   {
#     "name": "Twitter",
#     "profile_sidebar_fill_color": "F6F6F6",
#     "profile_background_tile": true,
#     "profile_sidebar_border_color": "EEEEEE",
#     "profile_image_url": "http://a0.twimg.com/profile_images/2284174758/v65oai7fxn47qv9nectx_normal.png",
#     "location": "San Francisco, CA",
#     "created_at": "Tue Feb 20 14:35:54 +0000 2007",
#     "follow_request_sent": false,
#     "id_str": "783214",
#     "profile_link_color": "038543",
#     "is_translator": false,
#     "default_profile": false,
#     "favourites_count": 17,
#     "contributors_enabled": true,
#     "url": "http://blog.twitter.com/",
#     "profile_image_url_https": "https://si0.twimg.com/profile_images/2284174758/v65oai7fxn47qv9nectx_normal.png",
#     "utc_offset": -28800,
#     "id": 783214,
#     "profile_banner_url": "https://si0.twimg.com/brand_banners/twitter/1323368512/live",
#     "profile_use_background_image": true,
#     "listed_count": 72534,
#     "profile_text_color": "333333",
#     "lang": "en",
#     "followers_count": 12788713,
#     "protected": false,
#     "profile_background_image_url_https": "https://si0.twimg.com/profile_background_images/378245879/Twitter_1544x2000.png",
#     "geo_enabled": true,
#     "description": "Always wondering what's happening. ",
#     "profile_background_color": "ACDED6",
#     "verified": true,
#     "notifications": false,
#     "time_zone": "Pacific Time (US & Canada)",
#     "statuses_count": 1379,
#     "status": {
#       "coordinates": null,
#       "created_at": "Tue Aug 21 19:04:00 +0000 2012",
#       "favorited": false,
#       "truncated": false,
#       "id_str": "237988442338897920",
#       "retweeted_status": {
#         "coordinates": null,
#         "created_at": "Tue Aug 21 18:51:44 +0000 2012",
#         "favorited": false,
#         "truncated": false,
#         "id_str": "237985351858278400",
#         "in_reply_to_user_id_str": null,
#         "text": "Arijit Guha fought for insurance coverage, and won.\n http://t.co/ZvQ6fU2O #twitterstories http://t.co/bVYPNnV7",
#         "contributors": [
#           16896060
#         ],
#         "retweet_count": 118,
#         "id": 237985351858278400,
#         "in_reply_to_status_id_str": null,
#         "geo": null,
#         "retweeted": false,
#         "possibly_sensitive": false,
#         "in_reply_to_user_id": null,
#         "place": null,
#         "source": "web",
#         "in_reply_to_screen_name": null,
#         "in_reply_to_status_id": null
#       },
#       "in_reply_to_user_id_str": null,
#       "text": "RT @TwitterStories: Arijit Guha fought for insurance coverage, and won.\n http://t.co/ZvQ6fU2O #twitterstories http://t.co/bVYPNnV7",
#       "contributors": null,
#       "retweet_count": 118,
#       "id": 237988442338897920,
#       "in_reply_to_status_id_str": null,
#       "geo": null,
#       "retweeted": false,
#       "possibly_sensitive": false,
#       "in_reply_to_user_id": null,
#       "place": null,
#       "source": "web",
#       "in_reply_to_screen_name": null,
#       "in_reply_to_status_id": null
#     },
#     "profile_background_image_url": "http://a0.twimg.com/profile_background_images/378245879/Twitter_1544x2000.png",
#     "default_profile_image": false,
#     "friends_count": 1195,
#     "screen_name": "twitter",
#     "following": true,
#     "show_all_inline_media": true
#   }
# ]        