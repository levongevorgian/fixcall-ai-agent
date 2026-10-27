"""Business rules, persistent call feed, and notification outbox. Python 3.11+."""
import hashlib
import hmac
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

KINDS = {'standard', 'eligible_warranty', 'warranty_representative', 'message', 'spam', 'unknown'}
REQUIRED = ('appliance_type', 'issue', 'brand', 'customer_name', 'phone', 'service_address')

class RuleError(ValueError):
    pass

def text(value, limit=1500):
    if not isinstance(value, str):
        return ''
    return value.strip()[:limit]

def phone_ok(value):
    value = text(value)
    if re.search(r'[^\d\s+().-]', value):
        return False
    digits = re.sub(r'\D', '', value)
    if value.startswith('+') and not value.startswith('+1'):
        return 8 <= len(digits) <= 15
    return len(digits) == 10 or (len(digits) == 11 and digits.startswith('1'))

def brand_key(value):
    return re.sub(r'[^a-z0-9]', '', text(value).lower())

def warranty_supported(brand):
    return brand_key(brand) in {'lg', 'lgelectronics', 'samsung', 'samsungelectronics', 'ge', 'generalelectric', 'geappliances'}

def verify_signature(body, key, signature, now_ms=None):
    """Matches Retell's official Python SDK HMAC format, raw UTF-8 body + timestamp."""
    if not key or not isinstance(signature, str):
        return False
    match = re.fullmatch(r'v=(\d+),d=([0-9a-f]{64})', signature)
    if not match:
        return False
    stamp = int(match[1])
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    if abs(now_ms - stamp) > 300000:
        return False
    expected = hmac.new(key.encode(), body + str(stamp).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, match[2])

def transcript_turns(call):
    turns = call.get('transcript_object')
    if isinstance(turns, list):
        return [(t.get('role'), text(t.get('content'), 20000)) for t in turns if isinstance(t, dict)]
    # Retell supplies Agent:/User: text in the standard call object.
    raw = text(call.get('transcript'), 100000)
    matches = list(re.finditer(r'(?im)^(Agent|User):\s*', raw))
    return [(m[1].lower(), raw[m.end():matches[i+1].start() if i+1 < len(matches) else len(raw)].strip()) for i,m in enumerate(matches)]

