import time
import pandas as pd
import random
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def extract_table_data(driver):
    script = """
    const host = document.querySelector("lib-city-history-summary");
    if (!host) {
        const legacyTable = document.querySelector("table");
        if (!legacyTable) return "❌ no legacy table found";
        let rows = legacyTable.querySelectorAll("tbody tr");
        return Array.from(rows).map(row =>
            Array.from(row.querySelectorAll("td")).map(cell => cell.innerText.trim())
        );
    }

    if (!host.shadowRoot) {
        const legacyTable = document.querySelector("table");
        if (!legacyTable) return "❌ no shadowRoot and no fallback table found";
        let rows = legacyTable.querySelectorAll("tbody tr");
        return Array.from(rows).map(row =>
            Array.from(row.querySelectorAll("td")).map(cell => cell.innerText.trim())
        );
    }

    let rows = host.shadowRoot.querySelectorAll("table tbody tr");
    return Array.from(rows).map(row =>
        Array.from(row.querySelectorAll("td")).map(cell => cell.innerText.trim())
    );
    """
    return driver.execute_script(script)

def clean_weather_summary_table(raw_rows, date_str):
    cleaned_data = []
    current_section = None

    for row in raw_rows:
        if len(row) == 0:
            continue

        # Section header (e.g., Temperature, Wind)
        if len(row) == 1:
            current_section = row[0].strip()
            continue

        if current_section and "Astronomy" in current_section:
            continue

        if len(row) >= 2:
            metric = row[0].strip()
            actual_value = row[1].strip()

            cleaned_data.append({
                "Date": date_str,
                "Section": current_section,
                "Metric": metric,
                "Value": actual_value
            })

    return pd.DataFrame(cleaned_data)

def scrape_weather_for_date(driver, date_str, city, state, station, retries=1):
    url = f"https://www.wunderground.com/history/daily/us/{state}/{city}/{station}/date/{date_str}"
    print(f"\nScraping: {date_str}")

    attempt = 0
    while attempt <= retries:
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.querySelector('table') !== null || document.querySelector('lib-city-history-summary') !== null")
            )
            time.sleep(2)

            rows = extract_table_data(driver)

            if isinstance(rows, str):
                print(f"JS Error on {date_str}: {rows}")
                raise Exception(rows)

            if not rows:
                print(f"No data extracted on {date_str}")
                raise Exception("No rows found")

            df_day = clean_weather_summary_table(rows, date_str)
            print(f"Extracted {len(df_day)} rows on {date_str}")
            return df_day

        except (Exception, WebDriverException) as e:
            print(f"Attempt {attempt + 1} failed for {date_str}: {e}")
            if attempt == retries:
                print(f"Giving up on {date_str}")
                return pd.DataFrame()
            else:
                attempt += 1
                time.sleep(5)
                try:
                    driver.refresh()
                except:
                    # Browser is dead — reinitialize driver
                    print("Refreshing driver...")
                    driver.quit()
                    driver = init_driver(headless=True)

def scrape_range(start_date, end_date, city, state, station, headless=True):
    driver = init_driver(headless=headless)
    all_data = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    while current_date <= end_date_obj:
        time.sleep(random.uniform(3,7))
        date_str = current_date.strftime("%Y-%m-%d")
        df_day = scrape_weather_for_date(driver, date_str, city, state, station)
        if df_day is not None and not df_day.empty:
            all_data.append(df_day)
            df_day.to_csv("temp_scraped.csv", mode="a", header=not os.path.exists("temp_scraped.csv"), index=False)
        current_date += timedelta(days=91.3125)

    driver.quit()

    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        df_all.to_csv(f"{city}_weather.csv")
    else:
        print("No data scraped.")
        return pd.DataFrame()

