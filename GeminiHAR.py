
#setx API_KEY "AIzaSyAKopIqRASuXw7TY8a6WD7mi4saFRFqPfA"

shortcut = 'data-har.lnk'

ini_date="2024-07-26 02:00:00"
end_date="2024-07-27 01:59:59"
time_step = 1
#users=["16fe","5b66","ed9c"]
users=["5b66","ed9c"]


activity_rooms = {
  'cooking': 'kitchen',
  'shower': 'bathroom',
  'toileting': 'bathroom',
  'pc': 'office',  # PC can be in multiple rooms
  'sleep': 'bedroom',
  'kitchen': 'kitchen',
  'resting': 'living room',  # Resting can occur in multiple rooms
  'exit': 'exit door',  # Exit is not associated with a specific room
}

activity_name = {
  'cooking': 'cooking or doing tasks',
  'shower': 'shower',
  'toileting': 'toileting or washing',
  'pc': 'using pc',  # PC can be in multiple rooms
  'sleep': 'sleeping',
  'kitchen': 'staying at kitchen',
  'resting': 'resting',  # Resting can occur in multiple rooms
  'exit': 'leaving home',  # Exit is not associated with a specific room
}
##LIBRARIES

import os
import google.generativeai as genai
import sys
import winshell


import numpy as np
from pandas import read_csv    
import pandas as pd
import time

from datetime import datetime, timedelta
import configparser

from google.api_core.exceptions import ResourceExhausted

config = configparser.ConfigParser()
config.read('llms-config.txt')

##TIMING

off_zone=60*60*2

def day_time(ti):
    return int((int)((ti+off_zone)/(60*60*24)))


def time2str(tt):
    return datetime.fromtimestamp(tt).strftime("%Y-%m-%d %H:%M:%S")

tN = (int)(datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S').timestamp())
print (end_date,"End date is", tN, "day:",day_time(tN), time2str(tN))


print(ini_date)
t0 = (int)(datetime.strptime(ini_date, '%Y-%m-%d %H:%M:%S').timestamp())
print (ini_date,"Init date is", t0, "day:",day_time(t0), time2str(t0))


ts=list(range(t0,tN,time_step))

def day_time0(ti):
    return day_time(ti)-day_time(t0)+1

def relT(ti):
    return (int)((ti-t0)/time_step)

days=list(range(day_time(t0),day_time(tN)+1))
print(days)

def getStrDatefrom(day_number):
    reference_date = datetime(1970, 1, 1)
    resulting_date = reference_date + timedelta(days=day_number)
    return resulting_date.strftime("%Y-%m-%d")

# GEMINI
genai.configure(api_key=os.environ['API_KEY'])
for model in genai.list_models():
    print(model.name)
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")



## LOAD DATA
processed_data_folder = winshell.shortcut(shortcut).path
print(os.listdir(processed_data_folder)) 

init_context= config.get('Configuration', 'init_context')
print(init_context)
question_format= config.get('Configuration', 'question_format')
print(question_format)

pre_act_format= config.get('Configuration', 'pre_act_format')
print(pre_act_format)

wait_time=30
max_retries = 6  # You can adjust this

for ux,user in enumerate(users):
    print(user)
    total=0
    user_context= config.get(user, 'context')
    prompt = init_context + user_context
    retries = 0
    while retries < max_retries:
        try:
            response = model.generate_content(prompt)
            break  # Exit the loop if successful
        except ResourceExhausted as ex:
            print(ex)
            print(f"Resource exhausted. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            retries += 1
    if retries == max_retries:
        print(f"Failed to get a response after {max_retries} retries.")
    print(response.text)


    for dx, day in enumerate(days):
         # Create a file for writing the conversation for this user
        with open(f"conversation_{user}_{day}.txt", "w", encoding="utf-8") as f:
            day_str = getStrDatefrom(day)
            print(day, users)
            df_total = pd.read_csv(
                processed_data_folder + "/DAY_" + str(day) + "/INTERVAL." + user + ".all.tsv",
                sep="\t",
                parse_dates=True,
                header=None,
                names=["activity", "xx", "yy", "ix", "zz", "d0", "dN"],
            )
            df_total['d0'] = pd.to_datetime(df_total['d0'])
            df_total['dN'] = pd.to_datetime(df_total['dN'])
            print(df_total)

            act=None
            prequestion=""
            for index, row in df_total.iterrows():
                print(f"Index: {index}")
                print(f"Activity: {row['activity']}")
                print(f"Start time: {row['d0']}")
                print(f"End time: {row['dN']}")

                
                if act:
                    prequestion0 = pre_act_format.replace("RRR0", room)
                    prequestion0 = prequestion0.replace("TTT0", str(t0))
                    prequestion0 = prequestion0.replace("TTT1", str(t1))
                    prequestion0 = prequestion0.replace("AAA0", act)
                else:
                    prequestion0=""
                    
                prequestion=prequestion+prequestion0
                print(prequestion)

                act = activity_name[row['activity']]
                room = activity_rooms[row['activity']]
                t0 = row['d0']
                t1 = row['dN']

                
                question = question_format.replace("RRR", room)
                question = question.replace("TTT", str(t0))
                question = question.replace("AAA", act)

                question = prequestion + question
                
                print("question:",question)

                retries = 0
                while retries < max_retries:
                    try:
                        response = model.generate_content(question)
                        break  # Exit the loop if successful
                    except ResourceExhausted:
                        print(f"Resource exhausted. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        retries += 1
                if retries == max_retries:
                    print(f"Failed to get a response after {max_retries} retries.")

                total = total + 1
            

                print(response.text)

                # Write the prompt and response to the file
                f.write(f"Prompt: {question}\n")
                f.write(f"Response: {response.text}\n")

                time.sleep(10)
                if total > 200:
                    sys.exit()
  # Terminación normal