def consent_evidence(call, acceptance, start_turn=0):
    """Verify caller words follow an agent $99 disclosure. Intent still comes from LLM.

    This is evidence validation, not a replacement for semantic consent evaluation.
    Reject absent evidence, negation, and questions conservatively.
    """
    acceptance = text(acceptance, 300).lower()
    if not acceptance or '?' in acceptance:
        return False
    if re.search(r"\b(no|not|don't|do not|can't|cannot|maybe|wait|unsure)\b", acceptance):
        return False
    if not re.search(r"\b(yes|yeah|yep|okay|ok|fine|agree|accepted|sure|go ahead|sounds good|that's good|that works)\b", acceptance):
        return False
    disclosed = False
    for role, content in transcript_turns(call)[start_turn:]:
        if role == 'agent' and re.search(r'\b99\b|ninety[ -]nine', content, re.I):
            disclosed = True
        if disclosed and role == 'user' and acceptance in content.lower():
            if '?' in content or re.search(r"\b(no|not|don't|do not|can't|cannot|maybe|wait|unsure)\b",content,re.I):
                return False
            return True
    return False

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS calls(call_id TEXT PRIMARY KEY, data TEXT NOT NULL,
              revision INTEGER NOT NULL DEFAULT 1, event_rank INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY, call_id TEXT NOT NULL,
              details TEXT NOT NULL, route TEXT NOT NULL, valid INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS bookings(call_id TEXT PRIMARY KEY, quote_id TEXT NOT NULL,
              reference TEXT NOT NULL, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(call_id TEXT PRIMARY KEY, reference TEXT NOT NULL, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(call_id TEXT NOT NULL, event TEXT NOT NULL,
              PRIMARY KEY(call_id,event));
            CREATE TABLE IF NOT EXISTS outbox(call_id TEXT PRIMARY KEY, target_revision INTEGER NOT NULL,
              sent_revision INTEGER NOT NULL DEFAULT 0, telegram_message_id INTEGER, attempts INTEGER NOT NULL DEFAULT 0,
              next_attempt REAL NOT NULL DEFAULT 0, last_error TEXT);
            ''')

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def _merge(self, c, call_id, values, rank=None, notify=False):
        row = c.execute('SELECT * FROM calls WHERE call_id=?', (call_id,)).fetchone()
        old = json.loads(row['data']) if row else {'call_id': call_id}
        # Ignore unknown/empty analysis fields rather than erasing tool-confirmed facts.
        old.update({k:v for k,v in values.items() if v is not None and v != ''})
        rev = row['revision']+1 if row else 1
        event_rank = max(row['event_rank'] if row else 0, rank or 0)
        c.execute('INSERT INTO calls VALUES(?,?,?,?,?) ON CONFLICT(call_id) DO UPDATE SET data=excluded.data,revision=excluded.revision,event_rank=excluded.event_rank,updated=excluded.updated',
                  (call_id, json.dumps(old), rev, event_rank, time.time()))
        if notify:
            c.execute('INSERT INTO outbox(call_id,target_revision) VALUES(?,?) ON CONFLICT(call_id) DO UPDATE SET target_revision=excluded.target_revision,next_attempt=0', (call_id,rev))
        return old

    def prepare(self, call_id, args, call=None):
        if args.get('caller_type') != 'customer':
            raise RuleError('Only a customer repair request may enter booking.')
        if type(args.get('warranty_mentioned')) is not bool:
            raise RuleError('warranty_mentioned must be a boolean based on what the caller said.')
        details = {k:text(args.get(k)) for k in REQUIRED}
        details['notes'] = text(args.get('notes'))
        details['warranty_mentioned'] = args['warranty_mentioned']
        details['_quote_turn_count'] = len(transcript_turns(call or {}))
        missing = [k for k in REQUIRED if not details[k]]
        if missing:
            raise RuleError('Ask for the missing details: '+', '.join(missing))
        if not phone_ok(details['phone']):
            raise RuleError('Please confirm the callback phone number.')
        if args['warranty_mentioned'] and not warranty_supported(details['brand']):
            with self.db() as c:
                c.execute('UPDATE quotes SET valid=0 WHERE call_id=?',(call_id,))
                self._merge(c, call_id, {**details,'call_type':'message','outcome':'unsupported_warranty'})
            return {'success':False,'route':'message_only','reason':'Warranty work is only supported for LG, Samsung, and General Electric. Offer a message; do not book.'}
        route = 'eligible_warranty' if args['warranty_mentioned'] else 'standard'
        quote_id = 'quote_'+uuid.uuid4().hex
        with self.db() as c:
            if c.execute('SELECT 1 FROM bookings WHERE call_id=?',(call_id,)).fetchone():
                raise RuleError('This call already has a booking handoff. Take an amendment message instead.')
            c.execute('UPDATE quotes SET valid=0 WHERE call_id=?',(call_id,))
            c.execute('INSERT INTO quotes VALUES(?,?,?,?,1)',(quote_id,call_id,json.dumps(details),route))
            self._merge(c,call_id,{**{k:v for k,v in details.items() if not k.startswith('_')},'call_type':route,'outcome':'intake_complete','service_fee':0 if route=='eligible_warranty' else 99})
        return {'success':True,'quote_id':quote_id,'route':route,'service_fee':0 if route=='eligible_warranty' else 99,
                'requires_fee_agreement':route=='standard','appointment_confirmed':False}

    def book(self, call_id, args, call):
        quote_id = text(args.get('quote_id'),100)
        with self.db() as c:
            # Serialize checking and insertion for concurrent retries.
            c.execute('BEGIN IMMEDIATE')
            existing = c.execute('SELECT * FROM bookings WHERE call_id=?',(call_id,)).fetchone()
            if existing:
                if existing['quote_id'] != quote_id:
                    raise RuleError('A request already exists for this call. Take an amendment message.')
                return {'success':True,'reference':existing['reference'],'status':'handed_to_booking','appointment_confirmed':False,'duplicate':True}
            quote = c.execute('SELECT * FROM quotes WHERE id=? AND call_id=? AND valid=1',(quote_id,call_id)).fetchone()
            if not quote:
                raise RuleError('Quote is missing or superseded. Prepare booking again using the current details.')
            if quote['route']=='standard':
                if args.get('fee_accepted') is not True or not consent_evidence(call,args.get('acceptance_words'),json.loads(quote['details']).get('_quote_turn_count',0)):
                    raise RuleError('Do not book. Disclose the $99 service call fee and wait for explicit customer agreement.')
            reference = 'REQ-'+uuid.uuid4().hex[:8].upper()
            details = json.loads(quote['details'])
            c.execute('INSERT INTO bookings VALUES(?,?,?,?)',(call_id,quote_id,reference,quote['details']))
            self._merge(c,call_id,{'outcome':'handed_to_booking','booking_reference':reference,
                         'fee_accepted':quote['route']=='standard','appointment_confirmed':False})
        return {'success':True,'reference':reference,'status':'handed_to_booking','appointment_confirmed':False,
                'say':'Your repair request has been passed to booking.','service_fee':0 if quote['route']=='eligible_warranty' else 99}

    def message(self, call_id, args):
        kind = args.get('caller_type')
        if kind not in {'warranty_representative','message'}:
            raise RuleError('Messages are for relevant callers, not spam.')
        details={k:text(args.get(k)) for k in ['caller_name','company','callback_phone','job_description']}
        if not details['job_description']:
            raise RuleError('Ask what message should be passed to the team.')
        if kind=='warranty_representative' and not all(details.values()):
            raise RuleError('Collect the representative name, company, callback number, and job description.')
        if details['callback_phone'] and not phone_ok(details['callback_phone']):
            raise RuleError('Please confirm the callback number.')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT reference FROM messages WHERE call_id=?',(call_id,)).fetchone()
            ref=old['reference'] if old else 'MSG-'+uuid.uuid4().hex[:8].upper()
            c.execute('INSERT INTO messages VALUES(?,?,?) ON CONFLICT(call_id) DO UPDATE SET details=excluded.details',(call_id,ref,json.dumps(details)))
            c.execute('UPDATE quotes SET valid=0 WHERE call_id=?',(call_id,))
            self._merge(c,call_id,{**details,'call_type':kind,'outcome':'message_taken','message_reference':ref})
        return {'success':True,'reference':ref,'callback_possible':bool(details['callback_phone'])}

    def webhook(self, payload):
        event=payload.get('event')
        if event not in {'call_ended','call_analyzed'}:
            return {'accepted':True,'ignored':True}
        call=payload.get('call')
        if not isinstance(call,dict) or not text(call.get('call_id'),200):
            raise RuleError('Missing call ID.')
        call_id=call['call_id'];rank=2 if event=='call_analyzed' else 1
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM events WHERE call_id=? AND event=?',(call_id,event)).fetchone():
                return {'accepted':True,'duplicate':True}
            c.execute('INSERT INTO events VALUES(?,?)',(call_id,event))
            row=c.execute('SELECT * FROM calls WHERE call_id=?',(call_id,)).fetchone()
            if row and row['event_rank']>rank:
                return {'accepted':True,'stale':True}
            existing=json.loads(row['data']) if row else {}
            analysis=call.get('call_analysis') or {}
            extracted=analysis.get('custom_analysis_data') or {}
            if not isinstance(extracted,dict):extracted={}
            values={k:text(extracted.get(k)) for k in ['customer_name','caller_name','company','phone','callback_phone','service_address','appliance_type','brand','issue','job_description','notes']}
            kind=extracted.get('call_category')
            if not existing.get('call_type') and kind in KINDS:values['call_type']=kind
            # Tool-validated values take precedence over post-call model extraction.
            values={k:v for k,v in values.items() if not existing.get(k)}
            values.update({'call_status':text(call.get('call_status')),'disconnection_reason':text(call.get('disconnection_reason')),
                           'transcript':text(call.get('transcript'),100000),'analysis_ready':rank==2,
                           'summary':text(analysis.get('call_summary'),3000),'synthetic':bool(call.get('metadata',{}).get('synthetic',False))})
            values.setdefault('outcome',existing.get('outcome','call_ended_without_booking'))
            self._merge(c,call_id,values,rank=rank,notify=True)
        return {'accepted':True}

    def feed(self):
        with self.db() as c:
            rows=c.execute('SELECT c.*,o.sent_revision,o.target_revision,o.last_error FROM calls c LEFT JOIN outbox o USING(call_id) ORDER BY updated DESC LIMIT 200').fetchall()
            return [{**json.loads(r['data']),'updated':r['updated'],'notification_status':
                    ('delivered' if r['sent_revision'] and r['sent_revision']>=r['target_revision'] else 'pending') if r['target_revision'] else 'waiting_for_call_end',
                    'notification_error':r['last_error']} for r in rows]

    def pending(self):
        with self.db() as c:
            row=c.execute("SELECT o.*,c.data FROM outbox o JOIN calls c USING(call_id) WHERE sent_revision<target_revision AND COALESCE(json_extract(c.data, '$.synthetic'),0)=0 AND next_attempt<=? ORDER BY c.updated LIMIT 1",(time.time(),)).fetchone()
            return dict(row) if row else None

    def delivered(self,item,message_id):
        with self.db() as c:
            c.execute('UPDATE outbox SET sent_revision=?,telegram_message_id=?,attempts=0,last_error=NULL WHERE call_id=?',
                      (item['target_revision'],message_id,item['call_id']))

    def failed(self,item,error):
        with self.db() as c:
            attempts=item['attempts']+1
            c.execute('UPDATE outbox SET attempts=?,next_attempt=?,last_error=? WHERE call_id=?',
                      (attempts,time.time()+min(300,2**min(attempts,8)),error,item['call_id']))

def notification(data):
    kind=data.get('call_type','unknown').replace('_',' ').title()
    lines=[('DEMO • ' if data.get('synthetic') else '')+'Appliance repair call',kind,
           'Outcome: '+data.get('outcome','details pending').replace('_',' ')]
    fields=[('Caller',data.get('customer_name') or data.get('caller_name')),('Company',data.get('company') if data.get('call_type') not in {'standard','eligible_warranty'} else None),
            ('Callback',data.get('phone') or data.get('callback_phone')),('Address',data.get('service_address')),
            ('Appliance',data.get('appliance_type')),('Brand',data.get('brand')),('Issue',data.get('issue') or data.get('job_description')),
            ('Service call fee',('$'+str(data['service_fee'])) if 'service_fee' in data else None),
            ('Reference',data.get('booking_reference') or data.get('message_reference')),('Notes',data.get('notes'))]
    lines += [f'{label}: {value}' for label,value in fields if value]
    if data.get('summary'):lines+=['Summary: '+data['summary']]
    if not data.get('analysis_ready'):lines+=['Analysis pending; this notification will be updated.']
    lines+=['Call ID: '+data['call_id']]
    return '\n'.join(lines)[:4000]
