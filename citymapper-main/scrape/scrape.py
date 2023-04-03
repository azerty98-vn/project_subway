import json
import re
import sys
import urllib.request
from os.path import expanduser

import psycopg2
import requests
from bs4 import BeautifulSoup
import os

os.chdir(sys.path[0])
sys.path.append('../modules')
import params
import route_type


# See params.py
data_path, user, password, database, host = params.get_variables()
conn = psycopg2.connect(database=str(database), user=str(user), host=str(host), password=str(password))
cursor = conn.cursor()


def get_google_images_data(soup, query_name, html, headers, pathtofolder):
    all_script_tags = soup.select('script')
    matched_images_data = ''.join(re.findall(r"AF_initDataCallback\(([^<]+)\);", str(all_script_tags)))
    matched_images_data_fix = json.dumps(matched_images_data)
    matched_images_data_json = json.loads(matched_images_data_fix)
    matched_google_image_data = re.findall(r'\[\"GRID_STATE0\",null,\[\[1,\[0,\".*?\",(.*),\"All\",',
                                           matched_images_data_json)
    matched_google_images_thumbnails = ', '.join(
        re.findall(r'\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]',
                   str(matched_google_image_data))).split(', ')
    for fixed_google_image_thumbnail in matched_google_images_thumbnails:
        google_image_thumbnail_not_fixed = bytes(fixed_google_image_thumbnail, 'ascii').decode('unicode-escape')
        google_image_thumbnail = bytes(google_image_thumbnail_not_fixed, 'ascii').decode('unicode-escape')

    # removing previously matched thumbnails for easier full resolution image matches.
    removed_matched_google_images_thumbnails = re.sub(
        r'\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]', "", str(matched_google_image_data))

    matched_google_full_resolution_images = re.findall(r"(?:'|,),\[\"(https:|http.*?)\",\d+,\d+\]",
                                                       removed_matched_google_images_thumbnails)

    fixed_full_res_image = matched_google_full_resolution_images[0]
    original_size_img_not_fixed = bytes(fixed_full_res_image, 'ascii').decode('unicode-escape')
    original_size_img = bytes(original_size_img_not_fixed, 'ascii').decode('unicode-escape')

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent',
                          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36')]
    urllib.request.install_opener(opener)
    try:
        urllib.request.urlretrieve(original_size_img, pathtofolder + '/' + query_name + '.jpg')
    except:
        pass


headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
"Accept-Encoding": "gzip, deflate",
"Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
"Dnt": "1",
"Host": "httpbin.org",
"Upgrade-Insecure-Requests": "1",
"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
}

pathtofolder = data_path + '\\Scrape\\'

cursor.execute("""select route_type, route_name from routes
                   f group by route_type, route_name
                    ORDER BY route_type
                    """)

conn.commit()
rows = cursor.fetchall()
for ii, i in enumerate(rows):
    print(f"""{ii}""" + '/' + f'{len(rows)}')
    query = route_type.str_route_type(int(i[0])) + ' ' + str(i[1]) + ' Paris'
    params = {
        "q": query,
        "tbm": "isch",
        "ijn": "0",
    }
    print('')
    html = requests.get("https://www.google.com/search", params=params, headers=headers)
    print('')
    soup = BeautifulSoup(html.text, 'lxml')
    get_google_images_data(soup, query, html, headers, pathtofolder)
