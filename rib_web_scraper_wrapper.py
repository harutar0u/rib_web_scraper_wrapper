import os
import re
import sys
import shutil
import subprocess
import json
import yaml

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


CONFIG = 'rib_web_scraper_wrapper_config.json'

CHROME_DRIVER = './chromedriver_win32/chromedriver.exe'
WEB_SCRAPER = './webscrape.exe'

DATA_TEXT = 'data.txt'
EVENT_YAML = 'event.yml'

OUTPUT_DIR = './output'
PULLED_DIR = './data-pulled'


def main():
    config = load_config(CONFIG)
    event_data = load_yaml_file(EVENT_YAML)

    if config['just-export-match-url'] == 0:
        split_files_by_events(config, event_data)

    elif config['just-export-match-url'] == 1:
        export_all_match_url_to_data_txt(event_data)


def split_files_by_events(config, event_data):
    print('Scraping all events and Split files by each events \n')
    max_event_num = count_event_num(event_data)

    event_count = 0
    for year in event_data.keys():
        print('* ' + str(year) + ' Season * ')

        for region in event_data[year].keys():
            print( '[' + region + '] ')

            for event_url in event_data[year][region]:
                event_title, match_url_list = scraping_match_url_list(event_url)

                event_count += 1
                print(event_title + ' [' + str(event_count) + '/' + str(max_event_num) + '] ')

                export_match_url_list_to_data_txt(match_url_list)

                run_webscraper()

                os.makedirs(
                    OUTPUT_DIR + '/' + str(year) + '/' + region + '/' \
                    + replace_forbidden_characters(event_title),
                    exist_ok=True
                )

                if config['save-data-txt']:
                    shutil.copyfile(
                        DATA_TEXT, 
                        OUTPUT_DIR + '/' + str(year) + '/' + region + '/' \
                        + replace_forbidden_characters(event_title) + '/' + DATA_TEXT
                    )

                move_scraped_data_to_event_dir(year, region, event_title)


def export_all_match_url_to_data_txt(event_data):
    print('Export all match url > ' + DATA_TEXT + '\n')
    max_event_num = count_event_num(event_data)

    event_count = 0
    all_match_url_list = []
    for year in event_data.keys():
        print('* ' + str(year) + ' Season * ')

        for region in event_data[year].keys():
            print( '[' + region + '] ')

            for event_url in event_data[year][region]:
                event_title, match_url_list = scraping_match_url_list(event_url)

                event_count += 1
                print(event_title + ' [' + str(event_count) + '/' + str(max_event_num) + '] ')

                all_match_url_list.extend(match_url_list)

    export_match_url_list_to_data_txt(all_match_url_list)


def replace_forbidden_characters(strings):
    return re.sub(r'[\\/:*?"<>|]+', '', strings)


def read_text_one_line(file_name):
    url_list = []
    with open(file_name) as f:
        for line in f:
            url_list.append(line)

    return url_list


def load_config(file_path):
    json_open = open(file_path, 'r')
    json_load = json.load(json_open)
    
    return json_load

def load_yaml_file(file_path):
    with open(file_path, 'r') as yml:
        yaml_load = yaml.safe_load(yml)
    
    return yaml_load


def count_event_num(event_data):
    max_event_num = 0
    for year in event_data.keys():
        for region in event_data[year].keys():
            max_event_num += len(event_data[year][region])

    return max_event_num


def scraping_match_url_list(event_url):
    options = Options()
    options.headless = True
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(CHROME_DRIVER)
    
    driver = webdriver.Chrome(options=options, service=service)

    driver.get(event_url)
    source_code = driver.page_source
    html_text = BeautifulSoup(source_code, 'html.parser')

    event_title = html_text.select_one('.MuiTypography-root.jss69').text

    driver.find_element(
        by=By.CSS_SELECTOR, 
        value='#root > div > div.MuiGrid-root.jss3.MuiGrid-item > div > div.jss59 > div.jss82 > div.jss83 > div > div:nth-child(2)'
    ).click()
    source_code = driver.page_source
    html_text = BeautifulSoup(source_code, 'html.parser')

    match_holder = html_text.select_one('.MuiGrid-root.jss3.MuiGrid-item').find_all('a')
    url_list = []
    for match_idx in range(len(match_holder)):
        match_url = match_holder[match_idx].get('href')
        if not 'match' in match_url:
            url_list.append(match_url)

    return event_title, url_list


def export_match_url_list_to_data_txt(match_url_list):
    with open(DATA_TEXT, 'w') as f:
        for match_url in match_url_list:
            f.write('https://rib.gg%s\n' % match_url)


def run_webscraper():
    try:
        result = subprocess.run(
            WEB_SCRAPER, 
            # shell=True, 
            # check=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True
        )
        for line in result.stdout.splitlines():
            print('>>> ' + line)
        print('\n')
    except subprocess.CalledProcessError:
        print('ERROR: Failed to execute ' + WEB_SCRAPER, file=sys.stderr)
    

def move_scraped_data_to_event_dir(year, region, event_title):
    src_dir = PULLED_DIR
    dst_dir = OUTPUT_DIR + '/' + str(year) + '/' + region + '/' \
              + replace_forbidden_characters(event_title) + '/'
    for p in os.listdir(src_dir):
        try:
            shutil.move(os.path.join(src_dir, p), dst_dir)
        except:
            print('ERROR: File already exists > ' + p)


if __name__ == '__main__':
    main()