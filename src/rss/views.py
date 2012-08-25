#encoding=utf-8

import chardet
import feedparser
import re
import sys
import urllib2
import pdb
import HTMLParser

import simplexquery as sxq
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.shortcuts import render_to_response

class Resolver(object):
    def __init__(self, xml):
        encoding = chardet.detect(xml)['encoding']
        print encoding
        if encoding != 'utf-8':
            encoding = 'iso8859-1'
        uxml = xml.decode(encoding)
        self.xml = uxml

    def __call__(self, uri):
        return self.xml.encode('ascii', 'xmlcharrefreplace')


def home(request):
    titles = []
    parsed_feeds = get_parsed_feeds()
    for feed in parsed_feeds:
        titles.extend(['%s' % item['title'] for item in feed['items']])
    return render_to_response('index.html', {'titulos': titles})


def filtro_regex(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace')
    print keyword
    filter_regex = build_filter_regex(keyword)
    item_regex = re.compile('<item>(?P<item>.*?)</item>', re.DOTALL)
    title_regex = re.compile('<title>(.*?)</title>')
    titles = []
    for feed_xml in get_feeds_xml():
        encoding = chardet.detect(feed_xml)['encoding']
        if encoding != 'utf-8':
            encoding = 'iso8859-1'
        for match in item_regex.finditer(feed_xml):
            item_xml = match.group('item')
            if filter_regex.search(item_xml) is not None:
                title = title_regex.search(item_xml).group(1)
                title = title.decode(encoding).encode('utf-8')
                titles.append(title)
    return HttpResponse(simplejson.dumps({'titles': titles}),
                        mimetype='application/json')


def filtro_xquery(request):
    if request.method != 'GET' or 'q'not in request.GET:
        return HttpResponseBadRequest()
    keyword = request.GET['q'].encode('ascii', 'xmlcharrefreplace').lower()
    query = build_query(keyword)
    items = []
    pp = HTMLParser.HTMLParser()
    for xml in get_feeds_xml():
        results = sxq.execute_all(query, resolver=Resolver(xml))
        if results:
            items.extend(results)
    return HttpResponse(results, mimetype='text/html')


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
