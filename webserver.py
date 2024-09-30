from flask import Flask, request, jsonify, render_template, Response
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import hashlib
import os
import threading
import chromedriver_autoinstaller
import sys
sys.path.insert(0, '/usr/lib/chromium-browser/chromedriver')

app = Flask(__name__)


progress = 0
logs = []  
content_stream = []  

# Function to initialize Selenium driver
def init_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chromedriver_autoinstaller.install()
    return webdriver.Chrome(options=chrome_options)

# Function to scroll the page down to the end
def scroll_to_end(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Main crawling function
def crawl(url, driver, output_file, depth=0, max_depth=3, visited_links=set(), content_hashes=set()):
    global progress, logs, content_stream

    if depth > max_depth:
        return

    try:
        driver.get(url)
    except Exception as e:
        logs.append(f"Error loading {url}: {e}")
        return

    time.sleep(2)
    scroll_to_end(driver)

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    for tag in soup(['img', 'video']):
        tag.decompose()

    content = ' '.join(soup.get_text(separator=" ", strip=True).split())
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

    if content_hash in content_hashes:
        return

    visited_links.add(url)
    content_hashes.add(content_hash)

    # Write content to the file and update logs and content_stream for SSE
    with open(output_file, 'a', encoding='utf-8', newline='') as f:
        f.write(f'{url} #{content}\n\n')
    
    logs.append(f"Content from: {url}\nPreview: {content[:200]}...")  # Log preview
    content_stream.append(f"Writing content from: {url}\nPreview: {content[:200]}...")

    progress = min(depth / max_depth * 100, 100)

    for link in soup.find_all('a', href=True):
        new_url = link['href']

        if 'rss' in new_url:
            continue

        if new_url.startswith('/'):
            new_url = url.rstrip('/') + new_url

        if ".htm" in new_url and new_url.count(".htm") > 1:
            new_url = new_url.replace(".htm", "", new_url.count(".htm") - 1)

        if new_url not in visited_links and new_url.startswith(url):
            crawl(new_url, driver, output_file, depth + 1, max_depth, visited_links, content_hashes)

def run_crawl(website_url, output_file):
    global progress, logs, content_stream

    # Reset progress and logs
    progress = 0
    logs = []
    content_stream = []

    if os.path.exists(output_file):
        os.remove(output_file)

    driver = init_driver()
    try:
        crawl(website_url, driver, output_file)
    finally:
        driver.quit()

# Background thread for crawling
def start_crawl_thread(website_url, chrome_driver_path, output_file):
    crawl_thread = threading.Thread(target=run_crawl, args=(website_url, output_file))
    crawl_thread.start()

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# start the crawl
@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    website_url = request.form['website_url']
    chrome_driver_path = request.form['chrome_driver_path']
    output_file = request.form['output_file']

    if not website_url or not chrome_driver_path or not output_file:
        return jsonify({'status': 'error', 'message': 'Please provide all required fields!'})

    start_crawl_thread(website_url, chrome_driver_path, output_file)
    return jsonify({'status': 'success', 'message': 'Crawling started!'})

# real-time streaming of content
@app.route('/stream')
def stream():
    def generate():
        global content_stream
        while True:
            if content_stream:
                message = content_stream.pop(0)
                yield f"data: {message}\n\n"
            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
