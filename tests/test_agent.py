import concurrent.futures,hashlib,hmac,json,tempfile,threading,time,unittest,urllib.error,urllib.request
from pathlib import Path
from unittest.mock import patch
from core import Store,RuleError,verify_signature,consent_evidence,notification
from configure import payloads
from demo import populate
from server import Handler,Server
D={'caller_type':'customer','appliance_type':'washer','issue':'Not draining','brand':'LG','customer_name':'Test Customer','phone':'+1 202-555-0111','service_address':'1 Example St, Arlington, VA 22201','notes':'','warranty_mentioned':False}
def turns(*items):return {'transcript_object':[{'role':r,'content':c} for r,c in items]}
C=turns(('agent','The service call fee is ninety-nine dollars. Is that okay?'),('user','Yes, that works.'))
def sign(raw,stamp=None):
 stamp=stamp or int(time.time()*1000)
 return f'v={stamp},d='+hmac.new(b'test-key',raw+str(stamp).encode(),hashlib.sha256).hexdigest()
class Rules(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'db')
 def tearDown(self):self.tmp.cleanup()
 def prep(self,**kw):return self.s.prepare('one',{**D,**kw})
 def args(self,q,**kw):return {'quote_id':q['quote_id'],'fee_accepted':True,'acceptance_words':'Yes, that works.',**kw}
 def event(self,event='call_ended',summary=''):
  return {'event':event,'call':{'call_id':'one','call_status':'ended','transcript':'User: Hello','call_analysis':{'call_summary':summary,'custom_analysis_data':{'call_category':'spam'}}}}
 def test_standard_fee(self):self.assertEqual(self.prep()['service_fee'],99)
 def test_brand_without_warranty(self):self.assertEqual(self.prep(brand='Samsung')['route'],'standard')
 def test_warranty_aliases(self):
  for b in ['LG','Samsung','GE','General Electric','GE Appliances']:self.assertEqual(self.prep(brand=b,warranty_mentioned=True)['service_fee'],0)
 def test_unsupported_warranty(self):self.assertEqual(self.prep(brand='Bosch',warranty_mentioned=True)['route'],'message_only')
 def test_missing_intake(self):
  for f in ['appliance_type','issue','brand','customer_name','phone','service_address']:
   with self.assertRaises(RuleError):self.prep(**{f:''})
 def test_invalid_phone(self):
  with self.assertRaises(RuleError):self.prep(phone='123')
 def test_string_boolean(self):
  with self.assertRaises(RuleError):self.prep(warranty_mentioned='false')
 def test_rep_and_spam_cannot_book(self):
  for k in ['warranty_representative','spam']:
   with self.assertRaises(RuleError):self.prep(caller_type=k)
 def test_acceptance_required(self):
  q=self.prep()
  with self.assertRaises(RuleError):self.s.book('one',self.args(q,fee_accepted=False),C)
 def test_exact_evidence_required(self):
  q=self.prep()
  with self.assertRaises(RuleError):self.s.book('one',self.args(q,acceptance_words='sure'),C)
 def test_standard_booking(self):
  q=self.prep();r=self.s.book('one',self.args(q),C);self.assertTrue(r['success']);self.assertFalse(r['appointment_confirmed'])
 def test_missing_disclosure(self):self.assertFalse(consent_evidence(turns(('user','Yes')),'Yes'))
 def test_question_not_consent(self):self.assertFalse(consent_evidence(turns(('agent','$99'),('user','Okay, but is that the total?')),'Okay'))
 def test_negation_not_consent(self):self.assertFalse(consent_evidence(turns(('agent','$99'),('user','Yes, but do not book yet')),'Yes'))
 def test_old_consent_not_reused(self):
  q=self.s.prepare('one',D,C)
  with self.assertRaises(RuleError):self.s.book('one',self.args(q),C)
 def test_text_transcript(self):self.assertTrue(consent_evidence({'transcript':'Agent: Fee is $99.\nUser: Yes, that works.'},'Yes, that works.'))
 def test_warranty_no_consent_needed(self):
  q=self.prep(warranty_mentioned=True);self.assertTrue(self.s.book('one',self.args(q,fee_accepted=False,acceptance_words=''),{})['success'])
 def test_late_warranty_old_quote_rejected(self):
  q=self.prep();self.prep(warranty_mentioned=True)
  with self.assertRaises(RuleError):self.s.book('one',self.args(q),C)
 def test_unsupported_warranty_old_quote_rejected(self):
  q=self.prep();self.prep(warranty_mentioned=True,brand='Bosch')
  with self.assertRaises(RuleError):self.s.book('one',self.args(q),C)
 def test_cross_call_quote_rejected(self):
  q=self.prep()
  with self.assertRaises(RuleError):self.s.book('other',self.args(q),C)
 def test_concurrent_retries_create_one_request(self):
  q=self.prep(warranty_mentioned=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:r=list(p.map(lambda _:self.s.book('one',self.args(q),{}),range(4)))
  self.assertEqual(len({x['reference'] for x in r}),1)
 def test_rep_message(self):
  r=self.s.message('rep',{'caller_type':'warranty_representative','caller_name':'Alex','company':'AHS','callback_phone':'2025550111','job_description':'Dryer job'})
  self.assertTrue(r['success']);self.assertNotIn('booking_reference',self.s.feed()[0])
 def test_incomplete_rep_rejected(self):
  with self.assertRaises(RuleError):self.s.message('rep',{'caller_type':'warranty_representative','job_description':'Repair'})
 def test_spam_message_rejected(self):
  with self.assertRaises(RuleError):self.s.message('spam',{'caller_type':'spam','job_description':'Sales'})
 def test_message_invalidates_quote(self):
  q=self.prep();self.s.message('one',{'caller_type':'message','job_description':'Call me'})
  with self.assertRaises(RuleError):self.s.book('one',self.args(q),C)
 def test_hangup_feed(self):self.s.webhook(self.event());self.assertEqual(len(self.s.feed()),1)
 def test_duplicate_webhook(self):
  self.s.webhook(self.event());self.assertTrue(self.s.webhook(self.event())['duplicate']);self.assertEqual(len(self.s.feed()),1)
 def test_analysis_edits_same_notification(self):
  self.s.webhook(self.event());self.s.delivered(self.s.pending(),123);self.s.webhook(self.event('call_analyzed','Final'))
  self.assertEqual(self.s.pending()['telegram_message_id'],123)
 def test_out_of_order_events(self):
  self.s.webhook(self.event('call_analyzed','Final'));self.s.webhook(self.event());self.assertEqual(self.s.feed()[0]['summary'],'Final')
 def test_tools_override_analysis(self):
  self.prep();self.s.webhook(self.event('call_analyzed'));self.assertEqual(self.s.feed()[0]['call_type'],'standard')
 def test_failed_delivery_retry(self):
  self.s.webhook(self.event());self.s.failed(self.s.pending(),'Unavailable');self.assertIsNone(self.s.pending());self.assertEqual(self.s.feed()[0]['notification_error'],'Unavailable')
 def test_synthetic_calls_not_sent(self):populate(self.s);self.assertIsNone(self.s.pending());self.assertEqual(len(self.s.feed()),4)
 def test_message_length(self):self.assertLessEqual(len(notification({'call_id':'x','notes':'x'*6000})),4000)
 def test_config_tools(self):
  llm,a=payloads('https://example.com','female-voice','test');self.assertEqual({t['name'] for t in llm['general_tools']},{'prepare_booking','book_repair','take_message','end_call'})
class Security(unittest.TestCase):
 def test_valid_signature(self):self.assertTrue(verify_signature(b'{}','test-key',sign(b'{}')))
 def test_tampering(self):self.assertFalse(verify_signature(b'changed','test-key',sign(b'{}')))
 def test_expiry(self):self.assertFalse(verify_signature(b'{}','test-key',sign(b'{}',1000)))
 def test_missing_key(self):self.assertFalse(verify_signature(b'{}','',''))
class HTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.srv=Server(('127.0.0.1',0),Handler);self.srv.store=Store(Path(self.tmp.name)/'db');self.srv.dashboard_token='dashboard-test'
  self.env=patch.dict('os.environ',{'RETELL_API_KEY':'test-key','TOOL_TOKEN':'tool-test'});self.env.start()
  threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.srv.server_port)
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.env.stop();self.tmp.cleanup()
 def test_dashboard_auth(self):
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.base+'/api/calls')
  self.assertEqual(e.exception.code,401)
 def test_reviewer_only_sees_review_window(self):
  self.srv.store.webhook({'event':'call_ended','call':{'call_id':'old'}})
  since=time.time()
  self.srv.store.webhook({'event':'call_ended','call':{'call_id':'new'}})
  self.srv.store.webhook({'event':'call_ended','call':{'call_id':'fixture','metadata':{'synthetic':True}}})
  with patch.dict('os.environ',{'REVIEW_TOKEN':'review-test','REVIEW_SINCE':str(since)}):
   req=urllib.request.Request(self.base+'/api/calls',headers={'Authorization':'Bearer review-test'})
   with urllib.request.urlopen(req) as r:self.assertEqual([c['call_id'] for c in json.load(r)['calls']],['new'])
 def test_reviewer_cannot_post(self):
  with patch.dict('os.environ',{'REVIEW_TOKEN':'review-test'}):
   req=urllib.request.Request(self.base+'/anything',data=b'{}',headers={'Authorization':'Bearer review-test'})
   with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
   self.assertEqual(e.exception.code,401)
 def test_unsigned_webhook(self):
  req=urllib.request.Request(self.base+'/webhooks/retell',data=b'{}')
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
  self.assertEqual(e.exception.code,401)
 def test_signed_webhook_feed(self):
  raw=json.dumps({'event':'call_ended','call':{'call_id':'http-test','transcript':'User: Hello'}}).encode()
  req=urllib.request.Request(self.base+'/webhooks/retell',data=raw,headers={'Content-Type':'application/json','X-Retell-Signature':sign(raw)})
  self.assertEqual(urllib.request.urlopen(req).status,200)
  req=urllib.request.Request(self.base+'/api/calls',headers={'Authorization':'Bearer dashboard-test'})
  with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['calls'][0]['call_id'],'http-test')
 def test_tools_round_trip(self):
  def post(name,args,call=None):
   raw=json.dumps({'call':{'call_id':'http-book',**(call or {})},'args':args}).encode()
   req=urllib.request.Request(self.base+'/tools/'+name,data=raw,headers={'Content-Type':'application/json','X-Retell-Signature':sign(raw),'Authorization':'Bearer tool-test'})
   with urllib.request.urlopen(req) as r:return json.load(r)
  q=post('prepare_booking',D);r=post('book_repair',{'quote_id':q['quote_id'],'fee_accepted':True,'acceptance_words':'Yes, that works.'},C);self.assertTrue(r['success'])

