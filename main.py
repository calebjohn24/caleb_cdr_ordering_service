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
from flask_compress import Compress
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.utils import secure_filename
from flask import redirect, url_for
from flask import render_template, send_file
from flask_session import Session
from flask_sslify import SSLify
from square.client import Client
from werkzeug.datastructures import ImmutableOrderedMultiDict
from flask import Blueprint, render_template, abort
from Cedar.admin import admin_panel, menu, pw_reset, feedback, schedule, billing
from Cedar.kiosk import online_menu, payments, qsr_menu, sd_menu, register
from Cedar.employee import qsr_employee, sd_employee
from Cedar.main_page import find_page

infoFile = open("info.json")
info = json.load(infoFile)
mainLink = info['mainLink']

botNumber = info['number']
adminSessTime = 3599
client = plivo.RestClient(auth_id='MAYTVHN2E1ZDY4ZDA2YZ',
                          auth_token='ODgzZDA1OTFiMjE2ZTRjY2U4ZTVhYzNiODNjNDll')
cred = credentials.Certificate('CedarChatbot-b443efe11b73.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cedarchatbot.firebaseio.com/',
    'storageBucket': 'cedarchatbot.appspot.com'
})

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
storage_client = storage.Client.from_service_account_json(
    'CedarChatbot-b443efe11b73.json')
bucket = storage_client.get_bucket('cedarchatbot.appspot.com')
sender = 'cedarrestaurantsbot@gmail.com'
emailPass = "cda33d07-f6bd-479e-806f-5d039ae2fa2d"
# smtpObj = smtplib.SMTP_SSL("smtp.gmail.com", 465)
# smtpObj.login(sender, emailPass)

dayNames = ["MON", "TUE", "WED", "THURS", "FRI", "SAT", "SUN"]
global locationsPaths
locationsPaths = {}

app = Flask(__name__)
app.register_blueprint(admin_panel.admin_panel_blueprint)
app.register_blueprint(find_page.find_page_blueprint)
app.register_blueprint(menu.menu_panel_blueprint)
app.register_blueprint(pw_reset.pw_reset_blueprint)
app.register_blueprint(feedback.feedback_blueprint)
app.register_blueprint(schedule.schedule_blueprint)
app.register_blueprint(online_menu.online_menu_blueprint)
app.register_blueprint(sd_menu.sd_menu_blueprint)
app.register_blueprint(qsr_menu.qsr_menu_blueprint)
app.register_blueprint(payments.payments_blueprint)
app.register_blueprint(qsr_employee.qsr_employee_blueprint)
app.register_blueprint(sd_employee.sd_employee_blueprint)
app.register_blueprint(register.register_kiosk_blueprint)
app.register_blueprint(billing.billing_blueprint)
scKey = str(uuid.uuid4())
app.secret_key = scKey
sslify = SSLify(app)
Compress(app)
CSRFProtect(app)


@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('find_page.findRestaurant'))

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return (str(e.description), 400)


if __name__ == '__main__':
    try:
        app.secret_key = scKey
        sslify = SSLify(app)
        app.config['SESSION_TYPE'] = 'filesystem'
        sess = Session()
        sess.init_app(app)
        sess.permanent = True
        # app.permanent_session_lifetime = datetime.timedelta(minutes=240)
        app.debug = True
        app.jinja_env.cache = {}
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        sys.exit()
