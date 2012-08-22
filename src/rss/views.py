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
    return render_to_response('index.html', {'titulos':titles})

    feeds_xml = get_feeds_xml()
    parsed_feeds = []
    for feed_xml in feeds_xml:
        parsed_feeds.append(feedparser.parse(feed_xml))
    return parsed_feeds


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
                   {'keyword':keyword})
    keyword_filter = re.compile(filter_regex, re.DOTALL|re.IGNORECASE)
    item_regex = re.compile(r'<item>(?P<item>.*?)</item>',re.DOTALL)
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
    store = zorba_api.InMemoryStore_getInstance()
    zorba = zorba_api.Zorba_getInstance(store)

    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace')
    results = []
    xml_ = join_feeds_xml(get_feeds_xml())
    for xml in [xml_]:
        dataManager = zorba.getXmlDataManager()
        docIter = dataManager.parseXML(xml)
        docIter.open();
        doc = zorba_api.Item_createEmptyItem()
        docIter.next(doc)
        docIter.close()
        docIter.destroy()
        query = r'for $item in doc("rss.xml")//item ' \
            'return <tr><td>{data($item/title)}</td>' \
            '<td>{data($item/pubDate)}</td><td>' \
            '<a href="{data($item/link)}">Ver</a></td></tr>'
        xquery = zorba.compileQuery(query)
        docManager = dataManager.getDocumentManager()
        docManager.put("rss.xml", doc)
        results.append(xquery.execute())
    zorba.shutdown()
    zorba_api.InMemoryStore_shutdown(store)
    print results

    return HttpResponse(results, mimetype='text/html')


def join_feeds_xml(feeds_xml):
    with open(
        '/home/daniel/Documents/big_data/tarea1/src/rss/jrss.xml',
        'r') as infile:
        return infile.read()



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


