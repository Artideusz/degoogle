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

    def __init__(self, queries=[], pages=1, offset=0, time_window='a', exclude_junk=True, headers=None, all_pages=False, delay=1000, verbose=False, no_banner=False):
        self.queries = queries
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

    def get_page(self, query, page, offset):
        pg = (page * 10) + (offset * 10) # offset factored in
        # since the digit piece is variable, i can't use argparse.choices :(
        if (self.time_window[0] not in ('a', 'd', 'h', 'm', 'n', 'w', 'y')) or (len(self.time_window) > 1 and not self.time_window[1:].isdigit()):
            raise Exception("Time window cannot be {}. Available options: 'a', 'd', 'h', 'm', 'n', 'w', 'y'".format(self.time_window))

        normalized_query = re.sub(r' |%20', '+', query)
        normalized_query = re.sub(r'"|\"', '%22', normalized_query)
        url = f"https://google.com/search?start={pg}&tbs=qdr:{self.time_window}&q={normalized_query}&filter=0"

        self.verbose_log(url)

        return requests.get(url, headers=self.headers)

    def extract_links(self, page_content):
        page_tree = html.fromstring(page_content)
        link_elements = page_tree.cssselect("div.g")

        res = []
        
        for i in range(0, len(link_elements)):
            url = link_elements[i].cssselect("a[data-usg]")[0].get("href")
            if not link_elements[i].cssselect("div[data-content-feature='1'] > div:nth-child(1)") and not link_elements[i].cssselect("div[data-content-feature='2'] > div:nth-child(1)"):
                desc = "No description"
            else:
                desc = (
                    link_elements[i].cssselect("div[data-content-feature='1'] > div:nth-child(1)") or 
                    link_elements[i].cssselect("div[data-content-feature='2'] > div:nth-child(1)")
                )[0].text_content()
            
            res.append({
                "url": url,
                "desc": desc
                }
            )
        return res


    def run(self):
        if not self.no_banner:
            self.show_banner()
        
        self.verbose_log("""
Current options:
Queries: {}
Pages: {}
Offset: {}
Delay: {}ms
""".format(self.queries, self.pages, self.offset, self.delay))
        
        if not self.queries:
            print("Error: Query not specified.")
            return
        
        results = []

        for query in self.queries:
            self.verbose_log("--- Current query: {} ---".format(query))
            results.append(
                {
                    "query": query,
                    "links": []
                }
            )
            page = 0
            while True:
                if page >= self.pages and not self.is_all_pages:
                    break
                
                self.verbose_log("Current page: {}".format(page + 1 + self.offset))
                
                r = self.get_page(query, page, self.offset)
                extracted_links = self.extract_links(r.text)
                results[len(results)-1]['links'] = results[len(results)-1]['links'] + extracted_links
                
                self.verbose_log("Links extracted: {}".format(len(extracted_links)))
                self.verbose_log("Links total: {}\n".format(len(results[len(results)-1]['links'])))
                
                if not extracted_links:
                    self.verbose_log("No more links")
                    break
                
                page += 1
                time.sleep(self.delay / 1000)

        return results

def parse_args():
    """Parse command line interface arguments."""
    parser = argparse.ArgumentParser(
        description="Search and extract google results.", prog="degoogle"
    )
    parser.add_argument('queries', nargs="+", type=str, help='search queries')
    parser.add_argument('--offset', dest='offset', type=int, default=0, help='page offset to start from')
    parser.add_argument('-p', '--pages', dest='pages', type=int, default=1, help='specify multiple pages')
    parser.add_argument('-A', '--all-pages', dest='all_pages', action="store_true", help='get all pages available. (bigger priority than -p)')
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
 
    dg1 = dg(args.queries, pages=args.pages, offset=args.offset, time_window=args.time_window, exclude_junk=args.exclude_junk, headers=args.headers, delay=args.delay, verbose=args.verbose, no_banner=args.no_banner, all_pages=args.all_pages)
    search_results = dg1.run()
    
    if not search_results:
        print("no results")
    else:
        final_string = "-- %i results --\n\n" % len(search_results)
        for result in search_results:
            final_string += "-- Query: {} --\n".format(result['query'])
            for link in result['links']:
                final_string += link['url'] + '\n'
                if not args.url_only:
                    final_string += link['desc'] + '\n'
                    final_string += "\n"
            final_string += "\n"

        if final_string[-2:] == '\n\n':
            final_string = final_string[:-2]
        
        print(final_string)


if __name__ == '__main__':
    main()