import datetime
import json
import smtplib
import sys
import time
import uuid
import plivo
import os
import firebase_admin
from passlib.hash import pbkdf2_sha256
from firebase_admin import credentials
from firebase_admin import db
from flask import Blueprint, render_template, abort
from google.cloud import storage
import pytz
from flask import Flask, flash, request, session, jsonify
from werkzeug.utils import secure_filename
from flask import redirect, url_for
from flask import render_template
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
# import Cedar
from Cedar.admin import admin_panel, menu, pw_reset
from Cedar.main_page import find_page

infoFile = open("info.json")
info = json.load(infoFile)
botNumber = info["number"]
mainLink = info['mainLink']
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ', auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})
storage_client = storage.Client.from_service_account_json('CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket("cedarchatbot.appspot.com")
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
smtpObj.login(sender, emailPass)

dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}

app = Flask(__name__)
app.register_blueprint(admin_panel.admin_panel_blueprint)
app.register_blueprint(find_page.find_page_blueprint)
app.register_blueprint(menu.menu_panel_blueprint)
app.register_blueprint(pw_reset.pw_reset_blueprint)
sslify = SSLify(app)
scKey = uuid.uuid4()
app.secret_key = scKey


locationsPaths = {}
tzGl = []


# Call the success method to see if the call succeeded
##########Restaurant END END###########


def checkLocation(estNameStr, location):
    try:
        ref = db.reference('/restaurants/'+estNameStr+'/'+location)
        test = dict(ref.get())
        if(test != None):
            return 0
        else:
            return 1
    except Exception as e:
        return 1



def sendCheckmate(estNameStr,location,token):
    print('order sent to checkmate')



@app.route('/<estNameStr>/<location>/schedule-<day>', methods=["GET"])
def scheduleSet(estNameStr,location,day):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    if (checkAdminToken(idToken, username) == 1):
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    user_ref = ref.child(str(username))
    user_ref.update({
        'time': time.time()
    })
    sched_ref = db.reference('/restaurants/' + estNameStr + '/'+location+"/schedule")
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/menu')
    menu_keys = list((menu_ref.get()).keys())
    menu_data = menu_ref.get()
    menuTotals = []
    for keys in menu_keys:
        if(menu_data[keys]["active"] == True):
            menuTotals.append(keys)
    currentSchedule = dict(sched_ref.get()[day])
    schedList = list(currentSchedule.keys())
    timeDict = {"Start-of-Day":'0:00'}
    timeContainers = []
    menus = ["Start-of-Day"]
    menuTimes = [0.0]
    menuTimesStr = ['0:00']
    for s in schedList:
        timeContainers.append(currentSchedule[s])
    timeContainers.sort()
    for tc in range(len(timeContainers)):
        for schedKeys in schedList:
            if(timeContainers[tc] == currentSchedule[schedKeys]):
                sch = str(schedKeys).replace(" ","-")
                menus.append(sch)
                timeStr = "{:.2f}".format(currentSchedule[schedKeys])
                timeStr = str(timeStr).replace(".",":")
                menuTimes.append(currentSchedule[schedKeys])
                menuTimesStr.append(timeStr)
                timeDict.update({sch:timeStr})
    menus.append("End-of-Day")
    menuTimes.append(23.59)
    menuTimesStr.append("23:59")
    timeDict.update({"End-of-Day":"23:59"})
    return(render_template("POS/AdminMini/listSchedule.html",day=day,menuTotals=menuTotals,timeDict=timeDict,menuTimes=menuTimes,menus=menus,menuTimesStr=menuTimesStr))

@app.route('/<estNameStr>/<location>/remTs~<day>~<menu>')
def remTimeSlot(estNameStr,location,day,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    menu = str(menu).replace("-"," ")
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+str(menu))
    menu_ref.delete()
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<estNameStr>/<location>/schedMenu~<day>~<menu>~<timeVal>', methods=["POST"])
def editTimeSlot(estNameStr,location,day,menu,timeVal):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    new_menu = str(rsp["menu"])
    del_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day)+"/"+menu)
    del_ref.delete()
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({new_menu:float(timeVal)})
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<estNameStr>/<location>/editMenuTime~<day>~<menu>', methods=["POST"])
def editMenuSlot(estNameStr,location,day,menu):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("scheduleSet",estNameStr=estNameStr,location=location,day=day)))

@app.route('/<estNameStr>/<location>/addTs~<day>', methods=["POST"])
def addTimeSlot(estNameStr,location,day):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    hour = float(rsp["hour"])
    minute = (float(rsp["minute"])/100)
    menu = str(rsp["menu"])
    newTime = hour+minute
    menu_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/schedule/'+str(day))
    menu_ref.update({menu:newTime})
    return(redirect(url_for("scheduleSet",location=location,day=day)))

@app.route('/<estNameStr>/<location>/rem-new-comment~<comment>')
def remNewComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/rem-saved-comment~<comment>')
def remSavedComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved/'+str(comment))
        item_ref.delete()
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/save-comment~<comment>')
def saveComment(estNameStr,location,comment):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        commRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/new/'+str(comment))
        commentData = dict(commRef.get())
        commRef.delete()
        savedRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/comments/saved')
        savedRef.update({
            comment:commentData
        })
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/rem-feedback~<question>')
def remQuestion(estNameStr,location,question):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        item_ref = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback/'+str(question))
        item_ref.delete()
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/add-feedback')
def addQuestion(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))
        return(render_template("POS/AdminMini/addFeedback.html",estNameStr=estNameStr,location=location))

