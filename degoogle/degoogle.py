#!/usr/bin/env python3

import argparse
import re
import requests
from lxml import html
import time

class dg():

    # for excluding youtube, quora, facebook results
    # disable with -j flag, or overwrite default by setting exclude_junk's action to store_true
    junk_strings = ['facebook.com/', 'pinterest.com/', 'quora.com/', 'youtube.com/', 'youtu.be/']
    junk_exclusion = r"(?:" + "|".join(junk_strings).replace(".", "\.") + ")"

    def __init__(self, query="", pages=1, offset=0, time_window='a', exclude_junk=True, headers=None, all_pages=False, delay=1000, verbose=False, no_banner=False):
        self.query = query
        self.pages = pages
        self.offset = offset
        self.time_window = time_window
        self.exclude_junk = exclude_junk
        self.headers = self.get_headers(headers)
        self.is_all_pages = all_pages
        self.delay = delay
        self.verbose = verbose
        self.no_banner = no_banner
    
    def show_banner(self):
        return print("""
 ██████████              █████████                             ████          
░░███░░░░███            ███░░░░░███                           ░░███          
 ░███   ░░███  ██████  ███     ░░░   ██████   ██████   ███████ ░███   ██████ 
 ░███    ░███ ███░░███░███          ███░░███ ███░░███ ███░░███ ░███  ███░░███
 ░███    ░███░███████ ░███    █████░███ ░███░███ ░███░███ ░███ ░███ ░███████ 
 ░███    ███ ░███░░░  ░░███  ░░███ ░███ ░███░███ ░███░███ ░███ ░███ ░███░░░  
 ██████████  ░░██████  ░░█████████ ░░██████ ░░██████ ░░███████ █████░░██████ 
░░░░░░░░░░    ░░░░░░    ░░░░░░░░░   ░░░░░░   ░░░░░░   ░░░░░███░░░░░  ░░░░░░  
                                                      ███ ░███               
                                                     ░░██████                
                                                      ░░░░░░                 
""")
    
    def verbose_log(self, msg):
        if self.verbose:
            print(msg)
    
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

    def get_page(self, page, offset):
        pg = (page * 10) + (offset * 10) # offset factored in
        # since the digit piece is variable, i can't use argparse.choices :(
        if (self.time_window[0] not in ('a', 'd', 'h', 'm', 'n', 'w', 'y')) or (len(self.time_window) > 1 and not self.time_window[1:].isdigit()):
            raise Exception("Time window cannot be {}. Available options: 'a', 'd', 'h', 'm', 'n', 'w', 'y'".format(self.time_window))

        normalized_query = re.sub(r' |%20', '+', self.query)
        normalized_query = re.sub(r'"|\"', '%22', normalized_query)
        url = f"https://google.com/search?start={pg}&tbs=qdr:{self.time_window}&q={normalized_query}&filter=0"

        self.verbose_log(url)

        return requests.get(url, headers=self.headers)

    def extract_links(self, page_content):
        page_tree = html.fromstring(page_content)
        link_elements = page_tree.cssselect("div[data-sokoban-container]")

        # print([(
        #     link.cssselect("div[data-header-feature='0'] > div > a[data-usg]")[0].get('href'),
        #     link.cssselect("div[data-content-feature='1'] > div:nth-child(1)") or link.cssselect("div[data-content-feature='2'] > div:nth-child(1)")
        #     ) for link in link_elements])
        
        res = []
        
        for i in range(0, len(link_elements)):
            res.append({
                "url": link_elements[i].cssselect("div[data-header-feature='0'] > div > a[data-usg]")[0].get('href'),
                "desc": (
                    link_elements[i].cssselect("div[data-content-feature='1'] > div:nth-child(1)") 
                    or 
                    link_elements[i].cssselect("div[data-content-feature='2'] > div:nth-child(1)")
                    )[0].text_content()
                }
            )
        return res

    # for each page desired, run google search + grab result entries form page contents.. returns a list of entries
    def process_query(self):
        pages = []
        links = [] # 1 entry = 1 (url,description)

        # run the search for each desired page until (pages+offset) reached or until a page with no results is found
        page = 0
        while True:
            if page >= self.pages and not self.is_all_pages:
                break
            
            self.verbose_log("Current page: {}".format(page + 1 + self.offset))
            
            r = self.get_page(page, self.offset)
            extracted_links = self.extract_links(r.text)
            links = links + extracted_links
            
            print(len(links))
            
            if not extracted_links:
                self.verbose_log("No more links")
                break
            
            page += 1
            time.sleep(self.delay / 1000)

        return links

    def run(self):
        if not self.no_banner:
            self.show_banner()
        self.verbose_log("""
Current options:
Query: {}
Pages: {}
Offset: {}
Delay: {}ms
""".format(self.query, self.pages, self.offset, self.delay))
        
        if not self.query or self.query == "":
            print("Error: Query not specified.")
            return
        
        return self.process_query()

def parse_args():
    """Parse command line interface arguments."""
    parser = argparse.ArgumentParser(
        description="Search and extract google results.", prog="degoogle"
    )
    parser.add_argument('query', type=str, help='search query')
    parser.add_argument('-o', '--offset', dest='offset', type=int, default=0, help='page offset to start from')
    parser.add_argument('-p', '--pages', dest='pages', type=int, default=1, help='specify multiple pages')
    parser.add_argument('-A', '--all-pages', dest='all_pages', action="store_true", help='get all pages available. (bigger priority than -p)') # TODO
    parser.add_argument('-d', '--delay', dest='delay', type=int, default=1000, help='specify delay between requests in ms. (DEFAULT: 1000)')
    parser.add_argument('-t', '--time-window', dest='time_window', type=str, default='a', help='time window')
    parser.add_argument('--urls-only', dest='url_only', action='store_true', help='omit link description')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='show verbose output')
    parser.add_argument('--no-banner', dest='no_banner', action='store_true', help='do not show banner')
    parser.add_argument('-j', '--exclude-junk', dest='exclude_junk', action='store_false', help='exclude junk (yt, fb, quora)')
    parser.add_argument('-H', dest='headers', action='append', help='Add custom headers to the search request')
    return parser.parse_args()



def main():
    args = parse_args()
    
    dg1 = dg(args.query, pages=args.pages, offset=args.offset, time_window=args.time_window, exclude_junk=args.exclude_junk, headers=args.headers, delay=args.delay, verbose=args.verbose, no_banner=args.no_banner, all_pages=args.all_pages)
    search_results = dg1.run()
    
    if not search_results:
        print("no results")
    else:
        final_string = "-- %i results --\n\n" % len(search_results)
        for result in search_results:
            if not args.url_only:
                final_string += result['desc'] + '\n' 
            final_string += result['url'] + '\n\n'
        if final_string[-2:] == '\n\n':
            final_string = final_string[:-2]
        
        print(final_string)


if __name__ == '__main__':
    main()