class Worker(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'db')
  self.s.webhook({'event':'call_ended','call':{'call_id':'worker-call','transcript':'User: Hello'}})
 def tearDown(self):self.tmp.cleanup()
 def once(self):
  class Stop:
   n=0
   def wait(self,_):self.n+=1;return self.n>1
  return Stop()
 def test_send_then_edit(self):
  from server import notification_worker
  with patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHAT_ID':'1'}),patch('server.telegram_request',return_value={'message_id':77}) as send:
   notification_worker(self.s,self.once());self.assertEqual(send.call_args.args[1],'sendMessage')
   self.s.webhook({'event':'call_analyzed','call':{'call_id':'worker-call','call_analysis':{'call_summary':'Final'}}})
   notification_worker(self.s,self.once());self.assertEqual(send.call_args.args[1],'editMessageText');self.assertEqual(send.call_args.args[2]['message_id'],77)
 def test_delivery_failure_is_queued(self):
  from server import notification_worker
  with patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHAT_ID':'1'}),patch('server.telegram_request',side_effect=RuntimeError('Temporary issue')):
   notification_worker(self.s,self.once())
  self.assertEqual(self.s.feed()[0]['notification_error'],'Temporary issue')
 def test_synthetic_not_transmitted(self):
  from server import notification_worker
  fresh=Store(Path(self.tmp.name)/'demo');populate(fresh)
  with patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHAT_ID':'1'}),patch('server.telegram_request') as send:
   notification_worker(fresh,self.once());send.assert_not_called()

if __name__=='__main__':unittest.main()

class PhoneRegression(unittest.TestCase):
 def test_reject_actual_live_misrecognition(self):
  from core import phone_ok
  self.assertFalse(phone_ok('202-555-010142'))
 def test_us_number_formats(self):
  from core import phone_ok
  for n in ['202-555-0142','(202) 555-0142','+1 202 555 0142','12025550142']:self.assertTrue(phone_ok(n))
 def test_invalid_us_lengths_and_letters(self):
  from core import phone_ok
  for n in ['2025550','+1 202555010142','9992025550142','2025550142oops']:self.assertFalse(phone_ok(n))
 def test_explicit_international_number(self):
  from core import phone_ok
  self.assertTrue(phone_ok('+44 20 7946 0958'))
