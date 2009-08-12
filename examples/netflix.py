from urllib import urlencode
from urlparse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

from django.conf import settings
from oauth import OAuthConsumer
from oauthclient import NetflixHttp
from remoteobjects import RemoteObject, fields

from library.conduit.models.base import Conduit, Result


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


class Title(Flixject, Result):

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

    def save_asset(self):
        pass


class Netflix(Conduit):

    @classmethod
    def lookup(cls, id):
        return Title()
        pass

    @classmethod
    def search(cls, **kwargs):
        pass