@app.route('/<estNameStr>/<location>/add-feedback-confirm', methods=['POST'])
def addQuestionConfirm(estNameStr,location):
    idToken = session.get('token', None)
    username = session.get('user', None)
    ref = db.reference('/restaurants/' + estNameStr + '/admin-info')
    try:
        user_ref = ref.get()[str(username)]
    except Exception:
        return redirect(url_for('.login',estNameStr=estNameStr,location=location))
    finally:
        if (checkAdminToken(idToken, username) == 1):
            return redirect(url_for('.login',estNameStr=estNameStr,location=location))

        request.parameter_storage_class = ImmutableOrderedMultiDict
        rsp = dict((request.form))
        print(rsp)
        qName = rsp['q-name']
        qId = str(uuid.uuid4()).replace("-","")
        qDict = {qId:
            {'ans':{},
             'info':{
                 "name":qName,
                 "maxScore":int(rsp['max']),
                 "day":{
                     "currday":int(datetime.datetime.now().weekday()),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "week":{
                     "currweek":int(datetime.datetime.now().isocalendar()[1]),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 },
                 "month":{
                     "currmonth":int(datetime.datetime.now().month),
                     "count":0,
                     "currentScore":0.0,
                     "totalScore":0
                 }
             }
             }}
        del rsp['q-name']
        del rsp['max']
        for k in range(0,int(len(rsp)/2)):
            nameKey = 'name-' + str(k+1)
            scoreKey = 'prce-' + str(k+1)
            print(rsp[nameKey])
            ansKey = str(uuid.uuid4()).replace("-","")
            ansDict = {ansKey:{
                "name":rsp[nameKey],
                "score":int(rsp[scoreKey])
            }}
            qDict[qId]['ans'].update(ansDict)

        qRef = db.reference('/restaurants/' + estNameStr + '/' +location+ '/feedback')
        qRef.update(qDict)
        return(redirect(url_for("panel",estNameStr=estNameStr,location=location)))

##########CUSTOMER END###########


###Kiosk###

def findMenu(estNameStr,location):
    getSquare(estNameStr)
    day = dayNames[int(datetime.datetime.now(tzGl[location]).weekday())]
    curMin = float(datetime.datetime.now(tzGl[location]).minute) / 100.0
    curHr = float(datetime.datetime.now(tzGl[location]).hour)
    curTime = curHr + curMin
    pathTime = '/restaurants/' + estNameStr + '/' + location + "/schedule/" + day

    schedule = db.reference(pathTime).get()
    schedlist = list(schedule)
    start = 24
    sortedHr = [0]
    for scheds in schedlist:
        sortedHr.append(schedule[scheds])

    sortedHr.sort()
    sortedHr.append(24)
    for sh in range(len(sortedHr) - 1):
        if((sortedHr[sh]< curTime < sortedHr[sh+1])== True):
            menuKey = sh
            break

    for sh2 in range(len(schedlist)):
        if(sortedHr[menuKey] == schedule[schedlist[sh2]]):
            menu = (schedlist[sh2])
            return(str(menu))


@app.route('/<estNameStr>/<location>/sitdown-startKiosk', methods=["GET"])
def startKiosk2(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("Customer/Sitdown/startKiosk.html",btn="sitdown-startKiosk",restName=estNameStr,locName=location))

@app.route('/<estNameStr>/<location>/qsr-startKiosk', methods=["GET"])
def startKiosk4(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("Customer/QSR/startKiosk.html",btn="qsr-startKiosk",restName=estNameStr,locName=location))

@app.route('/<estNameStr>/<location>/order', methods=["GET"])
def startKiosk5(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("Customer/QSR/startKiosk.html",btn="startOnline",restName=estNameStr,locName=location))

@app.route('/<estNameStr>/<location>/startOnline', methods=["POST"])
def startOnline(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    table = "Online Order"
    session['table'] = ""
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":1,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(estNameStr,location)
    print(menu)
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))



