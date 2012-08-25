import feedparser
import re
import urllib2

import simplexquery
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.shortcuts import render_to_response


class Resolver(object):
    def __init__(self, xml):
        self.xml = decode_xml(xml)

    def __call__(self, uri):
        return self.xml.encode('ascii', 'xmlcharrefreplace')


def home(request):
    titles = []
    parsed_feeds = get_parsed_feeds()
    for feed in parsed_feeds:
        titles.extend([item['title'] for item in feed['items']])
    return render_to_response('index.html', {'titulos': titles})


def filtro_regex(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace')
    filter_regex = build_filter_regex(keyword)
    item_regex = re.compile('<item>(?P<item>.*?)</item>', re.DOTALL)
    title_regex = re.compile('<title>(.*?)</title>')
    titles = []
    for feed_xml in get_feeds_xml():
        for match in item_regex.finditer(feed_xml):
            item_xml = match.group('item')
            if filter_regex.search(item_xml):
                title = title_regex.search(item_xml).group(1)
                titles.append(title)
    return HttpResponse(simplejson.dumps({'titles': titles}),
                        mimetype='application/json')


def filtro_xquery(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace').lower()
    query = build_query(keyword)
    items = []
    for xml in get_feeds_xml():
        results = simplexquery.execute_all(query, resolver=Resolver(xml))
        if results:
            items.extend(results)
    return HttpResponse(items, mimetype='text/html')


def get_parsed_feeds():
    feeds_xml = get_feeds_xml()
    parsed_feeds = []
    for feed_xml in feeds_xml:
        parsed_feeds.append(feedparser.parse(feed_xml))
    return parsed_feeds


def get_feeds_xml():
    feeds_urls = ('http://www.eltiempo.com/tecnologia/rss.xml',
                  'http://www.eltiempo.com/deportes/rss.xml',
                  'http://feeds.nytimes.com/nyt/rss/Technology',
                  'http://www.nytimes.com/services/xml/rss/nyt/Sports.xml',)
    feeds_xml = []
    for feed_url in feeds_urls:
        feed_xml = cache.get(feed_url)
        if feed_xml is None:
            feed_xml = get_feed_xml(feed_url)
            cache.set(feed_url, feed_xml)
        feeds_xml.append(feed_xml)
    return feeds_xml


def get_feed_xml(feed_url):
    request = urllib2.urlopen(feed_url)
    xml = request.read()
    request.close()
    return xml


def build_filter_regex(keyword):
    filter_regex = (
        '(<title>[^<]*?%(keyword)s[^<]*?</title>|'
        '<description>[^<]*?%(keyword)s[^<]*?</description>|'
        '<category[^>]*?>[^<]*?%(keyword)s[^<]*?</category>)') % (
            {'keyword': re.escape(keyword)})
    return re.compile(filter_regex, re.DOTALL | re.IGNORECASE)


def build_query(keyword):
    query = (
        'for $item in doc("rss.xml")//item '
        'let $title := lower-case($item/title) '
        'let $description := lower-case($item/description) '
        'where contains($description, "%(kw)s") or '
            'contains($title, "%(kw)s") or ('
            'some $category in $item/category '
            'satisfies contains(lower-case($category), "%(kw)s"))'
        'return <tr>'
            '<td>{data($item/title)}</td>'
            '<td>{data($item/pubDate)}</td>'
            '<td><a href="{data($item/link)}">Ver</a></td>'
        '</tr>') % {'kw': keyword}
    return query


def decode_xml(xml):
    # Se deberia obtener del xml del feed, pero por simplicidad y porque
    # se conoce la codificacion de los archivos, se hace asi:
    try:
        uxml = xml.decode('utf-8')
    except UnicodeDecodeError:
        uxml = xml.decode('iso8859-1')
    return uxml
