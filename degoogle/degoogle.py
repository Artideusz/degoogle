#!/usr/bin/env python3

import argparse
import re

import requests
from lxml import html

# todo ####################
# > better junk exclusion
# > infile outfile
# > further filtering
# > max results? made redundant by pages? more useful if/when meaningful filtering options exist beyond junk_strings
# > also just make this not a hot mess anymore. what are exceptions?

class dg():

    # for excluding youtube, quora, facebook results
    # disable with -j flag, or overwrite default by setting exclude_junk's action to store_true
    junk_strings = ['facebook.com/', 'pinterest.com/', 'quora.com/', 'youtube.com/', 'youtu.be/']
    junk_exclusion = r"(?:" + "|".join(junk_strings).replace(".", "\.") + ")"

    def __init__(self, query="", pages=1, offset=0, time_window='a', exclude_junk=True, headers=None):
        self.query = query
        self.pages = pages
        self.offset = offset
        self.time_window = time_window
        self.exclude_junk = exclude_junk
        self.headers = self.get_headers(headers)

    def get_headers(self, custom_headers):
        res = {}
        if custom_headers:
            for header in custom_headers:
                kv = header.split(":")
                if(len(kv) == 1):
                    raise Exception("One or more headers do not have a ':' seperator!")
                res[kv[0].lower().strip()] = kv[1].strip()
        
        if not res.get('user-agent'):
            res['user-agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0" # Needed for getting a valid response

        return res

    # normalize + run search.. supports page, offset, timeframe (tbs parameter)
    def search(self, page):
        if not self.query:
            print("query needs to be set.")
            return
        pg = (self.offset*10) + (page*10) # offset factored in
        # since the digit piece is variable, i can't use argparse.choices :(
        if (self.time_window[0] not in ('a', 'd', 'h', 'm', 'n', 'w', 'y')) or (len(self.time_window) > 1 and not self.time_window[1:].isdigit()):
            # TODO meaningful output
            print("invalid time interval specified.")
            return()

        normalized_query = re.sub(r' |%20', '+', self.query)
        normalized_query = re.sub(r'"|\"', '%22', normalized_query)
        url = f"https://google.com/search?start={pg}&tbs=qdr:{self.time_window}&q={normalized_query}&filter=0"

        return requests.get(url, headers=self.headers)

    # for each page desired, run google search + grab result entries form page contents.. returns a list of entries
    def process_query(self):
        pages = []
        entries = [] # 1 entry = 1 (url,description)

        # run the search for each desired page until (pages+offset) reached or until a page with no results is found
        for page in range(0, self.pages):
            r = self.search(page)
            if "did not match any documents" in r.text: # no results on this page, we can skip those that follow
                break
            pages.append(r.text)

        # grab result entries on each page. they will still need to be split into url and description
        for page in pages:
            page_tree = html.fromstring(page)
            # FIXME: One selector should be used
            page_urls = page_tree.cssselect("div > div:nth-child(1) > div:nth-child(1) > div > a[data-usg]")
            page_desc = page_tree.cssselect("div[data-content-feature] > div:nth-child(1)")

            for i in range(0, len(page_urls)):
                entries.append({
                    "url": page_urls[i].get('href'), 
                    "desc": page_desc[i].text
                    }
                )
                # print((page_urls[i].get('href'), page_desc[i].text))

        return entries


    # dg.py "query matchthis -notthis filetype:whatever"
    # search google for your query and return search_results, all cleaned URLs + descriptions from each page
    def run(self):
        try:
            results = self.process_query()
            return results
        except Exception as e:
            print(e)
            return

def parse_args():
    """Parse command line interface arguments."""
    parser = argparse.ArgumentParser(
        description="Search and extract google results.", prog="degoogle"
    )
    parser.add_argument('query', type=str, help='search query')
    parser.add_argument('-o', '--offset', dest='offset', type=int, default=0, help='page offset to start from')
    parser.add_argument('-p', '--pages', dest='pages', type=int, default=1, help='specify multiple pages')
    parser.add_argument('-t', '--time-window', dest='time_window', type=str, default='a', help='time window')
    parser.add_argument('-j', '--exclude-junk', dest='exclude_junk', action='store_false', help='exclude junk (yt, fb, quora)')
    parser.add_argument('-H', dest='headers', action='append', help='Add custom headers to the search request')
    return parser.parse_args()

def main():
    args = parse_args()

################################################################################################
# example/demo output... erase me! VVV

    # usage: make a dg object to run queries through #

    # object using command line args
    dg1 = dg(args.query, args.pages, args.offset, args.time_window, args.exclude_junk, args.headers)

    # object with query set in constructor. note all other params have default values.. you can overwrite them or leave them alone
    dg2 = dg("dg2.query test")

    # if you want to run a sequence of queries but leave your other params the same,
    # you can use 1 dg instance and loop over your queries, setting googler.query = this_query then calling dg.run()

    search_results = dg1.run()
    #more_results = dg2.run()

    if not search_results:
        print("no results")
    else:
        final_string = "-- %i results --\n\n" % len(search_results)
        for result in search_results:
            final_string += result['desc'] + '\n' + result['url'] + '\n\n'
        if final_string[-2:] == '\n\n':
            final_string = final_string[:-2]
        print(final_string)
################################################################################################

if __name__ == '__main__':
    main()