# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from bs4 import element
from urllib.request import urlopen
import statistics
import datetime
import re
import unicodedata
import argparse
import csv

mainUrl = "http://www.dream-pro.info/~lavalse/LR2IR/"

argParser = argparse.ArgumentParser(description='Date Arguments')
argParser.add_argument('--date', metavar='date', nargs=2, help = 'vote start date / end date')
argParser.add_argument('-teian', help = 'flag for printing suggestion date of the patterns', action='store_true')
args = argParser.parse_args()
teian = args.teian

#convert string "YYYY/MM/DD" to datetime.date(YYYY, MM, DD).
#avoiding strftime and strptime
def convertToDate(dateString):
    dateList = dateString.split("/")
    return datetime.date(int(dateList[0]), int(dateList[1]), int(dateList[2]))

if args.date is None or len(args.date)!=2:
    try:
        dateFile = open('DATE.txt','r')
        suggStart = convertToDate(dateFile.readline())
        voteEnd = convertToDate(dateFile.readline())
        dateFile.close()
    except:
        print("Failed to load the start/end date(DATE.txt)")
        exit()
else:
    suggStart = convertToDate(args.date[0])
    voteEnd = convertToDate(args.date[1])

blackList=set()

def makeBlackList():
    try:
        file = open('BLACKLIST.txt','r')
        while True:
            line = file.readline()
            if line == '':
                break
            blackList.add( str(int(line)) )
        file.close()
    except:
        print("Failed to read the Black List(BLACKLIST.txt)")




#check whether a comment has correct form
#return value :
#-1: No / 0: Nothing / 1~: Yes, with difficulty
def checkComment(comment):
    checkNo = re.compile("^\(20[0-9]{2}\/([1-9]|0[1-9]|1[12])\/([1-9]|[012][0-9]|3[01])\) *$")
    checkYes = re.compile("^\(20[0-9]{2}\/([1-9]|0[1-9]|1[12])\/([1-9]|[012][0-9]|3[01])\) ?★([1-9]|1[0-9]|2[0-5])(| .*)$")
    try:
        if checkNo.match(comment):
            commentDate = convertToDate(comment[1:comment.find(")")])
            if suggStart <= commentDate and commentDate <= voteEnd:
                return (commentDate, -1)
            else:
                print(comment)
                return (None, 0)
        elif checkYes.match(comment):
            commentDate = convertToDate(comment[1:comment.find(")")])
            if suggStart <= commentDate and commentDate <= voteEnd:
                difficulty = re.search("★(1[0-9]|2[0-5]|[1-9])", comment)
                return (commentDate, int(difficulty.group(1)))
            else:
                print(comment)
                return (None, 0)
        else:
            return (None, 0)
    except:
        print("Failed to check the comment: " + comment)
        return (None, 0)
#calculate the yes / no / median / history of one pattern
def getRate(aUrl):
    irUrl = mainUrl + aUrl
    i = 1
    yes = 0
    no = 0
    yesarr = []
    try:
        while True: #traveling pages
            pageSoup = BeautifulSoup(urlopen(irUrl+"&page="+str(i)), 'html.parser', from_encoding='cp932')
            pageTables = pageSoup.body.div.div.find_all('table')
            pageTable = pageTables[len(pageTables)-1].find_all('tr')
            # kinda dangerous part. check whether it's players' data table or not
            if len(pageTable[0].find_all('th'))!=17:
                break
            for j in range(1, len(pageTable),2):
                dataRow = pageTable[j]
                commentRow = pageTable[j+1]
                #check black list
                playerID = re.search('[0-9]+',dataRow.a['href']).group(0)
                if playerID in blackList:
                    continue
                #replace fullwidth(Em-size) characters with halfwidth characters
                comment = unicodedata.normalize("NFKC", commentRow.td.string or "")
                checkVal = checkComment(comment)
                if checkVal[1]==-1:
                    no = no+1
                elif checkVal[1]>0:
                    yes = yes+1
                    yesarr.append(checkVal)
            i = i+1

        med = -1
        if len(yesarr):
            yesarr = sorted(yesarr)
            temparr = []
            resarr = []
            for i in range(0, len(yesarr)):
                if i>0 and yesarr[i][0] > yesarr[i-1][0]:
                    med = statistics.median_high(temparr)
                    if len(resarr)==0 or med != resarr[-1][1]:
                        resarr.append( (yesarr[i-1][0], med))
                temparr.append(yesarr[i][1])
            med = statistics.median_high(temparr)
            if len(resarr)==0 or med != resarr[-1][1]:
                resarr.append( (yesarr[-1][0], med)) 
        return (yes, no, med, resarr)
    except:
        print("Failed to load the IR page: " + aUrl)
def makeSongList():
    try:
        retlist = []
        histlist = []
        lv50Url = mainUrl + 'search.cgi?mode=search&type=insane&exlevel=50&7keys=1'
        lv50Soup = BeautifulSoup(urlopen(lv50Url), 'html.parser', from_encoding='cp932')
        lv50Table = lv50Soup.body.div.div.table
        for lChild in lv50Table.children:
        # There could be some white-space NavigateStrings.
            if isinstance(lChild, element.Tag):
                lList = lChild.find_all('td')
                if len(lList):
                    res = getRate(lList[2].a['href'])
                    for i in range(0, len(res[3])):
                        if i:
                            histlist.append( (res[3][i][0], "★" + str(res[3][i-1][1]) + " → ★" + str(res[3][i][1]) + " " + lList[2].a.string ))
                        elif teian:
                            histlist.append( (res[3][i][0], "★" + str(res[3][i][1]) + " " + lList[2].a.string + " 提案" ))
                    retlist.append( [res[2], lList[2].a.string, res[0], res[1]] )
        histlist = sorted(histlist)
        retlist = sorted(retlist)
        return (retlist, histlist)
    except:
        print("Failed to load the ★50 Table")
        return ([], [])

if __name__ == "__main__":
    makeBlackList()
    songList = makeSongList()
    try:
        output = open('status.csv','w', encoding='utf-8-sig', newline='')
        outputWriter = csv.writer(output)
        outputWriter.writerow(["Median", "Name", "Yes", "No"])
        for it in songList[0]:
            outputWriter.writerow(it)
        output.close()
    except:
        print("Failed to write the status file")
    try:
        output = open('history.csv', 'w', encoding='utf-8-sig', newline='')
        outputWriter = csv.writer(output)
        for i in range(0, len( songList[1] )):
            if i==0 or songList[1][i-1][0] != songList[1][i][0]:
                outputWriter.writerow( [songList[1][i][0].strftime("%Y/%m/%d"), songList[1][i][1]] )
            else:
                outputWriter.writerow( ["", songList[1][i][1]] )
        output.close()
    except:
        print("Failed to write the history file")
