#!/usr/bin/env python

"""

An example Netflix API client, implemented using remoteobjects.

"""

__version__ = '1.0'
__date__ = '25 August 2009'
__author__ = 'Mark Paschal'


import sys
from urllib import urlencode
from urlparse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from oauth import OAuthConsumer
from oauthclient import NetflixHttp

from remoteobjects import RemoteObject, fields


class Flixject(RemoteObject):

    content_types = ('text/xml', 'application/xml')

    @classmethod
    def http(cls, access_token=None):
        h = NetflixHttp()
        h.consumer = OAuthConsumer(*settings.NETFLIX_KEY)
        h.add_credentials(h.consumer, access_token, domain="api.netflix.com")
        return h

    @classmethod
    def get(cls, url, **kwargs):
        if not urlparse(url)[1]:
            url = urljoin('https://api.netflix.com/', url)

        return super(Flixject, cls).get(url, http=cls.http(), **kwargs)

    def update_from_tree(self, tree):
        data = dict((k, v(tree)) for k, v in self.decoder_ring.items())
        self.update_from_dict(data)

    def update_from_response(self, url, response, content):
        self.raise_for_response(url, response, content)

        tree = ElementTree.fromstring(content)
        self.update_from_tree(tree)


class Title(Flixject):

    api_url = fields.Field()
    title   = fields.Field()
    link    = fields.Field()
    thumb   = fields.Field()

    decoder_ring = {
        'title': lambda x: x.find('title').get('regular'),
        'link':  lambda x: [j for j in x.findall('link') if j.get('rel') == 'alternate'][0].get('href'),
        'thumb': lambda x: x.find('box_art').get('large'),
        'api_url': lambda x: x.find('id'),
    }


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser()
    parser.add_option("-k", "--key", dest="key",
        help="Netflix API key (required)")
    parser.add_option("-s", "--secret", dest="secret",
        help="Netflix API shared secret (required)")
    opts, args = parser.parse_args()

    if opts.key is None or opts.secret is None:
        print >>sys.stderr, "Options --key and --secret are required"
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
