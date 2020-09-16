from random import randint
from tqdm import tqdm
from datetime import datetime
from time import sleep

import argparse
import sqlite3
import requests
import json

def getAirports(session, countries=[]):

    if len(countries) > 0:
        result = {}
        for country in countries:
            airports = getAirportForCountry(session, country)
            result.update(airports)
        return result
    else:
        return getAirportForCountry(session)

def getAirportForCountry(session, country=''):
    data = {
        'sessionId': session,
        'country': country
    }
    response = requests.post('https://navdatapro.aerosoft.com/api/v3/airports', data=data)
    airports = json.loads(response.text)['airports']
    return {airport['icao']: airport for airport in airports}

def getChartsForAirport(session, icao):
    data = {
        'sessionId': session,
        'icao': icao
    }
    response = requests.post('https://navdatapro.aerosoft.com/api/v3/catalogue', data=data)
    charts = json.loads(response.text)['catalogue']
    return charts

def getDownloadIdForChart(session, chartId):
    data = {
        'sessionId': session,
        'chartId': chartId
    }
    response = requests.post('https://navdatapro.aerosoft.com/api/v3/chart', data=data)
    downloadId = json.loads(response.text)['download_id']
    return downloadId

def downloadChartAsPdf(downloadId):
    response = requests.post('https://navdatapro.aerosoft.com/api/v3/download/' + str(downloadId))
    return response.content

def entryForAirportExists(icao, dbConnection):
    param = (icao,)
    cursor = dbConnection.execute('SELECT * FROM airports WHERE icao=?', param)
    return cursor.fetchone() is not None

def saveAirport(dbConnection, airport, airportExists, charts, binaries, mimeType='application/pdf'):

    airportInformation =  (
        airport['icao'],
        airport['airport_id'],
        airport['country'],
        airport['cityname'],
        airport['name'],
        airport['latitude'],
        airport['longitude'],
        airport['elevation'],
        airport['longestrunway'],
        datetime.now()
    )
    cursor = dbConnection.execute('INSERT INTO airport_information(icao, nav_data_airport_id, country, '
                         'city, name, latitude, longitude, elevation, longest_runway, timestamp)'
                         'VALUES (?,?,?,?,?,?,?,?,?,?)', airportInformation)
    airportInformationId = cursor.lastrowid

    airportValues = (
        airport['icao'],
        airport['iata'],
        airportInformationId
    )
    if airportExists:
        dbConnection.execute('')
    else:
        dbConnection.execute('INSERT INTO airports(icao, iata, latest_information) VALUES(?,?,?)', airportValues)

    for chart in charts:
        chartId = chart['chart_id']
        blob = binaries[chartId]
        cursor = dbConnection.execute('INSERT INTO chart_binaries(mime_type, creation_date, data) VALUES (?,?,?)',
                                      (mimeType, datetime.now(), blob))
        binaryId = cursor.lastrowid

        chartValues = (
            airportInformationId,
            chart['chart_id'],
            chart['chart_type'],
            chart['chart_name'],
            int(chart['geo_chart']),
            binaryId
        )
        dbConnection.execute('INSERT INTO charts(airport_information, nav_data_chart_id, type, name, geo_chart, '
                             'chart_binary) VALUES (?,?,?,?,?,?)', chartValues)

    dbConnection.commit()

def sleepRandom(processBar=None, min=15, max=60):
    value = randint(min, max)
    while value > 0:
        if processBar:
            message = alignProgressBarDescription('Disguise Pause: {} seconds remaining'.format(value))
            processBar.set_description(message)
            processBar.refresh()

        sleep(1)
        value -= 1

def main(session, countries, update, disguise):
    dbConnection = sqlite3.connect('lido.sqlite')

    airports = getAirports(session, countries)
    print('Downloading airports...')
    countryFilter = ' for ' + countries.__repr__() if len(countries) > 0 else ''
    print('Found {} airports{}.'.format(len(airports), countryFilter))
    if len(airports) == 0:
        exit()

    userInput = input('Do you want to continue to download all charts for these? (y/[n]): ')
    if userInput not in ['y', 'Y']:
        exit()

    processBar = tqdm(airports.items())
    isFirst = True
    for icao, airport in processBar:
        airportExists = entryForAirportExists(icao, dbConnection)
        if airportExists and not update:
            continue
        else:
            if disguise and not isFirst:
                sleepRandom(processBar)

            isFirst = False
            charts = getChartsForAirport(session, icao)
            processBar.set_description(alignProgressBarDescription('Collecting charts for {}'.format(icao)))
            processBar.refresh()

            i = 1
            n = len(charts)
            pdfs = {}
            for chart in charts:
                chartId = chart['chart_id']
                chartType = chart['chart_type']
                name = chart['chart_name']
                downloadId = getDownloadIdForChart(session, chartId)
                pdf = downloadChartAsPdf(downloadId)
                pdfs[chartId] = pdf

                processBar.set_description(alignProgressBarDescription('Downloading chart {} ({}|{}) \'{} {}\''.format(icao, i, n, chartType, name)))
                processBar.refresh()
                i += 1

            saveAirport(dbConnection, airport, airportExists, charts, pdfs)

    dbConnection.close()

def alignProgressBarDescription(text):
    return text.ljust(80)[0:80]

def parseArguments():
    argparser = argparse.ArgumentParser(
        prog='LIDO crawler',
        description='Crawls the Nav Data Pro API of Aerosoft for all available LIDO charts.'
    )
    argparser.add_argument(
        'SESSION', nargs="?",
        help='A valid session id that will be used for all API calls'
    )
    argparser.add_argument(
        '-u',
        '--update',
        help="Updates existing entries in your database.",
        action="store_true"
    )
    argparser.add_argument(
        '-c',
        '--country',
        help="Only crawl charts for the provided ICAO country code",
        metavar='COUNTRY_CODE',
        default=''
    )
    argparser.add_argument(
        '-d',
        '--disguise',
        help="Adds random pauses between airports to disguise the crawling. Recommended for larger chunks.",
        action="store_true"
    )
    return argparser.parse_args()

if __name__ == '__main__':
    args = parseArguments()
    countries = [ country for country in args.country.split(',') if len(country) > 0 ]
    main(args.SESSION, countries, args.update, args.disguise)