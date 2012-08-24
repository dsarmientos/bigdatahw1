import feedparser
import re
import sys
import urllib2

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.shortcuts import render_to_response

sys.path.insert(0, '/home/daniel/Desktop/zorba-2.5.0/build/swig/python')
import zorba_api


def home(request):
    titles = []
    parsed_feeds = get_parsed_feeds()
    for feed in parsed_feeds:
        titles.extend(
            map(lambda n: '%s' % n['title'],
                feed['items']))
    return render_to_response('index.html', {'titulos': titles})


def get_parsed_feeds():
    feeds_xml = get_feeds_xml()
    parsed_feeds = []
    for feed_xml in feeds_xml:
        parsed_feeds.append(feedparser.parse(feed_xml))
    return parsed_feeds


def filtro_regex(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace')
    filter_regex = r'(<title>[^<]*?%(keyword)s[^<]*?</title>|' \
                   '<description>[^<]*?%(keyword)s[^<]*?</description>|' \
                   '<category[^>]*?>[^<]*?%(keyword)s[^<]*?</category>)' % (
                   {'keyword': keyword})
    keyword_filter = re.compile(filter_regex, re.DOTALL | re.IGNORECASE)
    item_regex = re.compile(r'<item>(?P<item>.*?)</item>', re.DOTALL)
    titles = []
    for feed_xml in get_feeds_xml():
        for match in item_regex.finditer(feed_xml):
            item_xml = match.group('item')
            if keyword_filter.search(item_xml) is not None:
                title = re.search(r'<title>(.*?)</title>', item_xml).group(1)
                titles.append(title)
    return HttpResponse(simplejson.dumps({'titles': titles}),
                        mimetype='application/json')


def filtro_xquery(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    zorba, store, dataManager, docManager = init_zorba()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace').lower()
    xquery = build_xquery(zorba, keyword)
    results = []
    for xml in get_feeds_xml():
        docManager.put("rss.xml", build_doc(dataManager, xml))
        results.append(xquery.execute())
        docManager.remove("rss.xml")
    shutdown_zorba(zorba, store)
    return HttpResponse(results, mimetype='text/html')


def init_zorba():
    store = zorba_api.InMemoryStore_getInstance()
    zorba = zorba_api.Zorba_getInstance(store)
    dataManager = zorba.getXmlDataManager()
    docManager = dataManager.getDocumentManager()
    return zorba, store, dataManager, docManager


def build_xquery(zorba, keyword):
    # contains($item/category, "%(kw)s") does not work: more than one category
    query = r'for $item in doc("rss.xml")//item ' \
            'let $title := lower-case($item/title) ' \
            'where contains($title, "%(kw)s") or ' \
            'contains($item/description, "%(kw)s") ' \
            'return <tr><td>{data($item/title)}</td>' \
            '<td>{data($item/pubDate)}</td><td>' \
            '<a href="{data($item/link)}">Ver</a>' \
            '</td></tr>' % {'kw': keyword}
    return zorba.compileQuery(query)


def build_doc(dataManager, xml):
    docIter = dataManager.parseXML(xml)
    docIter.open()
    doc = zorba_api.Item_createEmptyItem()
    docIter.next(doc)
    docIter.close()
    docIter.destroy()
    return doc


def shutdown_zorba(zorba, store):
    zorba.shutdown()
    zorba_api.InMemoryStore_shutdown(store)


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
    feed = urllib2.urlopen(feed_url)
    xml = feed.read()
    feed.close()
    return xml
