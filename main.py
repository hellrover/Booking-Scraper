import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import snowflake.connector
from config import SNOWFLAKE_CONFIG
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas


options = Options()
options.add_argument("--headless=new")  
driver = webdriver.Chrome()

driver.get("https://www.booking.com/searchresults.en-gb.html?advanced_search_switch=standard&ss=Glasgow&ssne=Glasgow&ssne_untouched=Glasgow&efdco=1&label=gog235jc-10CAEoggI46AdICVgDaFCIAQGYATO4AQfIAQzYAQPoAQH4AQGIAgGoAgG4Auv4j84GwAIB0gIkYTUyOTRkZWUtMGU1MS00YTI1LTk3ZDktMmM0ZWVhMTdkYWQ22AIB4AIB&aid=397594&lang=en-gb&sb=1&src_elem=sb&src=searchresults&dest_id=-2597039&dest_type=city&checkin=2026-03-28&checkout=2026-03-29&group_adults=2&no_rooms=1&group_children=0")

wait = WebDriverWait(driver, 30)

# accept cookies
try:
    wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))).click()
except:
    pass

# close the sign-in option
try:
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Dismiss sign in information."]'))).click()
except:
    print("din't work")


# scroll to trigger loading
for i in range(1,5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    try:
        load_more = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//span[text()="Load more results"]/parent::button')
            )
        )
        driver.execute_script("arguments[0].click();", load_more)
        time.sleep(2)
    except:
        pass

hotels = wait.until(
  EC.visibility_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="property-card"]'))
)

results = []

for hotel in hotels:
    try:
        name = hotel.find_element(By.CSS_SELECTOR, '[data-testid="title"]').text
    except:
        name = "N/A"

    try:
        price = hotel.find_element(By.CSS_SELECTOR, '[data-testid="price-and-discounted-price"]').text
    except:
        price = "N/A"
    
    try:
        review = hotel.find_element(By.CSS_SELECTOR, '[class="f63b14ab7a dff2e52086"]').text
    except:
        review = "N/A"

    try:
        numReview = hotel.find_element(By.CSS_SELECTOR, '[class="fff1944c52 fb14de7f14 eaa8455879"]').text
    except:
        numReview = "N/A"
        

    results.append({
        "hotelName": name,
        "price": price,
        "review": review,
        "TotalReview" : numReview,
    })

driver.quit()

#Transforming data 
df=pd.DataFrame(results)

df.columns = [col.upper() for col in df.columns]
df.fillna('', inplace=True)

df["ID"] = range(1, len(df)+1)

df = df.rename(columns={
    "HOTELNAME": "HOTELNAME",
    "PRICE": "PRICE",
    "REVIEW": "RATING",
    "TOTALREVIEW": "REV"
})
df["PRICE"] = (
    df["PRICE"]
    .str.replace(r"[^\d]", "", regex=True)
    .replace("", "0")
    .astype(int)
)
df["RATING"] = pd.to_numeric(df["RATING"], errors="coerce").fillna(0).astype(int)
df["REV"] = df["REV"].fillna('').str.strip()

df = df[["ID", "HOTELNAME", "PRICE", "RATING", "REV"]]

print(df.tail())

# Connect to Snowflake
conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
cursor = conn.cursor()

insert_query = """
INSERT INTO booking (Id, hotelName, price, rating, rev)
VALUES (%s, %s, %s, %s, %s)
"""

data = df.values.tolist()

cursor.executemany(insert_query, data)

conn.commit()

cursor.close()
conn.close()