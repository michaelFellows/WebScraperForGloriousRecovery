import datefinder
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from secret import username, password
import requests
import pandas as pd
import json
import base64
import urllib.request
import os
import time
from io import StringIO
from html.parser import HTMLParser

# This class is used to strip HTML tags when we have to
# check if an event has been updated. Since we use
# string comparisons, we want to make it so that there
# is not whitespace or HTML tags just to avoid any errors.
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

#Get Organization URLs into a text file
fileObj = open("facebookURLs.txt","r")
organizationArray = fileObj.read().splitlines()
fileObj.close()

payload = {
    'email': username,
    'password': password
}

LOGIN_URL = "https://www.facebook.com/login/?"
LIST_OF_EVENT_POST_OBJECTS = []
LIST_OF_START_TIMES = []
for i in organizationArray:
    LINK_TO_ORGANIZATION = i
    with requests.Session() as session:
        #Log in to Facebook and find all <a> tags on the page
        post = session.post(LOGIN_URL, data = payload)
        page = requests.get(LINK_TO_ORGANIZATION)
        soup = BeautifulSoup(page.content, "html.parser")
        links = [a.get('href') for a in soup.find_all('a', href=True)]

    df = pd.DataFrame(links)
    df.columns = ['Links']

    #Pull only the URLs that start with /events/
    link = df['Links'].loc[df['Links'].str.startswith('/events/', na=False)].to_list()

    counter = 0
    for j in link:
        hasBeenScraped = False
        eventHasBeenUpdated = False
        mbasic_link = 'http://mbasic.facebook.com' + link[counter]
        standard_link = 'http://www.facebook.com' + link[counter]
        scrapedEventsArray = []
        fileObj = open("scrapedEvents.txt","r")
        scrapedEventsArray = fileObj.read().splitlines()
        fileObj.close()
        print(scrapedEventsArray)
        # This is the logic that checks if an event has already been scraped/posted
        for k in scrapedEventsArray:
            if mbasic_link[35:49] == k:
                hasBeenScraped = True
                print("URL has already been scraped")
        if hasBeenScraped == False:
            fileObj = open("scrapedEvents.txt","a")
            fileObj.write(mbasic_link[35:49:] + "\n")
            
        event_title_list = []
        time_list = []
        loc_list = []
        description_list = []
        image_list = []
        ticket_filter = []

        # Parsing the html for all of the relevant event data
        with requests.Session() as session:
            post = session.post(LOGIN_URL, data=payload)
            page = requests.get(mbasic_link)
            page2 = requests.get(standard_link)
            soup = BeautifulSoup(page.content, "html.parser")
            soup2 = BeautifulSoup(page2.content, "html.parser")
            soupString = str(soup2)
            start = soupString.find("data-testid=\"event_ticket_link\"><a class=\"_36hm\" href=\"") + len("data-testid=\"event_ticket_link\"><a class=\"_36hm\" href=\"https://l.facebook.com/l.php?u=")
            end = soupString.find("eventtix&amp;h=") + len("eventtix&amp")
            ticketURL = soupString[start:end]
            ticketURL = ticketURL.replace("%3A",":").replace("%2F","/").replace("%3F","?").replace("%3D","=")
            title_filter = soup.find_all('h1') 
            time_filter = soup.find_all('dt')
            loc_filter = soup.find_all('dt')
            description_filter = soup.find_all("div", {"class": "_52ja _2pi9 _2pip _2s23"})
            image_filter = soup.find_all('img')
            organization_filter = soup.find_all('a')

        for detail in title_filter:
            detail = str(detail.text)
            if detail == 'Facebook': # ignore facebook text
                pass
            else:
                event_title_list.append(detail) # append just the title
        print("Title is " + event_title_list[0])
                
        temp = []

        for detail in time_filter:
            detail = str(detail.text)
            temp.append(detail) # append text to the temp list
        time_list.append(temp[0]) # time is always going to be the first thing found so the rest is ignored
        print("Time is " + time_list[0])

        temp = []
        for detail in loc_filter:
            detail = str(detail.text)
            temp.append(detail)# append text to the temp list
        loc_list.append(temp[1])# location is the second string that will pop up with a dt tag
        print("Location is " + loc_list[0])

        temp = []
        hasDescription = True
        for detail in description_filter:
            detail = str(detail.text);
            if detail != "":
                temp.append(detail)
            else:
                hasDescription = False
        if hasDescription:
            description_list.append(temp[0])
        else:
            description_list.append("")
        print("Description is " + description_list[0])

        temp = []
        for detail in image_filter:
            detail = str(detail.attrs['src']);
            temp.append(detail)
        image_list.append(temp[2])
        print("Image src URL is " + image_list[0])
        
        title = event_title_list[0]
        start_time = time_list[0]
        location = loc_list[0]
        description = description_list[0]
        image = image_list[0]
        organization = str(organization_filter[5].text)
        organizationURL = str("https://www.facebook.com" + organization_filter[5].attrs['href'])

        # function that gets start and end time from time string
        matches = list(datefinder.find_dates(start_time))
        start_time = str(matches[0])
        end_time = ""
        if len(matches) == 2: #if there IS an endtime
            end_time = start_time[0:11] + str(matches[1])[11:19]
        else: #there isnt an end time, trim the start time time zone
            start_time = start_time[0:(len(start_time)-6)]
            end_time = start_time

        counter+=1

        # This is to get rid of any characters that don't work in a URL
        urlSafeTitle = ''.join(ch for ch in title if ch.isalnum())
        if ticketURL == "":
            embedTicketButton = ""
        else:
            embedTicketButton = "\n<b>To purchase tickets for "+ title + ", please " + "<a style=\"color: blue !important\" href=\""+ticketURL+"\" title=\"Buy Tickets\" target=\"_blank\">click here.</a></b>"

        linkToFacebookEvent = "\n<b>To view this event on Facebook, please "+"<a style=\"color: blue !important\" href=\""+standard_link+"\" title=\"View on Facebook\" target=\"_blank\">click here.</a></b>"

        # If it is an online event, we don't want to make a google maps URL
        if 'online' not in location.lower():
            linkToDirections = "\n<b>For directions to this event, please "+"<a style=\"color: blue !important\" href=\""+"https://maps.google.com/?q="+location+"\" title=\"Get directions\" target=\"_blank\">click here.</a></b>"
        else:
            linkToDirections = ""

        embedOrganization = "\n<i>Event by: "+"<a style=\"color: blue !important\" href=\""+organizationURL+"\" title=\""+organization+" on Facebook"+"\" target=\"_blank\">"+organization+"</a></i>"
        
        description = embedOrganization + "\n" + description + embedTicketButton + linkToFacebookEvent + linkToDirections
        print(description)

        # THIS IS WHERE WE WILL CHECK IF THE EVENT HAS BEEN UPDATED
        print(urlSafeTitle)
        if hasBeenScraped:
            print("Checking if event has been updated on facebook...")
            descriptionFromJSON = "\n"
            searchEventsURL = "https://gloriousrecovery.org/wp-json/tribe/events/v1/events"
            mediaRequest = requests.get(url=searchEventsURL)
            jsonResponse = mediaRequest.json()
            for i in range(len(jsonResponse['events'])):
                slug = jsonResponse['events'][i]['slug']
                if urlSafeTitle.lower() in slug:
                    indexInJson = i
                    break
            titleFromJSON = jsonResponse['events'][indexInJson]['title']
            descriptionFromJSON = descriptionFromJSON + jsonResponse['events'][indexInJson]['description']
            startTimeFromJSON = jsonResponse['events'][indexInJson]['start_date']
            endTimeFromJSON = jsonResponse['events'][indexInJson]['end_date']
            eventIDFromJSON = jsonResponse['events'][indexInJson]['id']

            descriptionFromJSON = strip_tags(descriptionFromJSON)
            descriptionSansHTML = strip_tags(description)
            descriptionFromJSON = ''.join(ch for ch in descriptionFromJSON if ch.isalnum())
            descriptionSansHTML = ''.join(ch for ch in descriptionSansHTML if ch.isalnum())
            titleFromJSON = ''.join(ch for ch in titleFromJSON if ch.isalpha())

            print("Titles are the same? ")
            print(urlSafeTitle == titleFromJSON)
            print("Descriptions are the same? ")
            print(descriptionSansHTML == descriptionFromJSON)
            print("start time is the same? ")
            print(start_time == startTimeFromJSON )
            print("end time is the same? ")
            print(end_time == endTimeFromJSON)

            if descriptionSansHTML == descriptionFromJSON and start_time == startTimeFromJSON and end_time == endTimeFromJSON and urlSafeTitle == titleFromJSON:
                eventHasBeenUpdated = False
                print("EVENT HAS NO CHANGES TO REFLECT")
            else:
                eventHasBeenUpdated = True
                print("EVENT HAS NEW CHANGES")

        if eventHasBeenUpdated or hasBeenScraped == False:
            user = "*USERNAME FOR WORDPRESS ACCOUNT*"
            password = "*PASSWORD FROM APPLICATION PASSWORDS*"
            featured = False
            if organization == 'Glorious Recovery':
                featured = True
            # Download the image for the event so we can upload it to wordpress
            urllib.request.urlretrieve(image, urlSafeTitle+".jpg")

            #We want to upload that image to wordpress
            imageType = 'image/jpg'
            imageName = urlSafeTitle + '.jpg'
            headers = { 'Content-Type': imageType,'Content-Disposition' : 'attachment; filename=./'+ urlSafeTitle + '.jpg'}
            post = {
            'caption': urlSafeTitle
            }
            data = open(imageName, 'rb').read()

            imageResponse = requests.post(url='https://gloriousrecovery.org/wp-json/wp/v2/media/', data=data, headers=headers, json=post, auth=(user, password))
            os.remove(urlSafeTitle+".jpg")
            searchURL = 'https://gloriousrecovery.org/wp-json/wp/v2/media/?search='+ urlSafeTitle

            #We want to get the URL of the uploaded image from the wordpress server
            mediaRequest = requests.get(url=searchURL)
            jsonResponse = mediaRequest.json()
            imageURL = jsonResponse[0]['guid']['rendered']
            url = "https://gloriousrecovery.org/wp-json/tribe/events/v1/events"
            if(eventHasBeenUpdated):
                url = "https://gloriousrecovery.org/wp-json/tribe/events/v1/events/" + str(eventIDFromJSON)
            credentials = user + ":" + password
            token = base64.b64encode(credentials.encode())
            header = {'Authorization': 'Basic ' + token.decode('utf-8')}
            print("PRINTING START TIME: " + start_time)
            print("PRINTING END TIME: " + end_time)
            # Finally, post to wordpress
            post = {
                'title'    : title,
                'status'   : 'publish', 
                'description'  : description,
                'start_date': start_time,
                'end_date': end_time,
                'image': imageURL,
                'slug': urlSafeTitle,
                'featured': featured
            }
            response = requests.post(url , headers=header, json=post)
            print(response)






