import re
from hashlib import md5
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import defaultdict
from time import sleep

longest_page = ('Temp', -1)
common_words = defaultdict(int)
subdomain_freqs = defaultdict(int)
blacklist_urls = set()
visited_urls = set()
robot_parse_links = dict()
seen_content_hashes = set()
stopwords = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers",
    "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its",
    "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their",
    "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves"
}


def scraper(url, resp):
    if resp.status == 200:
        if is_exact_duplicate(resp):
            blacklist_urls.add(url)
            return []
        
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    ##for this page -> tokenize, check if the longest page tuple needs to update, update common_words_freq
    if resp.status == 200 and url not in blacklist_urls:
        token_list = tokenize_html(resp)
        _longest_page_check(url, len(token_list))
        _count_tokens(token_list)
        
        print_report()
    return valid_links

def is_exact_duplicate(resp):
    """
    Check if page is exact duplicate
    """
    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        
        text = soup.get_text()
        
        text = ' '.join(text.split())
        
        content_hash = md5(text.encode('utf-8')).hexdigest()
        
        if content_hash in seen_content_hashes:
            return True
        
        seen_content_hashes.add(content_hash)
        return False
        
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return False
    
def extract_subdomain(url):
    '''
    Used to extract subdomains from urls to count how much each subdomain has been visited
    '''
    subdomain_pattern = r'https?://([^/]+)\.uci\.edu'
    match = re.search(subdomain_pattern, url)
    if not match:
        return
    
    subdomain = match.group(1).lower()
    # domain = match.group(2)

    if subdomain == 'www':
        return
    
    full_url = f'{subdomain}.uci.edu'
    subdomain_freqs[full_url] += 1

def long_enough_page(resp):
    '''
    Checks if page is long enough to scrape(small pages should be skipped)
    '''
    tokens = tokenize_html(resp)
    if len(tokens) <= 200:
        return False
    return True

def _tokenize_helper(text: str):
    '''
    tokenization function to get counts of word frequencies from each page
    '''
    token_list = []
    alphanumeric_set = {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
                                'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
    cur_token = ''
    for line in text.splitlines():
        for char in line.lower():
            if char in alphanumeric_set:
                cur_token += char
            else:
                if cur_token:
                    token_list.append("".join(cur_token))
                cur_token = ''
    if cur_token:
        token_list.append(cur_token)
    return token_list

def tokenize_html(resp):
    '''
    Tokenizes the html response
    '''
    try:
        bs_parser = BeautifulSoup(resp.raw_response.content, features='html.parser')
        tokens = _tokenize_helper(bs_parser.get_text())
    except AttributeError:
        return []
    return tokens

def _count_tokens(token_list):
    for token in token_list:
        if len(token) > 2 and token not in stopwords:
            common_words[token] += 1

def _longest_page_check(url, page_length):
    global longest_page
    if page_length > longest_page[1]:
        longest_page = (url, page_length)


def extract_next_links(url, resp):
    next_links = set()
    if resp.status != 200 or url in blacklist_urls:
        blacklist_urls.add(url)
        return []
    
    if url in visited_urls:
        return []
    
    extract_subdomain(url) ##get subdomain urls dict updated

    visited_urls.add(url)  

    parsed = urlparse(url)
    path = parsed.path 
    
    #links to uploaded documents/downloads, not crawlable content
    if "/files/" in path or "/sampledata/" in path:
        blacklist_urls.add(url)
        return []


    #check if page has enough content
    if not long_enough_page(resp):
        blacklist_urls.add(url)
        return []
    
    soup = BeautifulSoup(resp.raw_response.content, features='html.parser')

    #find all links, if href tags point to something, add them
    anchors = soup.find_all('a')
    for anchor in anchors:
        href = anchor.get('href')
        if href:
            parsed = urlparse(url)
            if parsed.scheme:
                href = urljoin(url, href)
            
        #delete fragment from url
            href = href.split('#')[0]
            if "archive" in href:
                href = href.split("?")[0]


            if is_valid(href):
                next_links.add(href)
    return next_links

    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

def print_report():
    '''
    Saves crawler data to report .txt file
    '''
    with open ("crawlerReport.txt", 'w') as report:
        report.write(f"Unique Pages:  {len(visited_urls)}\n\n\n")

        report.write(f"Longest Page:  {longest_page[0]} is {longest_page[1]} tokens long\n\n\n")

        report.write(f"Top 50 most frequent words: \n")
        top50_common_words = sorted(
            common_words.items(),
            key=lambda item: item[1],
            reverse=True
        )[:50]

        for word, freq in top50_common_words:
            report.write(f"{word}: {freq}\n")
        
        report.write("\n\n\n")

        report.write(f"Subdomain Frequencies:\n")
        for subdomain in sorted(subdomain_freqs):
            report.write(f"{subdomain}, {subdomain_freqs[subdomain]}\n")

# def robot_check(url): 
#     try:   
#         parsed = urlparse(url)
#     except Exception:
#         return False
#     robots_link = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
#     if robots_link not in robot_parse_links:
#         sleep(0.5) #politeness
#         try:
#             rp = RobotFileParser()
#             rp.set_url(robots_link)
#             rp.read()
#             robot_parse_links[robots_link] = rp
#         except Exception:
#             return False

#     return robot_parse_links[robots_link].can_fetch("*", url)
    
def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    if url in visited_urls or url in blacklist_urls:
        return False
    try:
        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False
        
        
        netloc = parsed.netloc
        path = parsed.path
        query = parsed.query

        #data files often come from this path, very large downloads with no value
        if "/supplement/" in path.lower():
            return False
        
        #from wiki.ics.uci.edu/doku.php/projects...?do= leading to crawler trap
        if "do=" in query:
            return False


        #from multiple runs -> lots of calendar traps & event traps
        trap_patterns = [
            r'/events?/.*\d{4}-\d{2}-\d{2}',
            r'/events?/.*\d{4}-\d{2}(?:/|$)',      
            r'/events?/.*\d{4}/\d{2}/\d{2}',
            r'/events?/.*\d{4}/\d{2}(?:/|$)',
            r'/calendar/',
            r'eventDate',
            r'tribe-bar-date',
            r'ical'
        ]
        
        full_url = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
        if any(re.search(pattern, full_url) for pattern in trap_patterns):
            return False

        allowed_domains = (
            '.ics.uci.edu',
            '.cs.uci.edu',
            '.informatics.uci.edu',
            '.stat.uci.edu'
        )

        if not any(domain in netloc for domain in allowed_domains):
            return False

        ##ban common url traps with regex -> calendar traps, repeating directory traps
        #https://support.archive-it.org/hc/en-us/articles/208332963-Modify-crawl-scope-with-a-Regular-Expression#InvalidURLs

        if re.match(r"^.*calendar.*$", path):
            return False
        if re.match(r"^.*?(/.+?/).*?\1.*$|^.*?/(.+?/)\2.*$", path):
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            #some common file types that can't be properly scraped/crawled
            + r"img|sql|odc|txt|war|apk|mpg|scm|ps\.z|rss|c|tex\.z|bib\.z|pps|bib|ppsx|ff|ma"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        raise
