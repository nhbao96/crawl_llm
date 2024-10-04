from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import hashlib
import os
import json

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

def crawl(url, driver, output_file, depth=0, max_depth=3, visited_links=set(), title_hashes=set()):
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
    # get title -> create hash to check overlap
    #content = ' '.join(soup.get_text(separator=" ", strip=True).split())
    # get title
    try:
        title = soup.title.get_text()
    except Exception as e:
        print(f'Can not find title {url}: {e}')
        return
    #hash title 
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    
    if title_hash in title_hashes:
        return

    title_hashes.add(title_hash)
    visited_links.add(url)

    #check url before go through content
    # find , handle child urls
    for link in soup.find_all('a', href=True):
        new_url = link['href']
        
        # rm rss
        if 'rss' in new_url:
            continue
        # remove video and do not values content link
        if ('video' in new_url) or ('media' in new_url) or ('podcast' in new_url):
            continue
        if ('#' in new_url) or ('@' in new_url) or ('javascript' in new_url):
            continue
        # change absolute
        if new_url.startswith('/'):
            new_url = url.rstrip('/') + new_url

        # rm redundant in url
        if ".htm" in new_url and new_url.count(".htm") > 1:
            new_url = new_url.replace(".htm", "", new_url.count(".htm") - 1)

        # recursive handle child url
        if new_url not in visited_links and new_url.startswith(url):
            crawl(new_url, driver, output_file, depth + 1, max_depth, visited_links, title_hashes)
    
    # get description
    try:
        meta_description = soup.find('meta', attrs={'property': 'og:description'}).get('content')
    except Exception as e:
        print(f'Can not get description from {url}:{e}')
        meta_description =''
    
    #metadata
    time_tag = soup.find_all("meta", {"class": "cms-date"})
    datetime_crawled = time_tag[0]['content'] if time_tag else "Not found"
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    keywords = keywords_tag.get('content') if keywords_tag else "No keywords"
    metadata={"datetime_crawled": datetime_crawled, "keywords": keywords}
    # get content
    try:
        content_all = soup.find_all("div", {"class": "article__body cms-body"})
        content_all = content_all[0].find_all('p')

        for tag in content_all:
            for attribute in ["class", "id", "name",'script', 'style', 'meta', 'link', 'img', 'video', 'a']:
                del tag[attribute]
        content_final=""
        for content in content_all[0:-1]:
            content_final=content_final+content.text.strip()
    except:
        return
    
    data ={
            "#url":url,
            "title": title,
            "description": meta_description,
            "content":content_final,
            "metadata": metadata
    }
    with open(output_file, 'a+', encoding='utf-8', newline='') as f:
        f.write(f'{data},\n')

def run_crawl(website_url, chrome_driver_path, output_file):
    # check file if exist, rm
    if os.path.exists(output_file):
        os.remove(output_file)
    with open(output_file, 'w+', encoding='utf-8') as file:
        file.write('{\n')
        file.close()
    driver = init_driver(chrome_driver_path)
    try:
        crawl(website_url, driver, output_file)
    finally:
        driver.quit()

#data config
website_url = 'https://baophapluat.vn/'
chrome_driver_path = r'C:\Users\atong\Documents\chromedriver-win64\chromedriver.exe'
output_file = 'content.json'

#process content file 
with open(output_file, 'w+', encoding='utf-8') as file:
    file.write('{\n')
    file.close()
run_crawl(website_url, chrome_driver_path, output_file)

with open(output_file, 'w+', encoding='utf-8') as file:
    file.seek(-1, 2)
    file.truncate()
    file.write('\n}')
    file.close()
