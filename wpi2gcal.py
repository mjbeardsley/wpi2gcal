#!/usr/bin/env python2.7

# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 15:07:12 2015

@author: matt
"""

import requests
import getpass
from HTMLParser import HTMLParser
import re
import copy
import datetime as dt
from oauth2client.client import flow_from_clientsecrets
import webbrowser
import httplib2
from googleapiclient.discovery import build

def test_html_out(text):
    f = open('cal.html','w')
    f.write(text.encode('UTF-8'))
    f.close()

# auth with google
flow = flow_from_clientsecrets('client_secret_705796806555-s9otnbf01sncbhkus96fqvalug6ogsu0.apps.googleusercontent.com.json',
                               scope='https://www.googleapis.com/auth/calendar',
                               redirect_uri='urn:ietf:wg:oauth:2.0:oob')
auth_uri = flow.step1_get_authorize_url()
webbrowser.open_new_tab(auth_uri)
code = str(raw_input('Paste code: '))
credentials = flow.step2_exchange(code)
http = httplib2.Http()
http = credentials.authorize(http)
service = build('calendar', 'v3', http=http)

# auth with wpi
usr = str(raw_input('WPI Username: '))
pas = getpass.getpass(prompt='WPI Password: ')
# choose term here eventually too
# seasondict = {"fall":1,"spring":2,"summer":3}
# term = year*100 + seasondict[season]
# login to wpi
header = {'Referer':'https://bannerweb.wpi.edu/pls/prod/twbkwbis.P_WWWLogin'}
loginurl = 'https://bannerweb.wpi.edu/pls/prod/twbkwbis.P_ValLogin'
logindata = {'sid':usr,'PIN':pas}
del pas
r = requests.post(loginurl,headers=header,data=logindata)
cookies = r.cookies
r = requests.post(loginurl,headers=header,data=logindata,cookies=cookies)
cookies = r.cookies
# choose term
termurl = 'https://bannerweb.wpi.edu/pls/prod/bwskfshd.P_CrseSchdDetl'
termdata = {'term_in':201502}
#termdata = term
r = requests.post(termurl,headers=header,data=termdata,cookies=cookies)
cookies = r.cookies
htmltxt = r.text
# log out
logouturl = 'https://bannerweb.wpi.edu/pls/prod/twbkwbis.P_Logout'
r = requests.get(logouturl,headers=header,cookies=cookies)
# write html to file
#test_html_out(htmltxt)

# parse the html into events
courselist = list()

class Course(object):
    def __init__(self,title):
        self.title = title
        self.qualities = dict()
        self.meetings = []
        self.event_template = {
            "start": {
                "dateTime": None,
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": None,
                "timeZone": "America/New_York"
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{
                    "method": "popup",
                    "minutes": 15
                }]
            },
            "summary": None,
            "visibility": "default",
            "recurrence": None,
#                ["RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;UNTIL=20150501T235959Z"]
            "description": None,
            "location": None,
            "source": {
                "title": "WPI Bannerweb Detail Schedule",
                "url": "https://bannerweb.wpi.edu"
            }
        }
    def create_event(self):
        events = list()
        daymap = {"M"  :"MO",
                  "T"  :"TU",
                  "W"  :"WE",
                  "R"  :"TH",
                  "F"  :"FR"}
        monmap = {"Jan":"01",
                  "Feb":"02",
                  "Mar":"03",
                  "Apr":"04",
                  "May":"05",
                  "Jun":"06",
                  "Jul":"07",
                  "Aug":"08",
                  "Sep":"09",
                  "Oct":"10",
                  "Nov":"11",
                  "Dec":"12"}
        def create_rrule(meeting):
            rrule = list()
            #"RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;UNTIL=20150501T235959Z"
            try:
                byday = ",".join([daymap[d] for d in list(meeting["Days"])])
                plaindate = meeting["Date Range"].split(' - ')[1]
                plaindate_yr = plaindate.split(", ")[1]
                plaindate_dymn = plaindate.split(", ")[0].split(" ")
                plaindate_mn = monmap[plaindate_dymn[0]]
                plaindate_dy = plaindate_dymn[1]
                until = plaindate_yr + plaindate_mn + plaindate_dy
                rrule_str = "RRULE:FREQ=WEEKLY;BYDAY=%s;UNTIL=%sT235959Z" % (byday,until)
                rrule.append(rrule_str)
            except TypeError:
                rrule = None
            return rrule
        def create_description(meeting):
            def unknown(elt):
                if elt is None:
                    return "Unknown"
                else: 
                    return elt
            return unknown(meeting["Schedule Type"]) + " at " + unknown(meeting["Where"]) + "."
        def create_endDateTime(meeting):
            try:
                plaindate = meeting["Date Range"].split(' - ')[0]
                plaindate_yr = plaindate.split(", ")[1]
                plaindate_dymn = plaindate.split(", ")[0].split(" ")
                plaindate_mn = monmap[plaindate_dymn[0]]
                plaindate_dy = plaindate_dymn[1]
                date = '-'.join([plaindate_yr,plaindate_mn,plaindate_dy])
                plaintime = meeting["Time"].split(" - ")[1]
                time_ampm = plaintime.split(" ")
                ampm = time_ampm[1]
                time = time_ampm[0].split(":")
                hour = time[0]
                if ampm == "pm":
                    hour = str(int(hour) + 12)
                if len(hour) == 1:
                    hour = "0" + hour
                mins = time[1]
                time = ':'.join([hour,mins,"00"])
                ret = date+"T"+time
            except AttributeError:
                ret = None
            return ret
        def create_startDateTime(meeting):
            try:
                plaindate = meeting["Date Range"].split(' - ')[0]
                plaindate_yr = plaindate.split(", ")[1]
                plaindate_dymn = plaindate.split(", ")[0].split(" ")
                plaindate_mn = monmap[plaindate_dymn[0]]
                plaindate_dy = plaindate_dymn[1]
                date = '-'.join([plaindate_yr,plaindate_mn,plaindate_dy])
                plaintime = meeting["Time"].split(" - ")[0]
                time_ampm = plaintime.split(" ")
                ampm = time_ampm[1]
                time = time_ampm[0].split(":")
                hour = time[0]
                if ampm == "pm":
                    hour = str(int(hour) + 12)
                if len(hour) == 1:
                    hour = "0" + hour
                mins = time[1]
                time = ':'.join([hour,mins,"00"])
                ret = date+"T"+time
            except AttributeError:
                ret = None
            return ret
        def create_summary(meeting):
            return self.title
        def create_location(meeting):
            return meeting['Where']
        def doublecheck(event):
            daymapnum = {0:"MO",
                         1:"TU",
                         2:"WE",
                         3:"TH",
                         4:"FR",
                         5:"SA",
                         6:"SU"}
            start = dt.datetime.strptime(event["start"]["dateTime"], '%Y-%m-%dT%H:%M:%S')
            end = dt.datetime.strptime(event["end"]["dateTime"], '%Y-%m-%dT%H:%M:%S')
            daynum = start.weekday()
            checkagainst = re.split("BYDAY\=|;UNTIL",event["recurrence"][0])[1]
            while not checkagainst.__contains__(daymapnum[daynum]):
                start += dt.timedelta(days=1)
                end += dt.timedelta(days=1)
                daynum = start.weekday()
            event["start"]["dateTime"] = start.isoformat('T').split(".")[0]
            event["end"]["dateTime"] = end.isoformat('T').split(".")[0]
            return event
        for meeting in self.meetings:
            event = copy.deepcopy(self.event_template)
            event["recurrence"]        =         create_rrule(meeting)
            event["summary"]           =       create_summary(meeting)
            event["start"]["dateTime"] = create_startDateTime(meeting)
            event["end"]["dateTime"]   =   create_endDateTime(meeting)
            event["description"]       =   create_description(meeting)
            event["location"]          =      create_location(meeting)
            if  not any(isinstance(i,type(None)) for i in [event["recurrence"],
                                                     event["start"]["dateTime"],
                                                     event["end"]["dateTime"]]):
                events.append(doublecheck(event))
        return events

class Meetings(object):
    def __init__(self,dictall):
        self.dictall = dictall

# parse the html into events
class HTMLEventParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.datamap = {"38":"&","nbsp":None}
        self.title = None
        self.nextCourse = None
        self.stopLookingQualities = False
        self.nextDataNewObj = False
        self.setMeetings = False
        self.objQualities = dict()
        self.setKey = False
        self.setVal = False
        self.key = None
        self.val = None
        self.courseIsSet = False
        self.meetingKeys = list()
        self.meetingVals = list()
        self.meetingValCount = -1
    def handle_starttag(self, tag, attrs):
        if tag == 'table' and attrs[1][1].__contains__('course'):
            self.nextDataNewObj = True
        elif tag == 'table' and attrs[1][1].__contains__('times'):
            self.setMeetings = True
        elif tag == 'th' and self.setMeetings is False:
            self.setKey = True
        elif tag == 'td' and self.setMeetings is False:
            self.setVal = True
        elif self.setMeetings is True:
            if tag == 'th':
                self.appendKey = True
            elif tag == 'td':
                self.appendVal = True
                self.meetingValCount += 1
                self.meetingVals.append(None)
            else:
                self.appendKey = False
                self.appendVal = False
    def handle_endtag(self, tag):
        if tag == 'table':
            self.stopLookingQualities = True
            self.nextCourse.qualities = self.objQualities
            if len(self.meetingKeys) > 0 and len(self.meetingVals) > 0:                
                numparams = len(self.meetingKeys)
                assert(len(self.meetingVals) % numparams == 0)
                total = 0
                while total < len(self.meetingVals):
                    newDict = {key:value for key,value in zip(self.meetingKeys,self.meetingVals[total:total+numparams])}                    
                    self.nextCourse.meetings.append(newDict)
                    total += numparams
        elif (tag == 'td' and self.setMeetings is False) or (tag == 'th' and self.setMeetings is False):
            self.setKey = False
            self.setVal = False
        elif tag == 'caption':
            self.nextCourse = Course(self.title)
            self.nextDataNewObj = False
    def handle_data(self, data):
        if not self.stopLookingQualities:
            if self.nextDataNewObj:
                if self.title is None:
                    self.title = data
                else:
                    self.title += data
            elif self.setKey:
                self.key = data
                self.objQualities[self.key] = None
#                self.setKey = False
            elif self.setVal:
                self.val = data
                if self.objQualities[self.key] is None:
                    self.objQualities[self.key] = self.val
                else:
                    self.objQualities[self.key] += self.val
#                self.setVal = False
        else:
            assert(not (self.appendKey and self.appendVal))
            if self.appendKey:
                self.meetingKeys.append(data)
            if self.appendVal:
                self.meetingVals[self.meetingValCount] = data
    def handle_entityref(self, data):
        data = self.datamap[data]
        self.handle_data(data)
    def handle_charref(self, data):
        data = self.datamap[data]
        self.handle_data(data)

htmltxt = htmltxt.replace('\n','')
htmltxt = re.split('<br>|<BR>',htmltxt)
numbrall = len(htmltxt)
numbrhead = 5
numbrfoot = 3
htmltxt = htmltxt[numbrhead:numbrall-numbrfoot]
for section in htmltxt:
    parser = HTMLEventParser()
    parser.feed(section)
    courselist.append(parser.nextCourse)

# use google calendar api to add events to the google calendar

calendar = {
    'summary': 'WPI Classes',
    'timeZone': 'America/New_York'
}

#f = open('calendarids','r+')
#f.seek(0)
#contents = f.read().split('\n')
#contents.pop()
#all_usr_calids = {contents_inner.split('\t')[0]:contents_inner.split('\t')[1] for contents_inner in contents}
#if usr not in all_usr_calids.keys():
#    created_calendar = service.calendars().insert(body=calendar).execute()
#    current_calid = created_calendar['id']
##    f.seek(0,2)
#    f.writelines([usr,'\t',current_calid,'\n'])
#else:
#    current_calid = all_usr_calids[usr]
#    service.calendars().delete(current_calid).execute()
#f.close()

created_calendar = service.calendars().insert(body=calendar).execute()
current_calid = created_calendar['id']

eventlist = [course.create_event() for course in courselist]
eventlist_flat = [item for sublist in eventlist for item in sublist]
for event in eventlist_flat:
    service.events().insert(calendarId=current_calid,body=event).execute()

#         4. That's it...?

