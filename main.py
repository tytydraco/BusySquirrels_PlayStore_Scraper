import time
import datetime

from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options

import mysql.connector

# Update the dynamic table once every this many seconds (def: 5m)
DYNAMIC_TABLE_LOOP_DELAY =  (60 * 5)

# Add a row to the static table
SQL_ADD_STATIC_COMMAND =    "INSERT INTO static (id, name, url, image_url) VALUES (%s, %s, %s, %s)"
# Add a row to the dynamic table
SQL_ADD_DYNAMIC_COMMAND =   "REPLACE INTO dynamic (id, price, timestamp) VALUES (%s, %s, %s)"
# Erase all rows from the static table
SQL_CLEAR_STATIC_COMMAND =  "DELETE FROM static"
# Erase all rows from the dynamic table
SQL_CLEAR_DYNAMIC_COMMAND = "DELETE FROM dynamic"

# Target Google Play Store URL
PLAY_STORE_PAGE =           "https://play.google.com/store/apps/collection/cluster?clp=0g4jCiEKG3RvcHNlbGxpbmdfcGFpZF9BUFBMSUNBVElPThAHGAM%3D:S:ANO1ljLdnoU&gsr=CibSDiMKIQobdG9wc2VsbGluZ19wYWlkX0FQUExJQ0FUSU9OEAcYAw%3D%3D:S:ANO1ljIKVpg"

# NOTE: These CSS selectors were obfuscated as of 1/11/2021 (Jan 11th, 2020)
# Parent view of all the individual app views
TOP_CHARTS_APP_SELECTOR =   ".ImZGtf.mpg5gc"
# App name view
NAME_SELECTOR =             ".WsMG1c.nnK0zc"
# Parent of the developer name URL (since there are multiple instances of this class name, we must be more specific)
DEVELOPER_PARENT_SELECTOR = ".KoLSrc"
# App URL view
URL_SELECTOR =              ".JC71ub"
# App price parent view (we must navigate further through the unclassed children)
PRICE_PARENT_SELECTOR =     ".VfPpfd.ZdBevf.i5DZme"
# App image URL
IMAGE_URL_PARENT_SELECTOR =        ".ZYyTud.K3IMke.buPxGf"

# Login to play_store database with default credentials
sql_connection = mysql.connector.connect(
    host =                  "localhost",
    user =                  "root",
    passwd =                "password",
    # Database should be pre-created ("CREATE DATABASE play_store")
    db =                    "play_store"
)
sql_cursor = sql_connection.cursor()

"""
MySQL commands to create static and dynamic table (should be precreated)

CREATE TABLE static (
	id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100),
    url VARCHAR(100),
    image_url VARCHAR(2000)
);

CREATE TABLE dynamic (
	id VARCHAR(100) PRIMARY KEY,
    price DECIMAL(5,2),
    timestamp VARCHAR(100)
);
"""

# Data class to make storing/referencing HTML elements easier
class App:
    def __init__(self, id, name, url, image_url, price):
        self.id = id
        self.name = name
        self.url = url
        self.image_url = image_url
        self.price = price

def clear_static_table():
    sql_cursor.execute(SQL_CLEAR_STATIC_COMMAND)
    sql_connection.commit()

def clear_dynamic_table():
    sql_cursor.execute(SQL_CLEAR_DYNAMIC_COMMAND)
    sql_connection.commit()

# Scroll to the bottom of the page to load all images
def scroll_to_bottom():
    cur_height = browser.execute_script("return document.body.scrollHeight")
    last_height = -1
    while last_height != cur_height:
        last_height = cur_height
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        cur_height = browser.execute_script("return document.body.scrollHeight")

opts = Options()
# NOTE: Images refuse to load if the client has no visibility of the screen.
#       We cannot go headless.
# opts.set_headless()
# Utilize the Firefox web driver
browser = Firefox(options=opts)
browser.get(PLAY_STORE_PAGE)

# Images need to load, so scroll to the very bottom of the page
scroll_to_bottom()

# Clear the dynamic table (once per run)
clear_dynamic_table()

# Return a list of App objects
def retrieve():
    apps = browser.find_elements_by_css_selector(TOP_CHARTS_APP_SELECTOR)
    app_infos = []

    # Iterate over all discovered apps
    for app in apps:
        name = app.find_element_by_css_selector(NAME_SELECTOR) \
            .get_attribute("innerHTML") \
            .replace("&amp;", "&")
        url = app.find_element_by_css_selector(URL_SELECTOR).get_attribute("href")
        id = url.split("?id=")[1]
        price = app.find_element_by_css_selector(PRICE_PARENT_SELECTOR) \
            .find_element_by_tag_name("span") \
            .get_attribute("innerHTML") \
            .replace("$", "")
        image_url = app.find_element_by_css_selector(IMAGE_URL_PARENT_SELECTOR) \
            .find_element_by_tag_name("img") \
            .get_attribute("src")

        # Encode the info as an App object
        app_infos.append(App(id, name, url, image_url, price))
    return app_infos

def populate_static_table():
    clear_static_table()
    for info in retrieve():
        sql_obj = (info.id, info.name, info.url, info.image_url)
        sql_cursor.execute(SQL_ADD_STATIC_COMMAND, sql_obj)
    sql_connection.commit()

def populate_dynamic_table():
    for info in retrieve():
        # Date and time is stored in UTC
        # Price is stored in native currency
        sql_obj = (info.id, info.price, datetime.datetime.utcnow())
        sql_cursor.execute(SQL_ADD_DYNAMIC_COMMAND, sql_obj)
    sql_connection.commit()

def kickoff_dynamic_table_loop():
    # Run infinite loop to insert/replace dynamic table data
    while True:
        populate_dynamic_table()
        time.sleep(DYNAMIC_TABLE_LOOP_DELAY)

# Populate our static table and kickoff the dynamic table loop if we are executing directly
if __name__ == "__main__":
    populate_static_table()
    kickoff_dynamic_table_loop()