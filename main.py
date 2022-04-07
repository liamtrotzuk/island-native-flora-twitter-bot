#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 27 17:05:12 2022

@author: liamtrotzuk
"""

# General
import pandas as pd
from datetime import date
from random import seed, randint
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="service_auth.json"
import re
import requests
import shutil

#Scraping
import ssl #have to do this workaround for read_html - urllib looks at the base SSL certificates in the highest level Python library (even above /liamtrotzuk/ - literally looks in /Library/Frameworks) - and I don't want to screw with the file system by adding it there.
import requests
from bs4 import BeautifulSoup

# Twitter
import tweepy
# Google
from google.cloud import storage
VAR_client = storage.Client(project="XXX")
from google.cloud.storage import Blob

try:
  VAR_bucket = VAR_client.get_bucket('raw_inputs')
except google.cloud.exceptions.NotFound:
    print('Sorry, that bucket does not exist!')
    
VAR_blob = VAR_bucket.blob('DF_PLANTS_Main.csv')
VAR_blob.download_to_filename("DF_PLANTS_Main.csv")
DF_PLANTS_a = pd.read_csv("DF_PLANTS_Main.csv")

DF_PLANTS_b = DF_PLANTS_a[DF_PLANTS_a['Image Gallery'].notnull()]

DF_PLANTS_Hawaii_a = DF_PLANTS_b
DF_PLANTS_Hawaii_a['HI_Native'] = DF_PLANTS_Hawaii_a['Native Status'].str.find('HI(N)')
DF_PLANTS_Hawaii_b = DF_PLANTS_Hawaii_a[DF_PLANTS_Hawaii_a['HI_Native'] != -1]

DF_PLANTS_PR_a = DF_PLANTS_b
DF_PLANTS_PR_a['PR_Native'] = DF_PLANTS_PR_a['Native Status'].str.find('PR(N)')
DF_PLANTS_PR_b = DF_PLANTS_PR_a[DF_PLANTS_PR_a['PR_Native'] != -1]

DATE_today = date.today()

def FUN_clean_df(FUN_VAR_DF_a):
    FUN_VAR_DF_b = FUN_VAR_DF_a[['Genus','Species','Common Name','Duration','Growth Habit','Family Common Name']]
    FUN_VAR_DF_b = FUN_VAR_DF_b.drop_duplicates()
    FUN_VAR_DF_b = FUN_VAR_DF_b.loc[(FUN_VAR_DF_b['Genus'].notnull())
                                    & (FUN_VAR_DF_b['Species'].notnull())
                                    & (FUN_VAR_DF_b['Common Name'].notnull())
                                    & (FUN_VAR_DF_b['Duration'].notnull())
                                    & (FUN_VAR_DF_b['Growth Habit'].notnull())
                                    & (FUN_VAR_DF_b['Family Common Name'].notnull())]
    return FUN_VAR_DF_b

DF_Hawaii = FUN_clean_df(DF_PLANTS_Hawaii_b)
DF_Puerto = FUN_clean_df(DF_PLANTS_PR_b)

#prep for scrape
#possibly don't have to run the sll line on a Linux VM? related to the above stupid SSL thing
ssl._create_default_https_context = ssl._create_unverified_context
DICT_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Mobile Safari/537.36'}
STR_sep = '(.jpeg)|(.JPEG)|(.jpg)|(.JPG)|(.png)|(.PNG)'

def FUN_isolate_plant_and_test_URL(FUN_VAR_DF_c):
    NUM_status_test = 1
    while NUM_status_test != 200:
        try:
            NUM_DF_len = len(pd.Index(FUN_VAR_DF_c))
            NUM_random = randint(1,NUM_DF_len)
            DF_trimmed = FUN_VAR_DF_c[NUM_random:NUM_random+1]
            GEN_a = requests.get('https://species.wikimedia.org/wiki/' + DF_trimmed.iloc[0,0] + '_' + DF_trimmed.iloc[0,1])
            GEN_b = BeautifulSoup(GEN_a.text,'html.parser')
            GEN_c = GEN_b.find_all('img')[0]['src']
            GEN_d = GEN_c.replace('/thumb','')
            GEN_e = re.split(STR_sep,GEN_d)
            STR_img_url = "https:" + GEN_e[0] + GEN_e[3]
            STR_img_url_just_img = STR_img_url.split("/")[-1]
            GEN_f = requests.get(STR_img_url,headers=DICT_headers,stream=True)
            NUM_status_test = GEN_f.status_code
            
        except:
            pass
        
        else:
            if NUM_status_test == 200: 
                
                #copy file to desktop
                GEN_f.raw.decode_content = True
                with open(STR_img_url_just_img,'wb') as f:
                    shutil.copyfileobj(GEN_f.raw,f)
                    
                #figure out if we use 'a' or 'an'
                if DF_trimmed.iloc[0,3][0] in ['A','E','I','O','U','H']:
                    STR_a_or_an = 'an'
                else:
                    STR_a_or_an = 'a'
                    
                # tweet text
                STR_tweet_text = DF_trimmed.iloc[0,0] + " " + DF_trimmed.iloc[0,1] + ", commonly known as " + DF_trimmed.iloc[0,2] + ", is " + STR_a_or_an + " " + DF_trimmed.iloc[0,3].lower().replace(" ","").replace(",","/") + " " + DF_trimmed.iloc[0,4].lower().replace(" ","").replace(",","/") + " in the " + DF_trimmed.iloc[0,5] + "."
                    
                return STR_tweet_text,STR_img_url_just_img
        
TUP_Hawaii = FUN_isolate_plant_and_test_URL(DF_Hawaii)
TUP_Puerto = FUN_isolate_plant_and_test_URL(DF_Puerto)
    
#Twitter 
auth = tweepy.OAuthHandler("XXX", "XXX")
auth.set_access_token("XXX", "XXX")
api = tweepy.API(auth)
api.update_status_with_media(TUP_Hawaii[0],TUP_Hawaii[1])

#Twitter 
auth = tweepy.OAuthHandler("XXX", "XXX")
auth.set_access_token("XXX", "XXX")
api = tweepy.API(auth)
api.update_status_with_media(TUP_Puerto[0],TUP_Puerto[1])

#cleanup
os.remove(TUP_Hawaii[1])
os.remove(TUP_Puerto[1])
#remove all else
for name in dir():
    if not name.startswith('_'):
        del globals()[name]
import gc
gc.collect()
