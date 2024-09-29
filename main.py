from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import hashlib
import os

def init_driver(chrome_driver_path):
    service = Service(executable_path=chrome_driver_path)
    return webdriver.Chrome(service=service)

def scroll_to_end(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  
        last_height = new_height

def crawl(url, driver, output_file, depth=0, max_depth=3, visited_links=set(), content_hashes=set()):
    # check max depth 
    if depth > max_depth:
        return 
    
    try:
        driver.get(url)
    except Exception as e:
        print(f"Error loading {url}: {e}")
        return
    
    time.sleep(2)
    scroll_to_end(driver)

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # rm unnesserary tags
    for tag in soup(['img', 'video']):
        tag.decompose()
    
    # get content -> create hash to check overlap
    content = ' '.join(soup.get_text(separator=" ", strip=True).split())
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    
    if content_hash in content_hashes:
        return

    visited_links.add(url)
    content_hashes.add(content_hash)
    
    # write result to output file
    with open(output_file, 'a', encoding='utf-8', newline='') as f:
        f.write(f'{url} #{content}\n\n')

    # find , handle child urls
    for link in soup.find_all('a', href=True):
        new_url = link['href']
        
        # rm rss
        if 'rss' in new_url:
            continue 

        # change absolute
        if new_url.startswith('/'):
            new_url = url.rstrip('/') + new_url

        # rm redundant in url
        if ".htm" in new_url and new_url.count(".htm") > 1:
            new_url = new_url.replace(".htm", "", new_url.count(".htm") - 1)

        # recursive handle child url
        if new_url not in visited_links and new_url.startswith(url):
            crawl(new_url, driver, output_file, depth + 1, max_depth, visited_links, content_hashes)


def run_crawl(website_url, chrome_driver_path, output_file):
    # check file if exist, rm
    if os.path.exists(output_file):
        os.remove(output_file)

    driver = init_driver(chrome_driver_path)
    try:
        crawl(website_url, driver, output_file)
    finally:
        driver.quit()

#data config
website_url = 'https://vtv.vn/'
chrome_driver_path = r'D:\Apps\chromedriver-win64\chromedriver.exe'
output_file = 'vtv_data1809.txt'


run_crawl(website_url, chrome_driver_path, output_file)