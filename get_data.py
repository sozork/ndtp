import datetime
import sqlite3
import requests
from bs4 import BeautifulSoup


dates_dict = {
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
}

connection = sqlite3.connect('data.db')
cursor = connection.cursor()

# cursor.execute("CREATE TABLE yandex (curent_date DATE, date DATE, rain BOOL, temperature REAL, humidity REAL)")
now = datetime.date.today()
def get_data_yandex(cursor):
    link = 'https://yandex.by/pogoda/ru/minsk/details/today?lat=53.902735&lon=27.555691'
    source = requests.get(link).text
    soup = BeautifulSoup(source, 'lxml')
    weather_container = soup.select_one('ul[aria-labelledby="_S_1_-short-forecast-title"]')
    days = weather_container.select('li[class*="AppForecastDay_dayCard_"]')
    for day in days:
        day_data = day.select_one('article[class*="AppForecastDay_container"]')

        date = day_data.select_one('h3[class*=AppForecastDayHeader_dayTitle]')
        date = datetime.date(datetime.datetime.now().year, int(dates_dict[date.text.split()[2]]), int(date.text.split()[1]))

        temp = day_data.select('div[class*="AppForecastDayPart_value__9pxTD AppForecastDayPart_center__esSb6 AppForecastDayPart_temp__kKbJG AppForecastDayPart_value__medium__JXTZV"][style$="-temp"]')
        avg_temp = 0
        for i in temp:
            avg_temp += int(i.text[:-1])
        avg_temp/=4

        humidity = day_data.select('div[class="AppForecastDayPart_value__9pxTD AppForecastDayPart_center__esSb6 AppForecastDayPart_showNarrow__fTNAB"][style$="-hum"]')
        avg_humidity = 0
        for i in humidity:
            avg_humidity += int(i.text[:-1])
        avg_humidity= round(avg_humidity/4, 1)
        
        rain = day_data.select('div[class="AppForecastDayPart_caption__k1Uip AppForecastDayPart_center__esSb6 AppForecastDayPart_text__dFFbf AppForecastDayPart_showWide__hsoFN"][style$="-text"]')
        israin = False
        for i in rain:
            if 'дожд' in i.text:
                israin = True
                break
        cursor.execute("INSERT INTO yandex VALUES(?, ?, ?, ?, ?)", [now.isoformat(), date.isoformat(), israin, avg_temp, avg_humidity])

def get_data_google(cursor):
    consider_rain_percent = 20
    url = "https://weather.googleapis.com/v1/forecast/days:lookup?"
    params = {
        "location.latitude": 53.90056,
        "location.longitude": 27.55861,
        "key": 'AIzaSyDOTTYUc3ssVWoIEl_1q4HTuEPnSZIFBE4',
        "days": 10,
        "pageSize": 10
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    days = response.json()["forecastDays"]
    for day in days:
        date = day['displayDate']
        date = datetime.date(date['year'], date['month'], date['day'])
        rain = day['daytimeForecast']['precipitation']['probability']['percent'] >= consider_rain_percent
        humidity = day['daytimeForecast']['relativeHumidity']
        avg_temp = round((day['maxTemperature']['degrees']+day['minTemperature']['degrees'])/2, 2)
        cursor.execute("INSERT INTO google VALUES(?, ?, ?, ?, ?)", [now.isoformat(), date.isoformat(), rain, avg_temp, humidity])

# query = '''CREATE TABLE google (
#     `current_date` DATE,
#     `date` DATE,
#     rain BOOL,
#     temperature REAL,
#     humidity REAL
# );'''
# cursor.execute(query)
get_data_google(cursor)
get_data_yandex(cursor)
connection.commit()
connection.close()