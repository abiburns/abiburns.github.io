import os
from scrape_weather_d import scrape_range

# Change the current working directory
path = r"C:\Users\Owner\Documents\Knowledge_Mining\weather"
os.chdir(path)

# Set parameters
start_date = "1975-03-23"
end_date = "1976-03-23"
# end_date = "2025-03-23"
# by = "91.3125 day")
station_code_1 = "KCALOSAN1265"
city_1 = "los-angeles"
state_1 = "ca"
station_code_2 = "KFLORLAN438"
city_2 = "orlando"
state_2 = "fl"
pause = 20

scrape_range(start_date, end_date, city_1, state_1, station_code_1)
scrape_range(start_date, end_date, city_2, state_2, station_code_2)

