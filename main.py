#!/usr/bin/python
# -*- coding: utf-8 -*-

from mechanize import Browser
from lxml.html import fromstring
from time import *
from thread import start_new_thread
import requests


class Main:
    email = ''
    password = ''
    html = ''
    authenticity_token = ''
    accidents = {}
    status = ''
    cars = {}
    fireman_at_accident = 0
    session = None
    headers = {
        "Content - Type": "application / x - www - form - urlencoded",
        "User-Agent":
        "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }
    missingcases = {
        'Loeschfahrzeug (LF)': 'LF 20/16',
        'Loeschfahrzeuge (LF)': 'LF 20/16',
        'Feuerwehrleute': 'LF 20/16',
        'FuStW': 'FuStW',
        'ELW 1': 'ELW 1',
        'ELW 2': 'ELW 2',
        'Drehleitern (DLK 23)': 'DLK 23',
        'GW-Messtechnik': 'GW-Messtechnik',
        'GW-Atemschutz': 'GW-A',
        'Ruestwagen oder HLF': 'RW',
        'GW-Oel': 'GW-Öl',
    }

    def __init__(self):
        self.email = raw_input('Email: ')
        self.password = raw_input('Passwort: ')
        self.login()

        while True:
            start_new_thread(self.thread, ())

            if int(strftime("%M")) % 30 == 0:
                self.login()

            sleep(5)

    def thread(self):
        print "hier"
        self.get_all_accidents()

        for key, accident in self.accidents.iteritems():
            if accident['status'] == 'rot':
                self.get_accident(key, accident)

    def login(self):
        url = "https://www.leitstellenspiel.de/users/sign_in"

        br = Browser()

        response = br.open(url)

        self.parse_token(response.read())

        data = {
            'authenticity_token': self.authenticity_token,
            'user[email]': self.email,
            'user[password]': self.password,
            'user[remember_me]': 1,
            'commit': 'Einloggen'
        }

        self.session = requests.session()
        self.session.headers.update(self.headers)

        request = self.session.post(url, data=data)
        self.parse_token(request.text)

    def parse_token(self, html):
        tree = fromstring(html)
        self.authenticity_token = tree.xpath('//meta[@name="csrf-token"]/@content')[0]

    def get_all_accidents(self):
        mission = self.session.get('https://www.leitstellenspiel.de/')
        startpoint = mission.text.find('missionMarkerAdd')
        endpoint = mission.text.find('missionMarkerBulkAdd', startpoint)
        ids = mission.text[startpoint:endpoint]
        ids = ids.split('\n')

        i = 0

        self.accidents = {}

        while i < len(ids) - 1:
            idpoint = ids[i].find(',"id":')
            statusstartpoint = ids[i].find(',"icon":')
            statusendpoint = ids[i].find(',"caption":', statusstartpoint)
            missingstartpoint = ids[i].find(',"missing_text":')
            missingendpoint = ids[i].find(',"id":', missingstartpoint)

            t = 0
            missingarray = {}

            if 'Feuerwehrleute' in ids[i][missingstartpoint + 16: missingendpoint]:
                missing = ids[i][missingstartpoint + 16: missingendpoint][1:].split(',')

                while t < len(missing):
                    if missing[t][2:][-1:] == '"':
                        missingarray[int(missing[t][24:26])] = missing[t][27:-2]
                    else:
                        missingarray[int(missing[t][24:26])] = missing[t][27:-1]
                    t = t + 1
            else:
                missing = ids[i][missingstartpoint + 16: missingendpoint][43:].split(',')

                while t < len(missing):
                    if missing[t][2:][-1:] == '"':
                        missingarray[missing[t][:2]] = missing[t][2:][:-1]
                    else:
                        missingarray[missing[t][:2]] = missing[t][2:]
                    t = t + 1

            self.accidents[ids[i][idpoint + 6: idpoint + 15]] = {
                'status': ids[i][statusstartpoint + 8: statusendpoint][-4:-1],
                'missing': missingarray
            }
            i = i + 1

    def get_accident(self, accidentid, accident):
        mission = self.session.get('https://www.leitstellenspiel.de/missions/' + accidentid)

        self.parse_fireman_at_accident(mission.text)
        self.parse_available_cars(mission.text)

        if accident['missing'] != {'': ''}:
            for count, string in accident['missing'].iteritems():
                string = str(string).replace("\u00f6", "oe")
                string = string.replace("\u00d6", "Oe")
                string = string.replace("\u00fc", "ue")

                if string[0] == ' ':
                    string = string[1:]

                t = 0

                if string == 'Feuerwehrleute':
                    newcount = int(count) - int(self.fireman_at_accident)

                    while t < newcount:
                        for carid, cartype in self.cars.iteritems():

                            if cartype == self.missingcases[string]:
                                self.send_car_to_accident(accidentid, carid)
                                del self.cars[carid]
                                t = t + 1
                                break
                else:
                    while t < int(count):
                        for carid, cartype in self.cars.iteritems():

                            if cartype == self.missingcases[string]:
                                self.send_car_to_accident(accidentid, carid)
                                del self.cars[carid]
                                t = t + 1
                                break
        else:
            for key, value in self.cars.iteritems():
                if value == 'LF 20/16':
                    self.send_car_to_accident(accidentid, key)
                    break

    def parse_fireman_at_accident(self, html):
        tree = fromstring(html)
        people = tree.xpath('//div[small[contains(., "Feuerwehrleute")]]/small//text()')
        for value in people:
            if value[11:-15] == 'Feuerwehrleute':
                self.fireman_at_accident = value[38:]

    def parse_available_cars(self, html):
        tree = fromstring(html)
        cars = tree.xpath('//tr[@class="vehicle_select_table_tr"]/@id')
        types = tree.xpath('//tr[@class="vehicle_select_table_tr"]/@vehicle_type')

        self.cars = {}

        for i, value in enumerate(cars):
            self.cars[value[24:]] = types[i]

    def send_car_to_accident(self, accident, car):
        url = 'https://www.leitstellenspiel.de/missions/' + accident + '/alarm'
        data = {
            'authenticity_token': self.authenticity_token,
            'commit': 'Alarmieren',
            'next_mission': 0,
            'vehicle_ids[]': car
        }

        self.session.post(url, data=data)

main = Main()
