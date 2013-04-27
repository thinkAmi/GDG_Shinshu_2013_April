#-*- coding: utf-8 -*-
import yaml
import os

import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch

from twilio import twiml
from twilio.rest import TwilioRestClient

from models import Phone


# See: https://jp.twilio.com/docs/quickstart/python/twiml/record-caller-leave-message
# (TwiML: Python クイックスタート チュートリアル)
# 分かりやすいTwilioとTwiML変換
# https://twilio-python.readthedocs.org/en/latest/usage/twiml.html


def _get_api_key():
    return yaml.safe_load(open('api.yaml').read().decode('utf-8'))



class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(template.render('html/index.html', {}))


class Memory(webapp2.RequestHandler):
    def post(self):
        talk = self.request.get('talk') if self.request.get('talk') else u'GDG信州Aprilへようこそ'
        phone = Phone(id='twilio', talk=talk)
        phone.put()

        self.response.out.write(template.render('html/memorize.html', {}))



#------------------------
# 手元からTwilioへ電話した時
#------------------------
# 選択メニュー
class Menu(webapp2.RequestHandler):
    def post(self):
        r = twiml.Response()
        with r.gather(numDigits=1, action='/select', method='POST') as g:
            g.say(u'再生は1を、録音は2を押してください', language='ja-jp')

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.write(str(r))


# 選択結果
class Selection(webapp2.RequestHandler):
    def post(self):
        digit = self.request.get('Digits')

        # Datastoreのを再生
        if digit == '1':
            phone = Phone.get_by_id('twilio')
            r = twiml.Response()
            r.say(unicode(phone.talk), language='ja-jp')
            self.response.headers['Content-Type'] = 'text/xml'
            self.response.write(str(r))

        # 録音して即再生
        # See: http://www.twilio.com/docs/api/rest/recording
        elif digit == '2':
            r = twiml.Response()
            r.say(u'10秒で　いれてね', language='ja-jp')
            r.record(maxLength=10, finishOnKey='#', action='/play', method='POST')

            self.response.headers['Content-Type'] = 'text/xml'
            self.response.write(str(r))

        else:
            phone = Phone.get_by_id('twilio')
            r = twiml.Response()
            r.say(u'それはだめです', language='ja-jp')
            self.response.headers['Content-Type'] = 'text/xml'
            self.response.write(str(r))


# 再生
class Play(webapp2.RequestHandler):
    def post(self):
        recordingUrl = self.request.get('RecordingUrl')

        r = twiml.Response()
        r.play(recordingUrl)

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.write(str(r))


# 録音一覧
class Records(webapp2.RequestHandler):
    def post(self):
        keys = _get_api_key()

        client = TwilioRestClient(keys['account_sid'], keys['auth_token'])
        records = client.recordings.list()
        self.response.out.write(template.render('html/record_list.html',{'records': records,
                                                                        }))


# 録音の削除
class Delete(webapp2.RequestHandler):
    def post(self):
        keys = _get_api_key()
        client = TwilioRestClient(keys['account_sid'], keys['auth_token'])
        records = client.recordings.list()

        if records:
            # See: https://twilio-python.readthedocs.org/en/latest/usage/recordings.html
            sid = records[0].sid
            client.recordings.delete(sid)
            self.response.out.write(template.render('html/delete.html', {}))

        else:
            self.response.out.write(template.render('html/nothing.html', {}))


#------------------------
# Twilioから手元へ電話した時
#------------------------
# 電話した時のURLを指定
class Call(webapp2.RequestHandler):
    def post(self):
        keys = _get_api_key()

        client = TwilioRestClient(keys['account_sid'], keys['auth_token'])
        call = client.calls.create(
            url='http://gdg-shinshu-april.appspot.com/outbound',
            to=keys['validated_phone_number'],
            # 「from_」と、アンダースコアがあることに、注意
            from_=keys['twilio_phone_number'],
            )
        self.response.out.write(template.render('html/called.html', {}))

# 実際の反応
class OutboundCall(webapp2.RequestHandler):
    def post(self):
        phone = Phone.get_by_id('twilio')
        r = twiml.Response()
        r.say(unicode(phone.talk), language='ja-jp')
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.write(str(r))




#------------------------
# SMS関係
#------------------------
# SMSは、日本の番号では、今のところ使えない
class SMS(webapp2.RequestHandler):
    def post(self):
        keys = _get_api_key()
        phone = Phone.get_by_id('twilio')

        client = TwilioRestClient(keys['account_sid'], keys['auth_token'])
        client.sms.messages.create(
            body=phone.talk,
            to=keys['validated_phone_number'],
            from_=keys['twilio_phone_number'],
            )

        self.response.out.write(template.render('html/sms.html', {}))







app = webapp2.WSGIApplication([
                                ('/', MainPage),
                                ('/memorize', Memory),
                                ('/call', Call),
                                ('/outbound', OutboundCall),
                                ('/menu', Menu),
                                ('/select', Selection),
                                ('/play', Play),
                                ('/list', Records),
                                ('/delete', Delete),
                                # 今のところ使えないので、コメントアウト
                                # ('/sms', SMS),
                              ],
                              debug=True)