@app.route('/<estNameStr>/<location>/qsr-startKiosk', methods=["POST"])
def startKioskQsr(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    togo = rsp["togo"]
    print(togo)
    if(togo == "here"):
        table = "Table #" + rsp["table"]
        print(table)
    else:
        table = "To Go"
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "togo":togo,
        "QSR":0,
        "cpn":1,
        "kiosk":0,
        "name":name,
        "phone":phone,
        "table":table,
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(estNameStr,location)
    # menu = "lunch"
    session["menu"] = menu
    ##print(menu)
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/sitdown-startKiosk', methods=["POST"])
def startKiosk(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    phone = rsp["number"]
    name = rsp["name"]
    table = rsp["table"]
    session['table'] = table
    session['name'] = name
    session['phone'] = phone
    path = '/restaurants/' + estNameStr + '/' + location + "/orders/"
    orderToken = str(uuid.uuid4())
    ref = db.reference(path)
    newOrd = ref.push({
        "QSR":1,
        "kiosk":0,
        "cpn":1,
        "name":name,
        "phone":phone,
        "table":table,
        "paid":"Not Paid",
        "alert":"null",
        "alertTime":0,
        "timestamp":time.time(),
        "subtotal":0.0
        })
    #print(newOrd.key)
    session['orderToken'] = newOrd.key
    menu = findMenu(estNameStr,location)
    session["menu"] = menu
    return(redirect(url_for('sitdownMenu',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/testmenu')
def dummyMenuRender(estNameStr,location):
    menu = "breakfast"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cart = {}
    return(render_template("Customer/QSR/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), locName=location.capitalize(), cart=cart ))


@app.route('/<estNameStr>/<location>/sitdown-menudisp')
def sitdownMenu(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    # print(cart)
    return(render_template("Customer/Sitdown/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), cart=cart, locName=location.capitalize()))

@app.route('/<estNameStr>/<location>/qsr-menudisp')
def qsrMenu(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    cartRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart")
    try:
        cart = dict(cartRef.get())
    except Exception as e:
        cart = {}
    # print(cart)
    return(render_template("Customer/QSR/mainKiosk2.html", menu=menuInfo, restName=estNameStr.capitalize(), cart=cart, locName=location.capitalize()))

@app.route('/<estNameStr>/<location>/qsr-additms~<cat>~<itm>', methods=["POST"])
def kiosk2QSR(estNameStr,location,cat,itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    ##print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = int(qty_str)
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                dispStr += str(raw_arr[0]).capitalize() + " "
                mods.append([raw_arr[0],raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    dispStr += "  |Notes: " +notes + "  (" + "${:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    ##print(orderToken)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat':cat,
        'itm':itm,
        'qty':qty,
        'img':img,
        'notes':notes,
        'price':price,
        'mods':mods,
        'unitPrice':unitPrice,
        'dispStr':dispStr
    })
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/sitdown-additms~<cat>~<itm>', methods=["POST"])
def kiosk2(estNameStr,location, cat, itm):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    ##print((request.form))
    rsp = dict((request.form))
    dispStr = ""
    unitPrice = 0
    notes = rsp['notes']
    qty_str = rsp['qty']
    if(qty_str == ""):
        qty = 1
    else:
        qty = int(qty_str)
    dispStr += str(qty) + " x " + itm + " "
    dict_keys = list(rsp.keys())
    mods = []
    img = ""
    for keys in dict_keys:
        if(keys != "notes" or keys != "qty"):
            try:
                raw_arr = rsp[keys].split("~")
                img = raw_arr[2]
                dispStr += str(raw_arr[0]).capitalize() + " "
                mods.append([raw_arr[0],raw_arr[1]])
                unitPrice += float(raw_arr[1])
            except Exception as e:
                pass
    price = float(qty*unitPrice)
    dispStr += "  |Notes: " +notes + "  ($" + "{:0,.2f}".format(price) + ")"
    menu = session.get('menu', None)
    orderToken = session.get('orderToken',None)
    ##print(orderToken)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    cartRefItm = db.reference(pathCartitm)
    cartRefItm.push({
        'cat':cat,
        'itm':itm,
        'qty':qty,
        'img':img,
        'notes':notes,
        'price':price,
        'dispStr':dispStr,
        'mods':mods,
        'unitPrice':unitPrice
    })
    return(redirect(url_for('sitdownMenu',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/qsr-itmRemove', methods=["POST"])
def kioskRemQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    cartRefItm = db.reference(pathCartitm)
    menuInfo = db.reference(pathMenu).get()
    cartData = db.reference(pathCartitm).get()
    return(redirect(url_for('qsrMenu',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/itmRemove', methods=["POST"])
def kioskRem(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    remItm = rsp["remove"]
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    remPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/" + remItm
    try:
        remRef = db.reference(remPath)
        remRef.delete()
    except Exception as e:
        pass
    finally:
        cartRefItm = db.reference(pathCartitm)
        menuInfo = db.reference(pathMenu).get()
        cartData = db.reference(pathCartitm).get()
    return(redirect(url_for('sitdownMenu',estNameStr=estNameStr,location=location)))





@app.route('/<estNameStr>/<location>/SDupdate')
def kioskUpdate(estNameStr,location):
    try:
        orderToken = session.get('orderToken',None)
        setPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        alertTimePath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/alertTime"
        alertPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/alert"
        alert = db.reference(alertPath).get()
        info = {
               "alert" : alert,
            }
        return jsonify(info)
    except Exception as e:
        return("200")


@app.route('/<estNameStr>/<location>/cartAdd', methods=["POST"])
def kioskCart(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    tableNum = db.reference(pathTable).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        reqRef = db.reference(pathRequest)
        newReq = reqRef.push(cart)
        pathRequestkey = '/restaurants/' + estNameStr + '/' + location + "/requests/" + newReq.key + "/info"
        reqRefkey = db.reference(pathRequestkey)
        reqRefkey.update({"table":tableNum,"type":"order","token":orderToken})
        cartRef.delete()
    except Exception:
        pass
    menuInfo = db.reference(pathMenu).get()
    cart = {}

    return(redirect(url_for('sitdownMenu',estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/cartAdd-QSR', methods=["POST"])
def kioskCartQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathCart = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/cart/"
    pathTable = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/table/"
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    tableNum = db.reference(pathTable).get()
    menuInfo = db.reference(pathMenu).get()
    try:
        cartRef = db.reference(pathCart)
        cart = db.reference(pathCart).get()
        test = str(list(cart.keys()))
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        cpnBool = orderInfo["cpn"]
        if(cpnBool == 0):
            cart = dict(orderInfo["cart"])
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                if("discount" == str(cart[keys]["cat"])):
                    pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/" + keys
                    pathRemRef = db.reference(pathRem)
                    pathRemRef.delete()
        return(render_template("Customer/QSR/receipt.html"))
        # return(redirect(url_for("payQSR",estNameStr=estNameStr,location=location)))
    except Exception:
        return(redirect(url_for("qsrMenu",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/recipt-qsr', methods=["POST"])
def reciptQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    orderToken = session.get('orderToken',None)
    if(rsp['email'] != ""):
        userRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email":rsp['email']
        })
    else:
        userRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email":"no-email"
        })
    return(redirect(url_for("payQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/collect-feedback')
def dispFeedBack(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    feedback_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback')
    feedback = dict(feedback_ref.get())
    return(render_template("Customer/Sitdown/feedback.html",feedback=feedback))


@app.route('/<estNameStr>/<location>/collect-feedback-ans', methods=['POST'])
def collectFeedback(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    if(rsp['email'] != ""):
        userRef = db.reference(pathOrder)
        userRef.update({
            "email":rsp['email']
        })
    else:
        userRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        userRef.update({
            "email":"no-email"
        })
    orderInfo = dict(db.reference(pathOrder).get())
    now = datetime.datetime.now(tzGl[location])
    feedback_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback')
    curr_feedback = dict(feedback_ref.get())
    comment_ref = db.reference('/restaurants/' + estNameStr + '/'+ location + '/comments/new')
    comments = str(rsp['comment']) + " "
    comment_ref.push({
        "comment":comments,
        "name":orderInfo['name'],
        "timeStamp":str(now.hour) + ":" + str(now.minute) + " " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
    })
    del rsp['comment']
    newFeedKeys = list(rsp.keys())
    feedKeys = list(curr_feedback.keys())
    timeScale = ['day','week','month']
    timeScaleVal = [int(datetime.datetime.now(tzGl[location]).weekday()),int(datetime.datetime.now(tzGl[location]).isocalendar()[1]),int(datetime.datetime.now(tzGl[location]).month)]
    for tms in range(len(timeScale)):
        for keys in feedKeys:
            currScore = curr_feedback[keys]['info'][timeScale[tms]]['totalScore']
            ansSize = curr_feedback[keys]['info'][timeScale[tms]]['count']
            addScore = curr_feedback[keys]['ans'][rsp[keys]]['score']
            timeKey = "curr" + str(timeScale[tms])
            timeVal = curr_feedback[keys]['info'][timeScale[tms]][timeKey]

            currScore += addScore
            ansSize += 1
            newDispScore = round(float(currScore)/float(ansSize),2)
            qFeedbackRef = db.reference('/restaurants/' + estNameStr + '/'+ location + '/feedback/' + keys + '/info/' + str(timeScale[tms]))
            if(timeVal == timeScaleVal[tms]):
                qFeedbackRef.update({
                    'count':ansSize,
                    'currentScore': newDispScore,
                    'totalScore':currScore
                })
            else:
                qFeedbackRef.update({
                    timeKey:timeScaleVal[tms],
                    'count':1,
                    'currentScore': addScore,
                    'totalScore':addScore
                })
    return(redirect(url_for("payQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/pay')
def payQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    if(QSR == 0):
        cart = dict(orderInfo["cart"])
        subtotal = 0
        items = []
        cartKeys = list(cart.keys())
        for keys in cartKeys:
            subtotal += cart[keys]["price"]
            dispStr = cart[keys]["dispStr"]
            items.append(dispStr)
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        session['total'] = round(subtotal*(1+taxRate),2)
        session['subtotal'] = subtotal
        session['kiosk'] = orderInfo["kiosk"]
        db.reference(pathOrder).update({
            "subtotal":subtotal,
            "total":float(subtotal*(1+taxRate))
        })
        sqTotal = str(int(round(subtotal*(1+taxRate),2) * 100)) + "~" + str(orderToken) +"~"+mainLink+location
        if(orderInfo['kiosk'] == 0):
            return(render_template("Customer/QSR/Payment.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(), cart=str(cart), items=items, subtotal=subtotalStr,tax=tax,total=total,sqTotal=sqTotal))
        else:
            return(render_template("Customer/QSR/Payment-Online.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(), cart=str(cart), items=items, subtotal=subtotalStr,tax=tax,total=total,orderToken=orderToken))
    else:
        cart = dict(orderInfo["ticket"])
        subtotal = orderInfo["subtotal"]
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        cartKeys = list(cart.keys())
        cpnBool = orderInfo["cpn"]
        pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
        items = []
        for ck in cartKeys:
            ckKeys = list(cart[ck].keys())
            for ckk in ckKeys:
                dispStr = cart[ck][ckk]["itm"]
                dispStr += " "
                for mds in range(len(cart[ck][ckk]["mods"])):
                    dispStr += cart[ck][ckk]["mods"][mds][0]
                dispStr += " "
                dispStr += str("$" + "{:0,.2f}".format(float(cart[ck][ckk]["unitPrice"])))
                dispStr += " x "
                dispStr += str(cart[ck][ckk]["qty"])
                dispStr += " " + str(cart[ck][ckk]["notes"])
                dispStr += " || $"
                dispStr += "{:0,.2f}".format(float(cart[ck][ckk]["price"]))
                items.append(dispStr)
                session['total'] = round(subtotal*(1+taxRate),2)
                session['kiosk'] = orderInfo["kiosk"]
        sqTotal = str(int(round(subtotal*(1+taxRate),2) * 100)) + "~" + str(orderToken)+"~"+mainLink+location
        return(render_template("Customer/Sitdown/Payment.html",locName=location.capitalize(),restName=str(estNameStr).capitalize(),
                               items=items, subtotal=subtotalStr,tax=tax,total=total, sqTotal=sqTotal))

@app.route('/<estNameStr>/<location>/payStaff')
def payStaff(estNameStr,location):
    menu = session.get('menu',None)
    orderToken = session.get('orderToken',None)
    tableNum = session.get('table',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    reqRef = db.reference(pathRequest)
    newReq = reqRef.push({"help":'Payment Assitance'})
    pathRequestkey = '/restaurants/' + estNameStr + '/' + location + "/requests/" + newReq.key + "/info"
    reqRefkey = db.reference(pathRequestkey)
    reqRefkey.set({"table":tableNum,"type":"help","token":orderToken})
    return(render_template('Customer/Sitdown/NoCCpay.html', alert='Staff Will Enter Code To Confirm Payment'))

@app.route('/<estNameStr>/<location>/payStaffConfirm', methods=['POST'])
def payStaffConfirm(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = session.get('orderToken',None)
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderRef = db.reference(pathOrder)
        orderRef.update({
            "paid":"PAID"
        })
        if(order['email'] != "no-email"):
            now = datetime.datetime.now(tzGl[location])
            write_str = "Your Meal From "+ estNameStr + " " + location + " @"
            write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
            write_str += "\n \n"
            # TODOX
            cart = dict(order["ticket"])
            subtotal = order["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
            tax = "${:0,.2f}".format(subtotal * taxRate)
            tax += " (" + str(float(taxRate * 100)) + "%)"
            total = "${:0,.2f}".format(subtotal * (1+taxRate))
            cartKeys = list(cart.keys())
            for ck in cartKeys:
                ckKeys = list(cart[ck].keys())
                for ckk in ckKeys:
                    dispStr = cart[ck][ckk]["dispStr"] +  "\n"
                    write_str += dispStr
            write_str+= "\n \n"
            write_str += subtotalStr + "\n" + tax + "\n" + total + "\n \n \n"
            write_str += 'Thank You For Dining with us ' + str(order['name']).capitalize() + " !"
            SUBJECT = "Thank You For Dining at "+ estNameStr + " " + location
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            # smtpObj.sendmail(sender, [order['email']], message)
            sendEmail(sender, order['email'], message)
        orderRef.delete()
        return(redirect(url_for('startKiosk4',estNameStr=estNameStr, location=location)))
    else:
        return(render_template('Customer/Sitdown/NoCCpay.html', alert='Incorrect Code please try again'))


@app.route('/<estNameStr>/<location>/qsr-payStaff')
def payStaffQSR(estNameStr,location):
    orderToken = session.get('orderToken',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
    qsrOrderRef = db.reference(qsrOrderPath)
    qsrOrderRef.update({
        token:{
            "cart":dict(order['cart']),
            "info":{"name":order["name"],
                    "number":order['phone'],
                    "paid":"NOT PAID",
                    "subtotal":order['subtotal'],
                    "total":order['total'],
                    'table':order['table'],
                    'verify':1}
            }
    })
    return(render_template('Customer/QSR/NoCCpay.html'))


@app.route('/<estNameStr>/<location>/pay-online')
def payOnline(estNameStr,location):
    orderToken = session.get('orderToken',None)
    subtotal = session.get('subtotal',None)
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    squareToken = dict(sqRef.get())["sq-token"]
    client = Client(
        access_token=squareToken,
        environment='production',
    )
    api_locations = client.locations
    mobile_authorization_api = client.mobile_authorization
    # Call list_locations method to get all locations in this Square account
    result = api_locations.list_locations()
    if result.is_success():
    	# The body property is a list of locations
        locations = result.body['locations']
    	# Iterate over the list
        for locationX in locations:
            # print(location)
            if((dict(locationX.items())["status"]) == "ACTIVE"):
                locationName = (dict(locationX.items())["name"]).replace(" ","-")
                locationId = dict(locationX.items())["id"]
                if(str(location).lower() == str(locationName).lower() ):

                    body = {}
                    body['location_id'] = locationId
                    checkout_api = client.checkout
                    body = {}
                    idX = str(uuid.uuid4())
                    body['idempotency_key'] = idX
                    body['order'] = {}
                    body['order']['reference_id'] = idX
                    body['order']['line_items'] = []

                    body['order']['line_items'].append({})

                    cart = dict(orderInfo["cart"])
                    subtotal = 0
                    items = []
                    cartKeys = list(cart.keys())
                    for keys in range(len(cartKeys)):
                        dispStr = str(cart[cartKeys[keys]]["dispStr"]).split('x')
                        disp2 = list(dispStr[1].split('('))
                        print(disp2)
                        dispX = disp2[0]
                        body['order']['line_items'][keys]['name'] = dispX
                        body['order']['line_items'][keys]['quantity'] = str(cart[cartKeys[keys]]["qty"])
                        body['order']['line_items'][keys]['base_price_money'] = {}
                        body['order']['line_items'][keys]['base_price_money']['amount'] = int((cart[cartKeys[keys]]["unitPrice"])*100)
                        body['order']['line_items'][keys]['base_price_money']['currency'] = "USD"

                    body['order']['line_items'].append({})
                    body['order']['line_items'][len(cartKeys)]['name'] = 'Order Fee'
                    body['order']['line_items'][len(cartKeys)]['quantity'] = '1'
                    body['order']['line_items'][len(cartKeys)]['base_price_money'] = {}
                    body['order']['line_items'][len(cartKeys)]['base_price_money']['amount'] = 25
                    body['order']['line_items'][len(cartKeys)]['base_price_money']['currency'] = "USD"

                    body['order']['taxes'] = []
                    body['order']['taxes'].append({})
                    body['order']['taxes'][0]['name'] = 'Sales Tax'
                    taxRef = db.reference(str('/restaurants/' + estNameStr + '/' + location))
                    taxDict =(dict(taxRef.get())["taxrate"])
                    print(taxDict)
                    tax = str((taxDict * 100))
                    body['order']['taxes'][0]['percentage'] = tax

                    body['ask_for_shipping_address'] = False
                    body['redirect_url'] = mainLink + estNameStr + '/' + location +'/online-confirm~'+orderToken

                    result = checkout_api.create_checkout(locationId , body)

                    if result.is_success():
                        link = str(result.body["checkout"]["checkout_page_url"])
                        print(link)
                        # print(result.body["checkout"])
                        return redirect(link)
                    elif result.is_error():
                        print(result.errors)
                        return(redirect(url_for('payQSR',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/online-confirm~<orderToken>')
def onlineVerify(estNameStr,location,orderToken):
    orderTokenCheck = session.get('orderToken',None)
    if(orderToken == orderTokenCheck):
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderRef = db.reference(pathOrder)
        order = dict(orderRef.get())
        if(order['QSR'] == 0):
            qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
            qsrOrderRef = db.reference(qsrOrderPath)
            qsrOrderRef.update({
                orderToken:{
                    "cart":dict(order['cart']),
                    "info":{"name":order["name"],
                            "number":order['phone'],
                            "paid":"PAID",
                            "subtotal":float(order['subtotal']+0.25),
                            "total":order['total'],
                            'table':order['table']}
                    }
            })
            if(order['email'] != "no-email"):
                getSquare(estNameStr)
                now = datetime.datetime.now(tzGl[location])
                write_str = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize() + " @"
                write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
                write_str += "\n \n"
                cart = dict(order["cart"])
                subtotal = 0
                items = []
                cartKeys = list(cart.keys())
                for keys in cartKeys:
                    subtotal += cart[keys]["price"]
                    dispStr = cart[keys]["dispStr"]
                    write_str += dispStr + "\n"
                subtotal += 0.25
                subtotalStr = "Subtotal ${:0,.2f}".format(subtotal)
                taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
                tax = "Tax ${:0,.2f}".format(subtotal * taxRate)
                tax += " (" + str(float(taxRate * 100)) + "%)"
                total = "Total ${:0,.2f}".format(subtotal * (1+taxRate))
                write_str+= "\n \n"
                write_str += subtotalStr +"\n"+tax + "\n"+ total +"\n \n \n"
                write_str += 'Thank You For Your Order ' + str(order['name']).capitalize() + " !"
                SUBJECT = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize()
                message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
                sendEmail(sender, order['email'], mesg)
        return(render_template("Customer/QSR/Payment-Success.html"))
    else:
        return(redirect(url_for('startOnline',estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/applyCpn', methods=["POST"])
def applyCpn(estNameStr,location):
    orderToken = session.get('orderToken',None)
    menu = session.get('menu',None)
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = dict((request.form))
    code = str(rsp["code"]).lower()
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    orderInfo = dict(db.reference(pathOrder).get())
    QSR = orderInfo["QSR"]
    try:
        cpnsPath = '/restaurants/' + estNameStr + '/' + location + "/discounts/"+ menu
        cpns = dict(db.reference(cpnsPath).get())
        disc = cpns[code]
        discCat = disc["cat"]
        discItm = disc["itm"]
        lim = disc["lim"]
        min = disc["min"]
        type = disc["type"]
        amt = float(disc["amt"])
        modName = disc["mods"][0]
        modItm = disc["mods"][1]
        QSR = int(orderInfo["QSR"])
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        orderInfo = dict(db.reference(pathOrder).get())
        varQSR = (QSR == 0)
        if(varQSR == True):
            cpnBool = orderInfo["cpn"]
            if(cpnBool == 0):
                cart = dict(orderInfo["cart"])
                cartKeys = list(cart.keys())
                for keys in cartKeys:
                    if("discount" == str(cart[keys]["cat"])):
                        pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/" + keys
                        pathRemRef = db.reference(pathRem)
                        pathRemRef.delete()
            cart = dict(orderInfo["cart"])
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                if(discCat == str(cart[keys]["cat"]) and discItm == str(cart[keys]["itm"])):
                    # TODO
                    for mod in range(len(cart[keys]["mods"])):
                        md = cart[keys]["mods"][mod][0]
                        print(md, modItm)
                        if(modItm == md):
                            for q in range(int(cart[keys]["qty"])):
                                if(amtUsed < lim):
                                    if(type == "money"):
                                        discAmt -= amt
                                    else:
                                        discAmt -= (cart[keys]["unitPrice"]*float(amt/100))
                                    amtUsed += 1
                                else:
                                    break
            print(amtUsed, min, discAmt)
            if(amtUsed >= min):
                #print("discApplied")
                pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/cart/"
                cartRefItm = db.reference(pathCartitm)
                cartRefItm.push({
                    'cat':'discount',
                    'itm':code,
                    'qty':int(amtUsed),
                    'img':'',
                    'notes':'',
                    'price':discAmt,
                    'dispStr': str(str(amtUsed) + " x " + str(code) + " $" + "{:0,.2f}".format(discAmt)),
                    'mods':[["-",0]],
                    'unitPrice':float(float(discAmt)/float(amtUsed))
                })
                pathCpn.update({"cpn":0})
            return(redirect(url_for('payQSR',estNameStr=estNameStr,location=location)))
        else:
            cart = dict(orderInfo["ticket"])
            subtotal = orderInfo["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            tax = "${:0,.2f}".format(subtotal *0.1)
            total = "${:0,.2f}".format(subtotal *1.1)
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            cpnBool = orderInfo["cpn"]
            print(cpnBool)
            if(cpnBool == 0):
                for ck in cartKeys:
                    ckKeys = list(cart[ck].keys())
                    for ckk in ckKeys:
                        if(cart[ck][ckk]["cat"] == "discount"):
                            pathRem = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket/" + str(ck) + "/" + str(ckk)
                            pathRemRef = db.reference(pathRem)
                            subtotal -= cart[ck][ckk]['price']
                            pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                            pathCpn.update({"subtotal":subtotal})
                            pathRemRef.delete()
            pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
            orderInfo = dict(db.reference(pathOrder).get())
            cart = dict(orderInfo["ticket"])
            subtotal = orderInfo["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            tax = "${:0,.2f}".format(subtotal *0.1)
            total = "${:0,.2f}".format(subtotal *1.1)
            amtUsed = 0
            discAmt = 0
            cartKeys = list(cart.keys())
            for ckx in cartKeys:
                ckxKeys = list(cart[ckx].keys())
                for ckkx in ckxKeys:
                    if((discCat == str(cart[ckx][ckkx]["cat"])) and (discItm == str(cart[ckx][ckkx]["itm"]))):
                        for mod in range(len(cart[ckx][ckkx]["mods"])):
                            md = cart[ckx][ckkx]["mods"][mod][0]
                            if(modItm == md):
                                for q in range(int(cart[ckx][ckkx]["qty"])):
                                    if(amtUsed < lim):
                                        if(type == "money"):
                                            discAmt -= amt
                                        else:
                                            discAmt -= (cart[ckx][ckkx]["unitPrice"]*float(amt/100))
                                        amtUsed += 1

                                    else:
                                        break
            if(amtUsed >= min):
                #print("discApplied")
                subtotal += discAmt
                pathCpn =  db.reference('/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken)
                pathCartitm = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket/"
                cartRefItm = db.reference(pathCartitm)
                postToken = str(uuid.uuid4()).replace("-","a")
                cartRefItm.push({
                    postToken:{
                    'cat':'discount',
                    'itm':code,
                    'qty':int(amtUsed),
                    'img':'',
                    'notes':'',
                    'price':discAmt,
                    'mods':[[" ",0]],
                    'unitPrice':float(float(discAmt)/float(amtUsed))
                    }
                })
                pathCpn.update({"cpn":0,
                                "subtotal":subtotal})
            return(redirect(url_for('payQSR',estNameStr=estNameStr,location=location)))
    except Exception as e:
        print(str(e))
        return(redirect(url_for('payQSR',estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/close-alert')
def kioskClear(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    orderToken = session.get('orderToken',None)
    alertPath = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    clearAlert = db.reference(alertPath).update({"alert":"null"})
    return(redirect(url_for("sitdownMenu",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/sendReq', methods=["POST"])
def kioskSendReq(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    rspKey = list(rsp.keys())[0]
    if(rspKey == "condiments"):
        requestId = "extra condiments-" + rsp["condiments"]
    elif(rspKey == "drinks"):
        requestId = "refill drinks-" + rsp["drinks"]
    elif(rspKey == "napkins"):
        requestId = "more napkins"
    elif(rspKey == "cutlery"):
        requestId = "more cutlery"
    elif(rspKey == "clear"):
        requestId = "clear table"
    elif(rspKey == "issue"):
        requestId = "issue-"+rsp["issue"]
    elif(rspKey == "box"):
        requestId = "box food-"+rsp["box"]
    elif(rspKey == "other"):
        requestId = "other-"+rsp["other"]
    menu = session.get('menu',None)
    orderToken = session.get('orderToken',None)
    tableNum = session.get('table',None)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
    reqRef = db.reference(pathRequest)
    newReq = reqRef.push({"help":requestId})
    pathRequestkey = '/restaurants/' + estNameStr + '/' + location + "/requests/" + newReq.key + "/info"
    reqRefkey = db.reference(pathRequestkey)
    reqRefkey.set({"table":tableNum,"type":"help","token":orderToken})
    return(redirect(url_for("sitdownMenu",estNameStr=estNameStr,location=location)))


##########Employee###########
@app.route('/<estNameStr>/<location>/qsr-employee-login')
def EmployeeLoginQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffQSR/login.html"))

@app.route('/<estNameStr>/<location>/qsr-employee-login2')
def EmployeeLogin2QSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<estNameStr>/<location>/qsr-employee-login', methods=['POST'])
def EmployeeLoginCheckQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        token = str(uuid.uuid4())
        loginRef.update({
            "token":token,
            "time":time.time()
        })
        session["token"] = token
        return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-view')
def EmployeePanelQSR(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLoginQSR",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2QSR",estNameStr=estNameStr,location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + location + "/orderQSR"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
    except Exception as e:
        ordsGet = {}
    menu = findMenu(estNameStr,location)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    categories = list(menuInfo.keys())
    activeItems = []
    inactiveItems = []
    for cats in categories:
        itms = list(dict(menuInfo[cats]).keys())
        for itm in itms:
            if(menuInfo[cats][itm]["descrip"] != "INACTIVE"):
                appItem = str(cats) + "~" + str(itm)
                activeItems.append(appItem)
            else:
                appItem = str(cats) + "~" + str(itm)
                inactiveItems.append(appItem)
    return(render_template("POS/StaffQSR/View.html", location=location.capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, orders=ordsGet))


@app.route('/<estNameStr>/<location>/qsr-activate-item~<cat>~<item>~<menu>')
def activateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-deactivate-item~<cat>~<item>~<menu>')
def deactivateItemQSR(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-view-success', methods=["POST"])
def EmployeeSuccessQSR(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/orderQSR/" + reqToken
    reqRef = db.reference(pathRequest)
    reqRef.delete()
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/qsr-sendOrder', methods=["POST"])
def sendOrderQsr(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    token = rsp["token"]
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
    qsrOrderRef = db.reference(qsrOrderPath)
    qsrOrderRef.update({
        token:{
            "cart":dict(order['cart']),
            "info":{"name":order["name"],
                    "number":order['phone'],
                    "paid":"PAID",
                    "subtotal":order['subtotal'],
                    "total":order['total'],
                    'table':order['table']}
            }
    })

    checkmate = db.reference('/restaurants/' + estNameStr + '/' + location + '/checkmate').get()
    if(checkmate == 0):
        sendCheckmate(estNameStr,location, token)

    if(order['email'] != "no-email"):
        getSquare(estNameStr)
        now = datetime.datetime.now(tzGl[location])
        write_str = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize() + " @"
        write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
        write_str += "\n \n"
        cart = dict(order["cart"])
        subtotal = 0
        items = []
        cartKeys = list(cart.keys())
        for keys in cartKeys:
            subtotal += cart[keys]["price"]
            dispStr = cart[keys]["dispStr"]
            write_str += dispStr + "\n"
        subtotal += 0.25
        subtotalStr = "${:0,.2f}".format(subtotal)
        taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
        tax = "${:0,.2f}".format(subtotal * taxRate)
        tax += " (" + str(float(taxRate * 100)) + "%)"
        total = "${:0,.2f}".format(subtotal * (1+taxRate))
        write_str+= "\n \n"
        write_str += subtotalStr +"\n"+tax + "\n"+ total +"\n \n \n"
        write_str += 'Thank You For Your Order ' + str(order['name']).capitalize() + " !"
        SUBJECT = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize()
        message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
        # smtpObj.sendmail(sender, [order['email']], message)
        sendEmail(sender, order['email'], mesg)
    return(redirect(url_for("EmployeePanelQSR",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/employee-login')
def EmployeeLogin(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login.html"))

@app.route('/<estNameStr>/<location>/employee-login2')
def EmployeeLogin2(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    return(render_template("POS/StaffSitdown/login2.html"))

@app.route('/<estNameStr>/<location>/employee-login', methods=['POST'])
def EmployeeLoginCheck(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    code = rsp['code']
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        token = str(uuid.uuid4())
        loginRef.update({
            "token":token,
            "time":time.time()
        })
        session["token"] = token
        return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))
    else:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view')
def EmployeePanel(estNameStr,location):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    token = session.get('token',None)
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + location + "/employee/")
    loginData = dict(loginRef.get())
    try:
        if(((token == loginData["token"]) and (time.time() - loginData["time"] <= 3600))):
            pass
        else:
            return(redirect(url_for("EmployeeLogin",estNameStr=estNameStr,location=location)))
    except Exception as e:
        return(redirect(url_for("EmployeeLogin2",estNameStr=estNameStr,location=location)))
    try:
        ordPath = '/restaurants/' + estNameStr + '/' + location + "/orders/"
        ordsRef = db.reference(ordPath)
        ordsGet = dict(ordsRef.get())
        tokens = list(ordsGet)
        for tt in tokens:
            if(int(ordsGet[tt]["QSR"]) == 0):
                print(ordsGet[tt])
                del ordsGet[tt]
    except Exception as e:
        ordsGet = {}
    try:
        pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/"
        reqRef = db.reference(pathRequest)
        reqData = dict(reqRef.get())
    except Exception as e:
        reqData = {}
    menu = findMenu(estNameStr,location)
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories"
    menuInfo = dict(db.reference(pathMenu).get())
    categories = list(menuInfo.keys())
    activeItems = []
    inactiveItems = []
    for cats in categories:
        itms = list(dict(menuInfo[cats]).keys())
        for itm in itms:
            if(menuInfo[cats][itm]["descrip"] != "INACTIVE"):
                appItem = str(cats) + "~" + str(itm)
                activeItems.append(appItem)
            else:
                appItem = str(cats) + "~" + str(itm)
                inactiveItems.append(appItem)
    return(render_template("POS/StaffSitdown/View.html", location=location.capitalize(), restName=str(estNameStr.capitalize()), menu=menu, activeItems=activeItems, inactiveItems=inactiveItems, reqData=reqData, orders=ordsGet))


@app.route('/<estNameStr>/<location>/activate-item~<cat>~<item>~<menu>')
def activateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["tmp"]
    db.reference(pathMenu).update({"descrip":descrip})
    pathDel = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item +"/tmp"
    db.reference(pathDel).delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/deactivate-item~<cat>~<item>~<menu>')
def deactivateItem(estNameStr,location,cat,item,menu):
    if(checkLocation(estNameStr,location) == 1):
        return(redirect(url_for("findRestaurant")))
    pathMenu = '/restaurants/' + estNameStr + '/' + location + "/menu/" + menu + "/categories/"+ cat + "/" + item
    descrip = dict(db.reference(pathMenu).get())["descrip"]
    db.reference(pathMenu).update({"tmp":descrip})
    db.reference(pathMenu).update({"descrip":"INACTIVE"})
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view-success', methods=["POST"])
def EmployeeSuccess(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        del reqData["info"]
        tickRef = db.reference(pathTicket)
        cartData = reqData
        cartKeys = list(cartData.keys())
        # return(str(cartKeys))
        addTotal = 0
        req = []
        for ccx in range(len(cartKeys)):
            addTotal += float(cartData[cartKeys[ccx]]["price"])
        tickRef.push(reqData)
        currTotal = float(dict(db.reference(pathTotal).get())["subtotal"])
        tickTotal = db.reference(pathTotal).update({"subtotal":float(currTotal+addTotal)})
    reqRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view-warning', methods=["POST"])
def EmployeeWarn(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    if(reqData["info"]["type"] == "order"):
        pathTicket = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken +"/ticket"
        pathTotal = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
        del reqData["info"]
        tickRef = db.reference(pathTicket)
        cartData = reqData
        cartKeys = list(cartData.keys())
        # return(str(cartKeys))
        addTotal = 0
        req = []
        for ccx in range(len(cartKeys)):
            addTotal += float(cartData[cartKeys[ccx]]["price"])
        tickRef.push(reqData)
        currTotal = float(dict(db.reference(pathTotal).get())["subtotal"])
        tickTotal = db.reference(pathTotal).update({"subtotal":float(currTotal+addTotal)})
    AlertSend = db.reference(pathUser).update({"alert":str("Warning: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

@app.route('/<estNameStr>/<location>/view-reject', methods=["POST"])
def EmployeeReject(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    reqToken = rsp["req"]
    alert = rsp["reason"]
    pathRequest = '/restaurants/' + estNameStr + '/' + location + "/requests/" + reqToken
    reqRef = db.reference(pathRequest)
    reqData = dict(reqRef.get())
    orderToken = reqData["info"]["token"]
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    AlertSend = db.reference(pathUser).update({"alert":str("Request Cancelled: "+alert)})
    AlertTime = db.reference(pathUser).update({"alertTime":time.time()})
    reqRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/view-editBill', methods=["POST"])
def EditBill(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    amt = float(rsp["amt"])
    itm = str(rsp["itm"])
    pathUserX = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    pathUser = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken + "/ticket"
    cartRefItm = db.reference(pathUser)
    subtotal = float(db.reference(pathUserX).get()["subtotal"])
    subtotal += amt
    db.reference(pathUserX).update({"subtotal":subtotal})
    cartRefItm.push({str(uuid.uuid4()):{
        'cat':"",
        'img':"",
        'itm':itm,
        'qty':1,
        'notes':"added by staff",
        'dispStr':"Staff Correction: "+ itm + "  ($" + "{:0,.2f}".format(amt) + ")",
        'price':amt,
        'mods':[["",str(amt)]],
        'unitPrice':amt
    }})
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))


@app.route('/<estNameStr>/<location>/view-clearTicket', methods=["POST"])
def RemBill(estNameStr,location):
    request.parameter_storage_class = ImmutableOrderedMultiDict
    rsp = ((request.form))
    orderToken = rsp["req"]
    pathUserX = '/restaurants/' + estNameStr + '/' + location + "/orders/" + orderToken
    remRef = db.reference(pathUserX)
    remRef.delete()
    return(redirect(url_for("EmployeePanel",estNameStr=estNameStr,location=location)))

####SQUARE####
@app.route('/<estNameStr>/<location>/verify-kiosk', methods=["POST"])
def verifyOrder(estNameStr,location):
    rsp = request.get_json()
    print(rsp)
    token = rsp['tokenVal']
    pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
    orderRef = db.reference(pathOrder)
    order = dict(orderRef.get())
    if(order['QSR'] == 0):
        qsrOrderPath = '/restaurants/' + estNameStr + '/' + location + '/orderQSR'
        qsrOrderRef = db.reference(qsrOrderPath)
        qsrOrderRef.update({
            token:{
                "cart":dict(order['cart']),
                "info":{"name":order["name"],
                        "number":order['phone'],
                        "paid":"PAID",
                        "subtotal":order['subtotal'],
                        "total":order['total'],
                        'table':order['table']}
                }
        })
        packet = {
            "code":token,
            "success": "true"
        }
        checkmate = db.reference('/restaurants/' + estNameStr + '/' + location + '/checkmate').get()
        if(checkmate == 0):
            sendCheckmate(estNameStr,location, token)
        if(order['email'] != "no-email"):
            getSquare(estNameStr)
            now = datetime.datetime.now(tzGl[location])
            write_str = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize() + " @"
            write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
            write_str += "\n \n"
            cart = dict(order["cart"])
            subtotal = 0
            items = []
            cartKeys = list(cart.keys())
            for keys in cartKeys:
                subtotal += cart[keys]["price"]
                dispStr = cart[keys]["dispStr"]
                write_str += dispStr + "\n"
            subtotal += 0.25
            subtotalStr = "${:0,.2f}".format(subtotal)
            taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
            tax = "${:0,.2f}".format(subtotal * taxRate)
            tax += " (" + str(float(taxRate * 100)) + "%)"
            total = "${:0,.2f}".format(subtotal * (1+taxRate))
            write_str+= "\n \n"
            write_str += subtotalStr +"\n"+tax + "\n"+ total +"\n \n \n"
            write_str += 'Thank You For Your Order ' + str(order['name']).capitalize() + " !"
            SUBJECT = "Your Order From "+ estNameStr.capitalize()  + " " + location.capitalize()
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            # smtpObj.sendmail(sender, [order['email']], message)
            sendEmail(sender, order['email'], mesg)
        return jsonify(packet)
    else:
        pathOrder = '/restaurants/' + estNameStr + '/' + location + "/orders/" + token
        orderRef = db.reference(pathOrder)
        orderRef.update({
            "paid":"PAID"
        })
        packet = {
            "code":tokenVal,
            "success": "true"
        }
        if(order['email'] != "no-email"):
            now = datetime.datetime.now(tzGl[location])
            write_str = "Your Meal From "+ estNameStr + " " + location + " @"
            write_str += str(now.hour) + ":" + str(now.minute) + " on " + str(now.month) + "-" + str(now.day) + "-" + str(now.year)
            write_str += "\n \n"
            # TODOX
            cart = dict(order["ticket"])
            subtotal = order["subtotal"]
            subtotalStr = "${:0,.2f}".format(subtotal)
            taxRate = float(db.reference('/restaurants/' + estNameStr + '/' + location + '/taxrate').get())
            tax = "${:0,.2f}".format(subtotal * taxRate)
            tax += " (" + str(float(taxRate * 100)) + "%)"
            total = "${:0,.2f}".format(subtotal * (1+taxRate))
            cartKeys = list(cart.keys())
            for ck in cartKeys:
                ckKeys = list(cart[ck].keys())
                for ckk in ckKeys:
                    dispStr = cart[ck][ckk]["dispStr"] +  "\n"
                    write_str += dispStr
            write_str+= "\n \n"
            write_str += subtotalStr + "\n" + tax + "\n" + total + "\n \n \n"
            write_str += 'Thank You For Dining with us ' + str(order['name']).capitalize() + " !"
            SUBJECT = "Thank You For Dining at "+ estNameStr + " " + location
            message = 'Subject: {}\n\n{}'.format(SUBJECT, write_str)
            # smtpObj.sendmail(sender, [order['email']], message)
            sendEmail(sender, order['email'], message)
        orderRef.delete()
        return jsonify(packet)


@app.route('/<estNameStr>/<locationX>/reader/<type>', methods=["POST"])
def GenReaderCode(estNameStr,locationX,type):
    rsp = request.get_json()
    print(rsp)
    code = rsp['code']
    kioskType = ["qsr-startKiosk","sitdown-startKiosk"]
    sqRef = db.reference(str('/restaurants/' + estNameStr))
    squareToken = dict(sqRef.get())["sq-token"]
    loginRef = db.reference('/restaurants/' + estNameStr + '/' + str(locationX) + "/employee")
    loginData = dict(loginRef.get())
    hashCheck = pbkdf2_sha256.verify(code, loginData['code'])
    if(hashCheck == True):
        client = Client(
            access_token=squareToken,
            environment='production',
        )
        api_locations = client.locations
        mobile_authorization_api = client.mobile_authorization
        # Call list_locatio
        result = api_locations.list_locations()
        if result.is_success():
        	# The body property is a list of locations
            locations = result.body['locations']
        	# Iterate over the list
            for location in locations:
                if((dict(location.items())["status"]) == "ACTIVE"):
                    # print(dict(location.items()))
                    locationName = (dict(location.items())["name"]).replace(" ","-")
                    # print(locationName)
                    locationId = dict(location.items())["id"]
                    if(str(locationName).lower() == locationX):
                        body = {}
                        body['location_id'] = locationId
                        result = mobile_authorization_api.create_mobile_authorization_code(body)
                        if result.is_success():
                            code = dict(result.body)['authorization_code']
                            print(code)
                            packet = {
                                "code":code,
                                "link": str(mainLink + locationX + "/" + kioskType[int(type)])
                            }
                            return jsonify(packet)
                        elif result.is_error():
                            packet = {
                                "code":"invlaid location"
                            }
                            return jsonify(packet)
    else:
        packet = {
            "code":"invlaid employee code"
        }
        return jsonify(packet)


@app.route('/find-restaurant')
def findRestaurant():
    restaurantsDict = dict(db.reference('/restaurants').get())
    restaurants = list(restaurantsDict.keys())
    return(render_template("Global/findrestaurant.html", restaurants=restaurants))


@app.route('/restname~<restaurant>')
def findRestaurantLocation(restaurant):
    restaurantsDict = dict(db.reference('/restaurants/' + restaurant).get())
    del restaurantsDict['admin-info']
    del restaurantsDict['sq-token']
    locations = list(restaurantsDict.keys())
    return(render_template("Global/findrestaurantloc.html",restaurant=restaurant,locations=locations))

@app.route('/pickscreen-<restaurant>~<location>')
def pickScreen(restaurant, location):
    return(render_template("Global/pickScreen.html",restaurant=restaurant,location=location))





if __name__ == '__main__':
    try:
        ##print(locationsPaths.keys())
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        app.permanent_session_lifetime = datetime.timedelta(minutes=240)
        app.debug = True
        app.run(host="0.0.0.0",port=5000)
    except KeyboardInterrupt:
        sys.exit()
