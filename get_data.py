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
yesterday = now - datetime.timedelta(days=1)
def get_data_yandex(cursor):
    link = 'https://yandex.by/pogoda/ru/minsk/details/today?lat=53.902735&lon=27.555691'
    source = requests.get(link).text
    soup = BeautifulSoup(source, 'lxml')
    # разбор сайта на нужные данные
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
        # супер костыльное получение дождя, если часть слова 'дожд' был утром, днём, вечером или ночью
        rain = day_data.select('div[class="AppForecastDayPart_caption__k1Uip AppForecastDayPart_center__esSb6 AppForecastDayPart_text__dFFbf AppForecastDayPart_showWide__hsoFN"][style$="-text"]')
        israin = False
        for i in rain:
            if 'дожд' in i.text:
                israin = True
                break
        cursor.execute("INSERT INTO yandex VALUES(?, ?, ?, ?, ?)", [now.isoformat(), date.isoformat(), israin, avg_temp, avg_humidity])

def get_data_google(cursor):
    consider_rain_quant = 0.01 # сколько минимум мм осадов = был дождь
    # для подробных данных смотрите документацию google wheather api
    url = "https://weather.googleapis.com/v1/forecast/days:lookup?"
    params = {
        "location.latitude": 53.9,
        "location.longitude": 27.57,
        "key": 'AIzaSyDOTTYUc3ssVWoIEl_1q4HTuEPnSZIFBE4',
        "days": 10,
        "pageSize": 10
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    days = response.json()["forecastDays"]
    # собираем данные по гуглу за каждый полученный день
    for day in days:
        date = day['displayDate']
        date = datetime.date(date['year'], date['month'], date['day'])

        time = 'daytimeForecast'
        precipitation_daytime = day[time]['precipitation']
        rain_daytime = precipitation_daytime['qpf']['quantity'] - precipitation_daytime['snowQpf']['quantity'] >= consider_rain_quant # если колво осадков - кол-во снега больше consider_rain_quant, тогда дождь был, иначе нет
        humidity_daytime = day[time]['relativeHumidity']
    
        time = 'nighttimeForecast'
        precipitation_nighttime = day[time]['precipitation']
        rain_nighttime = precipitation_nighttime['qpf']['quantity'] - precipitation_nighttime['snowQpf']['quantity'] >= consider_rain_quant # если колво осадков - кол-во снега больше consider_rain_quant, тогда дождь был, иначе нет
        humidity_nighttimetime = day[time]['relativeHumidity']

        # среднее между днём и ночью
        avg_temp = round((day['maxTemperature']['degrees']+day['minTemperature']['degrees'])/2, 2)
        rain = rain_daytime or rain_nighttime
        humidity = round((humidity_daytime+humidity_nighttimetime)/2, 2)
        cursor.execute("INSERT INTO google VALUES(?, ?, ?, ?, ?)", [now.isoformat(), date.isoformat(), rain, avg_temp, humidity])

def get_data_openmeteo(cursor):
    considerd_rain_min = 0.01 # сколько минимум мм осадов = был дождь
    # для подробностей смотреть документацию openmeteo https://open-meteo.com/
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 53.9,
        "longitude": 27.57,
        "start_date": yesterday.isoformat(),
        "end_date": yesterday.isoformat(),
        "daily": ["weather_code", "temperature_2m_mean", "rain_sum", "relative_humidity_2m_mean"],
        "timezone": "Europe/Moscow"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()['daily']
    date = data['time'][0]
    avg_temp = data['temperature_2m_mean'][0]
    rain = data['rain_sum'][0]>considerd_rain_min
    humidity = data['relative_humidity_2m_mean'][0]
    cursor.execute("INSERT INTO openmeteo VALUES(?, ?, ?, ?)", [date, rain, avg_temp, humidity])

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
get_data_openmeteo(cursor)
connection.commit()
connection.close()
