import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from collections import defaultdict


longest_page = ('Temp', -1)
common_words = defaultdict(int)
subdomain_freqs = defaultdict(int)
blacklist_urls = set()
visited_urls = set()
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
    print('init scraper')
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    ##for this page -> tokenize, check if the longest page tuple needs to update, update common_words_freq
    if resp.status == 200:
        if url not in blacklist_urls:
            token_list = tokenize_html(resp)
            _longest_page_check(url, len(token_list))
            _count_tokens(token_list)

    return valid_links


def extract_subdomain(url):
    '''
    Used to extract subdomains from urls to count how much each subdomain has been visited
    '''
    subdomain_pattern = r'https?://([^/]+)\.(ics|cs|informatics|stat)\.uci\.edu'
    match = re.search(subdomain_pattern, url)
    if not match:
        return
    
    subdomain = match.group(1).lower()
    domain = match.group(2)

    if subdomain == 'www':
        return
    
    full_url = f'http://{subdomain}.{domain}.uci.edu'
    subdomain_freqs[full_url] += 1


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
    try:
        bs_parser = BeautifulSoup(resp.raw_response.content, 'html')
        tokens = _tokenize_helper(bs_parser.get_text())
    except AttributeError:
        return []
    return tokens

def _count_tokens(token_list):
    for token in token_list:
        if len(token) > 2 and token not in stopwords:
            common_words[token] += 1

def _longest_page_check(url, page_length):
    if page_length > longest_page[1]:
        longest_page = (url, page_length)


def extract_next_links(url, resp):
    next_links = set()
    if resp.status != 200 or url in blacklist_urls or url in visited_urls:
        blacklist_urls.add(url)
        return []
    
    print('just finished response validity check')
    extract_subdomain(url) ##get subdomain urls dict updated

    visited_urls.add(url)    

    soup = BeautifulSoup(resp.raw_response.content, 'html')
    print('soup parser initialized')


    anchors = soup.find_all('a')
    for anchor in anchors:
        print(f'Anchor: {anchor}')
        href = anchor.get('href')
        if href:
            parsed = urlparse(url)
            if parsed.scheme:
                href = urljoin(url, href)
            
        #delete fragment from url
        href = href.split('#')[0]


        if is_valid(href):
            next_links.add(href)
    print('found all anchor links')
    return next_links

    print(f'URL: {resp.raw_response.url}')
    print(f'Content: {resp.raw_response.content}')
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|txt"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        raise
