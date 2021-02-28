# MAIL.PY

from random import choice as rchoice
from io import StringIO

SMTPHOST = 'smtp.office365.com:587'

# Sending mail
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

class SMTPRemote:
    def __init__(self, user, pwd, remote=SMTPHOST):
        self.remote = remote
        self.server = None
        self.open()
        self.user = user
        self.pwd = pwd
        self.login()

    def open(self):
        self.server = smtplib.SMTP(self.remote)
        self.server.ehlo()
        self.server.starttls()

    def login(self):
        self.server.login(self.user, password=self.pwd)

    def close(self):
        self.server.quit()

    def send(self, message):
        self.server.sendmail(message.sender, message.recipients, message.compile())

class Message:
    def __init__(self, sender, *recp):
        self.sender = sender
        self.recipients = recp
        self.mime = MIMEMultipart('mixed')
        self.body = MIMEMultipart('alternative')
        self.mime.attach(self.body)

    def write(self, data, ctype='plain'):
        m = MIMEText(data, _subtype=ctype, _charset='utf-8')
        self.body.attach(m)
        return m

    def attach(self, filepath):
        return self._attach(filepath, open(filepath, 'rb').read())

    def _attach(self, name, binary_data):
        f = MIMEApplication(binary_data)
        f.add_header('Content-Disposition', 'attachment', filename=os.path.split(name)[-1])
        self.mime.attach(f)
        return f

    def compile(self):
        return self.mime.as_string()

class MMS(Message):
    PROVIDERS = {'sprint': '@pm.sprint.com',
                'att': '@mms.att.net',
                'tmobile': '@tmomail.net',
                'verizon': '@vzwpix.com'}

    def __init__(self, sender, *recipients, group=False):
        """Give recipients as tuples with (number, service provider)"""
        if type(recipients[0]) not in (tuple, list):
            raise TypeError('Recipients for MMS must be (number, provider) tuples')
        self.recipients = [r[0].replace('-', '')+MMS.PROVIDERS[r[1]] for r in recipients]
        super().__init__(sender, *self.recipients)
        self.group = group

    def compile(self):
        self.mime['From'] = self.sender
        if self.group:
            self.mime['To'] = ', '.join((self.recipients))
        else:
            self.mime['To'] = ''
            self.mime['Bcc'] = ', '.join(self.recipients)
        return super().compile()


# MAIN.PY
import requests
from email.parser import BytesParser
import datetime as dt
from bs4 import BeautifulSoup
from time import sleep

print('The following information will be used to send text messages using MMS.')
user = input('Email (OUTLOOK ONLY): ')
pwd = input('Email password: ')

print('Logging into SMTP server...')
smtp = SMTPRemote(user, pwd)
print('Success.')
phone = ('', '')
while phone[1] not in MMS.PROVIDERS:
    phone = input('Phone number (no dashes): '), input('Service provider (att, sprint, verizon, tmobile): ').lower()

def sendmsg(string):
    global phone, smtp
    msg = MMS(user, phone)
    msg.write(string)
    smtp.send(msg)


def getNow():
    return dt.datetime.utcnow()
def strf(now):
    return now.strftime('%a, %b %d %Y %H:%M:%S GMT')

def html(s):
    return BeautifulSoup(s, 'html.parser')

def handle(data):
    global smtp, phone

    available = False
    
    rows = data.find_all('tr')
    for row in rows[1:-3]:
        try:
            columns = row.find_all('td')
            name = columns[0].get_text().strip().replace('\n', ' ')
            link = columns[0].a.get('href').strip().replace('\n', ' ')
            status = columns[1].get_text().strip().replace('\n', ' ')

            if status == "Stock Available":
                sendmsg('RTX STOCK AVAILABLE:\n%s' % link)
                available = True
                # AVAILABLE, DO SOMETHING
                
        except AttributeError:
            if 'name' in locals():
                print('ERROR: Bad item %s' % name)
            else:
                print('ERROR: Bad item', row.replace('\n', ''))

    return available


m = """GET  HTTP/1.1
Host: s3.amazonaws.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0 Waterfox/78.7.0
Accept: text/html, */*; q=0.01
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate, br
If-Modified-Since: {TIME}
Origin: https://www.nowinstock.net
Connection: keep-alive
Referer: https://www.nowinstock.net/
Sec-GPC: 1
"""

url = 'https://s3.amazonaws.com:443/nowinstock.net/modules/trackers/us/1498.html'

INTERVAL = 15

print('Sending you a test notification...')
sendmsg('This is a test notification.')
print('Notification sent. It may take a few seconds for Microsoft to deliver it.')
print('Now fetching updates every %d seconds.' % INTERVAL)
while True:
    time = strf(getNow())
    sleep(INTERVAL)
    
    req = m.format(TIME=time)

    reqline, headers = req.encode().split(b'\n', 1)
    headers = BytesParser().parsebytes(headers)

    content = requests.get(url, headers=headers).content

    if handle(html(content)):
        print(dt.datetime.now().strftime('[%H:%M:%S] Handled query successfully. Something was in stock!'))
    else: print(dt.datetime.now().strftime('[%H:%M:%S] Handled query successfully. Nothing is in stock lol.'))

smtp.close()
