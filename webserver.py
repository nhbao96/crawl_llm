from flask import Flask, request, jsonify, render_template, Response, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import json
import threading
import os
from datetime import datetime

app = Flask(__name__)

visited_links = set()
unique_urls = set()
content_stream = []
driver = None
is_crawling = False
output_file = ""
format_type = ""

def init_driver():
    driver_path = 'D:\\Apps\\chromedriver-win64\\chromedriver.exe'
    service = Service(executable_path=driver_path)
    return webdriver.Chrome(service=service)

def init_output_file(output_file, format_type):
    with open(output_file, 'w', encoding='utf-8') as f:
        if format_type == "json":
            f.write("[\n")
        else:
            f.write("")

def normalize_url(url):
    return url.rstrip('/')

def scroll_to_end(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def extract_meta_data(soup):
    time_tag = soup.find_all("meta", {"class": "cms-date"})
    datetime_crawled = time_tag[0]['content'] if time_tag else "Not found"
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    keywords = keywords_tag.get('content') if keywords_tag else "No keywords"
    return {"datetime_crawled": datetime_crawled, "keywords": keywords}

def extract_page_data(driver, url):
    driver.get(url)
    time.sleep(2)
    scroll_to_end(driver)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    title = soup.title.get_text() if soup.title else ""
    meta_data = extract_meta_data(soup)
    description_tag = soup.find('meta', attrs={'property': 'og:description'})
    description = description_tag.get('content') if description_tag else ""
    for tag in soup(['script', 'style', 'meta', 'link', 'img', 'video', 'a']):
        tag.decompose()
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
    finally:
        return {"#url": url, "title": title, "description": description, "content": content, "meta_data": meta_data}

def write_page_data(output_file, page_data, format_type, first_entry):
    with open(output_file, 'a', encoding='utf-8') as f:
        if format_type == "json":
            if not first_entry:
                f.write(",\n")
            json.dump(page_data, f, ensure_ascii=False, indent=4)
        else:
            data_txt = f"#{page_data['#url']} {{ #{page_data['content']} #{page_data['title']} #{page_data['description']} #{page_data['meta_data']} }}"
            f.write(data_txt + "\n")

def crawl_and_save(url, driver, output_file, format_type="json", depth=0, max_depth=3):
    global visited_links, unique_urls, content_stream, is_crawling

    if depth > max_depth or not is_crawling:
        return

    normalized_url = normalize_url(url)
    if normalized_url in visited_links or normalized_url.count(".htm") > 1 or normalized_url in unique_urls:
        return
    else:
        unique_urls.add(normalized_url)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for link in soup.find_all('a', href=True):
        new_url = link['href']
        if 'rss' in new_url or new_url in visited_links:
            continue
        if ('video' in new_url) or ('media' in new_url) or ('podcast' in new_url):
            continue
        if ('#' in new_url) or ('@' in new_url) or ('javascript' in new_url):
            continue
        if new_url.startswith('/'):
            new_url = normalized_url.rstrip('/') + new_url
        if ".htm" in new_url and new_url.count(".htm") > 1:
            new_url = new_url.replace(".htm", "", new_url.count(".htm") - 1)
        if new_url.startswith(normalized_url):
            crawl_and_save(new_url, driver, output_file, format_type, depth + 1, max_depth)

    try:
        page_data = extract_page_data(driver, normalized_url)
        if page_data:
            write_page_data(output_file, page_data, format_type, len(visited_links) == 0)
            visited_links.add(normalized_url)
            log_message(f"Writing content from: {normalized_url}", "INFO")
    except Exception as e:
        log_message(f"Error processing {url}: {e}", "ERROR")
        return

def start_crawl_thread(website_url, output_file_param, format_type_param):
    global driver, visited_links, unique_urls, content_stream, is_crawling, output_file, format_type
    visited_links = set()
    unique_urls = set()
    content_stream = []
    output_file = output_file_param
    format_type = format_type_param
    driver = init_driver()
    init_output_file(output_file, format_type)
    is_crawling = True
    try:
        crawl_and_save(website_url, driver, output_file, format_type)
    finally:
        driver.quit()
        stop_crawl_message()

def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_stream.append(f"{timestamp} [{level}] - {message}")

def stop_crawl_message():
    if format_type == "json":
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write("\n]")
    log_message("Crawling stopped.", "INFO")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    website_url = request.json.get('website_url')
    output_file_param = request.json.get('output_file')
    format_type_param = request.json.get('format_type', 'json')
    crawl_thread = threading.Thread(target=start_crawl_thread, args=(website_url, output_file_param, format_type_param))
    crawl_thread.start()
    return jsonify({'status': 'success', 'message': 'Crawling started!'})

@app.route('/stop_crawl', methods=['POST'])
def stop_crawl():
    global is_crawling
    is_crawling = False
    return jsonify({'status': 'success', 'message': 'Crawling stopped!'})

@app.route('/crawl_log')
def crawl_log():
    def generate():
        global content_stream
        while True:
            if content_stream:
                yield f"data: {content_stream.pop(0)}\n\n"
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download_log')
def download_log():
    if os.path.exists(output_file):
        return send_file(output_file, as_attachment=True)
    else:
        return jsonify({'status': 'error', 'message': 'File not found!'})

if __name__ == '__main__':
    app.run(debug=True)
