__author__ = 'Keanulaszlo'
"""
Josh King helped significantly with the POSTing process. If it weren't for him I wouldn't have finished this,
or even been able to.
"""
#TEST
import csv
import os  # StackOverflow told me to
from collections import deque  # StackOverflow told me to
import configparser
import urllib.request
import urllib.parse
import http.cookiejar
import datetime
import time
from datetime import date, timedelta as td

from bs4 import BeautifulSoup

# graphing magic aka rip me
from pandas import DataFrame
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import spline


# don't look at this
def get_last_row(csv_name):
    with open(csv_name, 'r') as f:
        return deque(csv.reader(f), 1)[0]


def save_fig():
    path = 'figs'
    filename = date.isoformat(date.today())

    fig = plt.gcf()

    fig.set_size_inches(24, 13.2)
    fig.savefig(os.path.join(path, filename), dpi=128)


def plotpoints(plot_change_only, df):
    if plot_change_only:
        for k in range(df.shape[1]):
            # someday i will write regex to do this
            source = df[df.columns[k]]
            y_array = [source[0]]  # processed source
            for g in range((df[df.columns[k]]).size - 1)[1:]:
                if source[g] == source[g - 1]:
                    y_array.append(np.NaN)
                else:
                    y_array.append(source[g])
            y_array.append(source[-1])

            ys = np.array(y_array).astype('double')
            ymask = np.isfinite(ys)
            plt.plot(df.index[ymask], ys[ymask], label=df.columns[k])
    else:
        for k in range(df.shape[1]):
            source = df[df.columns[k]]
            ys = np.array(source)
            plt.plot(df.index, ys, label=df.columns[k])


# pls no
def smooth_graph(csv_name):
    df = DataFrame.from_csv(csv_name, parse_dates=False)

    xs = np.array([])
    for j in range(len(df.index)):
        xs = np.append(xs, time.mktime((datetime.datetime.strptime(df.index[j], '%Y-%m-%d')).timetuple()))

    xnew = np.linspace(xs.min(), xs.max(), 300)

    for k in range(df.shape[1]):
        ys = np.array(df[df.columns[k]])
        mark_smooth = spline(xs, ys, xnew)
        plt.plot(xnew, mark_smooth, label=df.columns[k])

    plt.title('Grades')
    plt.xlabel('Date')
    plt.ylabel('Mark')

    plt.legend(loc='best', title='Period')

    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')

    plt.grid()

    save_fig()
    plt.show()


def raw_graph(csv_name):
    df = DataFrame.from_csv(csv_name)
    plotpoints(config['options'].getboolean('Plot_changes_only', fallback=False), df)

    plt.title('Grades')
    plt.xlabel('Date')
    plt.ylabel('Mark')

    plt.legend(loc='best', title='Period')

    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')

    plt.grid()

    save_fig()
    plt.show()

# pull config
config = configparser.ConfigParser()
config.read('config.ini')

# credentials
username = config['credentials'].get('user')
password = config['credentials'].get('pass')

# cookie nonsense
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# payload business
payload = {'UserName': username, 'Password': password, 'SchlCode': 2, 'page': ''}
post_data = urllib.parse.urlencode(payload)
binary_data = post_data.encode('UTF-8')

# req 1: to pull action cache
req = urllib.request.Request('https://myportal.smhs.org/Login.asp', binary_data)
resp = opener.open(req)

# req 2: to pull main menu
soupData = BeautifulSoup(resp)

for formdata in soupData.find_all('form'):
    lastURL = formdata.get('action')

req = urllib.request.Request('https://myportal.smhs.org/' + lastURL, binary_data)
resp = opener.open(req)

# req 3: to pull grades html
soupData = BeautifulSoup(resp)

for formdata in soupData.find_all('a'):
    if 'GradebookSummary.asp' in formdata.get('href'):
        lastURL = formdata.get('href')

req = urllib.request.Request('https://myportal.smhs.org/' + lastURL)
resp = opener.open(req)

# now the fun begins
# req 4: to pull values
soupData = BeautifulSoup(resp)

header = 'Date'
goal = '\n' + date.isoformat(date.today())
# tds[3] is Period, tds[5] is Grade
for tr in soupData.find_all('tr', {'class': ['NormalClickableRow', 'NormalClickableRowEven']}):
    tds = tr.find_all('td')
    goal += ',' + tds[5].text.strip()
    header += ',' + tds[3].text.strip()

with open('grades.csv', 'a', newline='') as grades:
    if os.stat('grades.csv').st_size == 0:
        grades.write(header)
        grades.write(goal)
    elif get_last_row('grades.csv')[0] != date.isoformat(date.today()):
        if get_last_row('grades.csv')[0] != date.isoformat(date.today() - td(days=1)):
            d1 = datetime.datetime.strptime(get_last_row('grades.csv')[0], '%Y-%m-%d').date()
            d2 = date.today()
            delta = d2 - d1

            for i in range(delta.days - 1):
                grades.write('\n' + date.isoformat(d1 + td(days=i + 1)))

            grades.write(goal)
        else:
            grades.write(goal)

if config['options'].getboolean('Smooth_graph', fallback=False):
    smooth_graph('grades.csv')
else:
    raw_graph('grades.csv')
