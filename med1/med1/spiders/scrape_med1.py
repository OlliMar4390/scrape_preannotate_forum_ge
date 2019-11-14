# scrape all threads of the med1.de forum, subject 'Nierenkrankheiten'
# one post, one dictionary
# scrapy crawl med1.2 -o med1.2.jl

import scrapy
import time


class Med1Spider(scrapy.Spider):
    name = 'med1.2'
    start_urls = [
        'https://www.med1.de/forum/nierenerkrankungen/',
    ]

    def parse(self, response):
        # follow links to Beiträgen
        for href in response.css('a.messageGroupLink::attr(href)'):
            yield response.follow(href, self.parse_beitraege)

        # follow pagination links
        for href in response.css('li.skip a.fa-chevron-right::attr(href)'):
            yield response.follow(href, self.parse)

    def parse_beitraege(self, response):
        for article in response.css('article'):
            item_id = article.css('::attr(itemid)').extract_first()
            if item_id is not None:
                parts = item_id.split('?')
                thread_id = parts[0]
                yield {
                    'username': article.css('span.username::text').extract_first(),
                    'thread-title': response.css('li.active::attr(title)').extract_first(),  # just nice to have
                    'post-html': article.css('div.messageText').extract_first(),
                    'item-id': item_id,
                    'time-of-download': time.strftime('%d.%m.%Y %H:%M:%S'),
                    'thread-id': thread_id,
                }
            # NOTE: Assume that articles without attribute 'itemid' are replications of thread starter posts on
            #       paginated pages (on page 2 etc.) or meta commentaries ('Subject name was changed' etc).
            # else:
            #    print('WARNING: no itemid found for '%s'' % response.url)

        next_page = response.css('li.skip a.fa-chevron-right::attr(href)').extract_first()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse_beitraege)
