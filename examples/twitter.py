#!/usr/bin/python

# A Twitter API client, implemented using remoteobjects

from urllib import urlencode, quote_plus
from urlparse import urljoin, urlunsplit
from httplib2 import Http
from remoteobjects import RemoteObject, fields, ListObject

twitter = None

class LastStatus(RemoteObject):
    created_at = fields.Field()
    id = fields.Field()
    text = fields.Field()
    source = fields.Field()
    truncated = fields.Field()
    in_reply_to_status_id = fields.Field()
    in_reply_to_user_id = fields.Field()
    favorited = fields.Field()
    in_reply_to_screen_name = fields.Field()

class User(RemoteObject):
    id = fields.Field()
    name = fields.Field()
    screen_name = fields.Field()
    location = fields.Field()
    description = fields.Field()
    profile_image_url = fields.Field()
    protected = fields.Field()
    followers_count = fields.Field()
    status = fields.Object(LastStatus)

    @classmethod
    def get_user(cls, http=None, **kwargs):
        url = '/users/show'
        if 'id' in kwargs:
            url += '/%s.json' % quote_plus(kwargs['id'])
        else:
            url += '.json'
        query = urlencode(filter(lambda x: x in ('screen_name', 'user_id'), kwargs))
        url = urlunsplit((None, None, url, query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

class DirectMessage(RemoteObject):
    id = fields.Field()
    sender_id = fields.Field()
    text = fields.Field()
    recipient_id = fields.Field()
    created_at = fields.Field()
    sender_screen_name = fields.Field()
    recipient_screen_name = fields.Field()
    sender = fields.Object(User)
    recipient = fields.Object(User)

class Status(RemoteObject):
    created_at = fields.Field()
    id = fields.Field()
    text = fields.Field()
    source = fields.Field()
    truncated = fields.Field()
    in_reply_to_status_id = fields.Field()
    in_reply_to_user_id = fields.Field()
    favorited = fields.Field()
    user = fields.Object(User)

    @classmethod
    def get_status(cls, id, http=None):
        return cls.get(urljoin(Twitter.endpoint, "/statuses/show/%d.json" % int(id)), http=http)

class DirectMessageList(ListObject):
    entries = fields.List(fields.Object(DirectMessage))
    def update_from_dict(self, data):
        super(DirectMessageList, self).update_from_dict({ 'entries': data })

    def __getitem__(self, key):
        return self.entries.__getitem__(key)

    @classmethod
    def get_messages(cls, http=None, **kwargs):
        url = '/direct_messages.json'
        query = urlencode(filter(lambda x: x in ('since_id', 'page'), kwargs))
        url = urlunsplit((None, None, url, query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

    @classmethod
    def get_sent_messages(cls, http=None, **kwargs):
        url = '/direct_messages/sent.json'
        query = urlencode(filter(lambda x: x in ('since_id', 'page'), kwargs))
        url = urlunsplit((None, None, url, query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

class UserList(ListObject):
    entries = fields.List(fields.Object(User))
    def update_from_dict(self, data):
        super(UserList, self).update_from_dict({ 'entries': data })

    def __getitem__(self, key):
        return self.entries.__getitem__(key)

    @classmethod
    def get_friends(cls, http=None, **kwargs):
        return cls.get_related("friends", http=http, **kwargs)

    @classmethod
    def get_followers(cls, http=None, **kwargs):
        return cls.get_related("followers", http=http, **kwargs)

    @classmethod
    def get_related(cls, relation, http=None, **kwargs):
        url = '/statuses/%s' % relation
        if 'id' in kwargs:
            url += '/%s.json' % quote_plus(kwargs['id'])
        else:
            url += '.json'
        query = urlencode(filter(lambda x: x in ('screen_name', 'user_id', 'page'), kwargs))
        url = urlunsplit((None, None, url, query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

class Timeline(ListObject):
    entries = fields.List(fields.Object(Status))
    def update_from_dict(self, data):
        super(Timeline, self).update_from_dict({ 'entries': data })

    def __getitem__(self, key):
        return self.entries.__getitem__(key)

    @classmethod
    def public(cls, http=None):
        return cls.get(urljoin(Twitter.endpoint, '/statuses/public_timeline.json'), http=http)

    @classmethod
    def friends(cls, http=None, **kwargs):
        query = urlencode(filter(lambda x: x in ('since_id', 'max_id', 'count', 'page'), kwargs))
        url = urlunsplit((None, None, '/statuses/friends_timeline.json', query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

    @classmethod
    def user(cls, http=None, **kwargs):
        url = '/statuses/user_timeline'
        if 'id' in kwargs:
            url += '/%s.json' % quote_plus(kwargs['id'])
        else:
            url += '.json'
        query = urlencode(filter(lambda x: x in ('screen_name', 'user_id', 'since_id', 'max_id', 'page'), kwargs))
        url = urlunsplit((None, None, url, query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

    @classmethod
    def mentions(cls, http=None, **kwargs):
        query = urlencode(filter(lambda x: x in ('since_id', 'max_id', 'page'), kwargs))
        url = urlunsplit((None, None, '/statuses/mentions.json', query, None))
        return cls.get(urljoin(Twitter.endpoint, url), http=http)

class Twitter(Http):
    endpoint = 'http://twitter.com/'

    @property
    def authd(self):
        return len(self.credentials.credentials) > 0

    def public_timeline(self):
        return Timeline.public(http=self)

    def friends_timeline(self, **kwargs):
        assert self.authd, "This request requires authentication."
        return Timeline.friends(http=self, **kwargs)

    def user_timeline(self, **kwargs):
        if not set(['screen_name', 'user_id', 'id']) & set(kwargs.keys()):
            assert self.authd, "This request requires authentication."
        return Timeline.user(http=self, **kwargs)

    def show(self, id):
        return Status.get_status(id, http=self)

    def user(self, id, **kwargs):
        if not set(['screen_name', 'user_id', 'id']) & set(kwargs.keys()):
            raise Exception("A screen_name, user_id or id keyword parameter is required.")
        return User.get_user(http=self, **kwargs)

    def mentions(self, **kwargs):
        assert self.authd, "This request requires authentication."
        return Timeline.mentions(http=self, **kwargs)

    def friends(self, **kwargs):
        if not set(['screen_name', 'user_id', 'id']) & set(kwargs.keys()):
            assert self.authd, "This request requires authentication."
        return UserList.get_friends(http=self, **kwargs)

    def direct_messages_received(self, **kwargs):
        assert self.authd, "This request requires authentication."
        return DirectMessageList.get_messages(http=self, **kwargs)

    def direct_messages_sent(self, **kwargs):
        assert self.authd, "This request requires authentication."
        return DirectMessageList.get_messages_sent(http=self, **kwargs)

if __name__ == '__main__':
    twitter = Twitter()

    print "\nPublic timeline:"
    for tweet in twitter.public_timeline():
        print "%d: %s from %s" % (tweet.id, tweet.text, tweet.user.screen_name)

    twitter.add_credentials("username", "password")

    if twitter.authd:
        print "Direct messages sent to me:"
        for tweet in twitter.direct_messages_received():
            print "%d: %s from %s" % (tweet.id, tweet.text, tweet.sender.screen_name)

        print "\nFrom my friends:"
        for tweet in twitter.friends_timeline():
            print "%d: %s from %s" % (tweet.id, tweet.text, tweet.user.screen_name)
