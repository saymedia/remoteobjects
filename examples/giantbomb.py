from cgi import parse_qs
from datetime import datetime
import time
from urllib import urlencode
from urlparse import urljoin, urlparse, urlunparse

from django.conf import settings
from google.appengine.api.urlfetch import fetch
from google.appengine.api import images
from remoteobjects import RemoteObject, fields

import api.encoder
from library.conduit import conduits
from library.conduit.models.base import Conduit, Result
from library.models import Asset, Link


class Bombdate(fields.Field):

    timestamp_format = '%Y-%m-%d %H:%M:%S'

    def decode(self, value):
        try:
            return datetime(*(time.strptime(value, self.timestamp_format))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return value.replace(microsecond=0).strftime(self.timestamp_format)


class Bombject(RemoteObject):

    content_types = ('application/json', 'text/javascript')

    @classmethod
    def get(cls, url, **kwargs):
        if not urlparse(url)[1]:
            url = urljoin('http://api.giantbomb.com/', url)

        self = super(Bombject, cls).get(url, **kwargs)
        self = self.filter(api_key=settings.GIANT_BOMB_KEY, format='json')
        return self

    def filter(self, **kwargs):
        url = self._location
        parts = list(urlparse(url))
        query = parse_qs(parts[4])
        query = dict([(k, v[0]) for k, v in query.iteritems()])

        for k, v in kwargs.iteritems():
            if v is None and k in query:
                del query[k]
            else:
                query[k] = v

        parts[4] = urlencode(query)
        url = urlunparse(parts)
        return super(Bombject, self).get(url)


class Image(Bombject):
    tiny_url = fields.Field()
    small_url = fields.Field()
    thumb_url = fields.Field()
    screen_url = fields.Field()
    super_url = fields.Field()


class Game(Bombject, Result):

    id = fields.Field()
    name = fields.Field()
    api_detail_url = fields.Field()
    site_detail_url = fields.Field()

    summary = fields.Field(api_name='deck')
    description = fields.Field()
    image = fields.Object(Image)
    published = Bombdate(api_name='date_added')
    updated = Bombdate(api_name='date_last_updated')

    characters = fields.Field()
    concepts = fields.Field()
    developers = fields.Field()
    platforms = fields.Field()
    publishers = fields.Field()

    links = ()

    @classmethod
    def get(cls, url, **kwargs):
        res = GameResult.get(url)
        res = res.filter()
        return res.results[0]

    def update_from_dict(self, data):
        super(Game, self).update_from_dict(data)

        link = Link(
            rel="alternate",
            content_type="text/html",
            href=self.site_detail_url,
        )
        self.links = [link]

        if self.image:
            for urlspec in ('super_url', 'thumb_url', 'small_url'):
                url = getattr(self.image, urlspec)

                # Get it.
                resp = fetch(url)
                image = images.Image(resp.content)

                self.links.append(Link(
                    rel="thumbnail",
                    content_type="image/jpeg",
                    href=url,
                    width=image.width,
                    height=image.height,
                ))

    def save_asset(self):
        asset = Asset(
            object_type=Asset.object_types.game,
            title=self.name,
            content=self.summary,
            content_type='text/markdown',
            privacy_groups=['public'],
            published=self.published,
            updated=self.updated,
        )
        asset.save()

        for link in self.links:
            link.asset = asset
            link.save()

        return asset


class GameResult(Bombject):

    status_code = fields.Field()
    error = fields.Field()
    total = fields.Field(api_name='number_of_total_results')
    count = fields.Field(api_name='number_of_page_results')
    limit = fields.Field()
    offset = fields.Field()
    results = fields.List(fields.Object(Game))

    def update_from_dict(self, data):
        if not isinstance(data['results'], list):
            data = dict(data)
            data['results'] = [data['results']]
        super(GameResult, self).update_from_dict(data)


class GiantBomb(Conduit):

    @classmethod
    def lookup(cls, id):
        return Game.get('/game/%s/' % (id,))

    @classmethod
    def search(cls, query=None):
        assert query is not None
        obj = GameResult.get('/search/').filter(resources='game')
        obj = obj.filter(query=query)
        return obj.results


conduits.add(GiantBomb)

api.encoder.register(RemoteObject, 'to_dict')
