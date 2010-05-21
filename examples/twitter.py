#!/usr/bin/env python

# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""

A Twitter API client, implemented using remoteobjects.

"""

__version__ = '1.1'
__date__ = '17 April 2009'
__author__ = 'Brad Choate'


import httplib
from optparse import OptionParser
import sys
from urllib import urlencode, quote_plus
from urlparse import urljoin, urlunsplit

from httplib2 import Http

from remoteobjects import RemoteObject, fields, ListObject


class User(RemoteObject):

    """A Twitter account.

    A User can be retrieved from ``http://twitter.com/users/show.json`` with
    the appropriate ``id``, ``user_id``, or ``screen_name`` parameter.

    """

    id = fields.Field()
    name = fields.Field()
    screen_name = fields.Field()
    location = fields.Field()
    description = fields.Field()
    profile_image_url = fields.Field()
    protected = fields.Field()
    followers_count = fields.Field()
    status = fields.Object('Status')

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

    """A Twitter direct message.

    The authenticated user's most recent direct messages are at
    ``http://twitter.com/direct_messages.json``.

    """

    id = fields.Field()
    sender_id = fields.Field()
    text = fields.Field()
    recipient_id = fields.Field()
    created_at = fields.Field()
    sender_screen_name = fields.Field()
    recipient_screen_name = fields.Field()
    sender = fields.Object(User)
    recipient = fields.Object(User)

    def __unicode__(self):
        return u"%s: %s" % (self.sender.screen_name, self.text)


class Status(RemoteObject):

    """A Twitter update.

    Statuses can be fetched from
    ``http://twitter.com/statuses/show/<id>.json``.

    """

    created_at = fields.Field()
    id = fields.Field()
    text = fields.Field()
    source = fields.Field()
    truncated = fields.Field()
    in_reply_to_status_id = fields.Field()
    in_reply_to_user_id = fields.Field()
    in_reply_to_screen_name = fields.Field()
    favorited = fields.Field()
    user = fields.Object(User)

    @classmethod
    def get_status(cls, id, http=None):
        return cls.get(urljoin(Twitter.endpoint, "/statuses/show/%d.json" % int(id)), http=http)

    def __unicode__(self):
        return u"%s: %s" % (self.user.screen_name, self.text)


class DirectMessageList(ListObject):

    entries = fields.List(fields.Object(DirectMessage))

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

    """A user agent for interacting with Twitter.

    Instances of this class are full ``httplib2.Http`` HTTP user agent
    objects, but provide convenient convenience methods for interacting with
    Twitter and its data objects.

    """

    endpoint = 'http://twitter.com/'

    def public_timeline(self):
        return Timeline.public(http=self)

    def friends_timeline(self, **kwargs):
        return Timeline.friends(http=self, **kwargs)

    def user_timeline(self, **kwargs):
        return Timeline.user(http=self, **kwargs)

    def show(self, id):
        return Status.get_status(id, http=self)

    def user(self, id, **kwargs):
        return User.get_user(http=self, **kwargs)

    def mentions(self, **kwargs):
        return Timeline.mentions(http=self, **kwargs)

    def friends(self, **kwargs):
        return UserList.get_friends(http=self, **kwargs)

    def direct_messages_received(self, **kwargs):
        return DirectMessageList.get_messages(http=self, **kwargs)

    def direct_messages_sent(self, **kwargs):
        return DirectMessageList.get_messages_sent(http=self, **kwargs)


def show_public(twitter):
    print "## Public timeline ##"
    for tweet in twitter.public_timeline():
        print unicode(tweet)


def show_dms(twitter):
    print "## Direct messages sent to me ##"
    for dm in twitter.direct_messages_received():
        print unicode(dm)


def show_friends(twitter):
    print "## Tweets from my friends ##"
    for tweet in twitter.friends_timeline():
        print unicode(tweet)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser()
    parser.add_option("-u", "--username", dest="username",
        help="name of user for authentication")
    parser.add_option("--public", action="store_const", const=show_public,
        dest="action", default=show_public,
        help="Show tweets from the public timeline")
    parser.add_option("--dms", action="store_const", const=show_dms,
        dest="action", help="Show DMs sent to you (requires -u)")
    parser.add_option("--friends", action="store_const", const=show_friends,
        dest="action", help="Show your friends' recent tweets (requires -u)")
    opts, args = parser.parse_args()

    twitter = Twitter()

    # We'll use regular HTTP authentication, so ask for a password and add
    # it in the regular httplib2 way.
    if opts.username is not None:
        password = raw_input("Password (will echo): ")
        twitter.add_credentials(opts.username, password)

    try:
        print
        opts.action(twitter)
        print
    except httplib.HTTPException, exc:
        # The API could be down, or the credentials on an auth-only request
        # could be wrong, so show the error to the end user.
        print >>sys.stderr, "Error making request: %s: %s" \
            % (type(exc).__name__, str(exc))
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
