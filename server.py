#!/usr/bin/env python3
"""Small dependency-free demo backend. Bind locally or run behind an HTTPS gateway."""
import argparse
import hmac
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import Store, RuleError, text, verify_signature, notification

ROOT=Path(__file__).resolve().parent

def load_env():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key,value=line.split('=',1)
                os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

def telegram_request(token, method, data):
    request=urllib.request.Request('https://api.telegram.org/bot'+token+'/'+method,
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=25) as r:result=json.load(r)
    except urllib.error.HTTPError as e:
        # Do not let a secret-bearing request URL appear in logs or errors.
        if method=='editMessageText' and b'message is not modified' in e.read():return {'message_id':data['message_id']}
        raise RuntimeError('Telegram rejected delivery (HTTP '+str(e.code)+').') from None
    except Exception:
        raise RuntimeError('Telegram delivery is temporarily unavailable.') from None
    if not result.get('ok'):raise RuntimeError('Telegram did not accept the notification.')
    return result['result']

def notification_worker(store,stop):
    while not stop.wait(1):
        token=os.getenv('TELEGRAM_BOT_TOKEN');chat=os.getenv('TELEGRAM_CHAT_ID')
        if not token or not chat:continue
        item=store.pending()
        if not item:continue
        data=json.loads(item['data'])
        # Synthetic demonstrations never send messages to an external service.
        if data.get('synthetic'):
            continue
        body={'chat_id':chat,'text':notification(data)}
        if item['telegram_message_id']:
            body['message_id']=item['telegram_message_id'];method='editMessageText'
        else:method='sendMessage'
        try:
            result=telegram_request(token,method,body)
            store.delivered(item,result['message_id'])
        except Exception as e:
            store.failed(item,str(e))

class Handler(BaseHTTPRequestHandler):
    server_version='RepairDesk/1.0'
    def log_message(self,format,*args):
        # No bodies, tokens, transcript data, or request URLs in access logs.
        pass

    def respond(self,status,data,content_type='application/json; charset=utf-8'):
        raw=json.dumps(data).encode() if content_type.startswith('application/json') else data
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(raw)

    def dashboard_auth(self):
        value=self.headers.get('Authorization','')
        return bool(self.server.dashboard_token) and hmac.compare_digest(value,'Bearer '+self.server.dashboard_token)

    def reviewer_auth(self):
        token=os.getenv('REVIEW_TOKEN','')
        return bool(token) and hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)

    def do_GET(self):
        route=urllib.parse.urlparse(self.path).path
        if route=='/health':return self.respond(200,{'status':'ok'})
        if route in {'/','/app.js','/style.css'}:
            filename={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[route]
            mime={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[route]
            return self.respond(200,(ROOT/'static'/filename).read_bytes(),mime)
        reviewer=self.reviewer_auth()
        if not self.dashboard_auth() and not reviewer:return self.respond(401,{'error':'Enter the dashboard access key.'})
        if route=='/api/calls':
            calls=self.server.store.feed()
            if reviewer:
                since=float(os.getenv('REVIEW_SINCE','0'))
                calls=[c for c in calls if c['updated']>=since and not c.get('synthetic')]
            return self.respond(200,{'calls':calls})
        if route=='/api/status':return self.respond(200,{'retell_ready':bool(os.getenv('RETELL_API_KEY') and os.getenv('RETELL_AGENT_ID')),
            'telegram_ready':bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID')),
            'booking_mode':'request_handoff','voice_tested':False})
        return self.respond(404,{'error':'Not found.'})

    def do_POST(self):
        route=urllib.parse.urlparse(self.path).path
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>2_000_000:return self.respond(413,{'error':'Invalid request size.'})
            raw=self.rfile.read(length)
            if route.startswith('/tools/') or route=='/webhooks/retell':
                if not verify_signature(raw,os.getenv('RETELL_API_KEY',''),self.headers.get('X-Retell-Signature','')):
                    return self.respond(401,{'error':'Invalid webhook signature.'})
                if route.startswith('/tools/'):
                    expected=os.getenv('TOOL_TOKEN','')
                    if not expected or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+expected):
                        return self.respond(401,{'error':'Invalid tool authorization.'})
            elif not self.dashboard_auth():return self.respond(401,{'error':'Unauthorized.'})
            payload=json.loads(raw)
            if not isinstance(payload,dict):raise RuleError('Expected a JSON object.')
            if route=='/webhooks/retell':return self.respond(200,self.server.store.webhook(payload))
            if route.startswith('/tools/'):
                call=payload.get('call',{})
                args=payload.get('args',{})
                if not isinstance(call,dict) or not isinstance(args,dict):raise RuleError('Invalid call or tool arguments.')
                call_id=text(call.get('call_id'),200)
                if not call_id:raise RuleError('Tool requires a trusted Retell call ID.')
                if route=='/tools/prepare_booking':result=self.server.store.prepare(call_id,args,call)
                elif route=='/tools/book_repair':result=self.server.store.book(call_id,args,call)
                elif route=='/tools/take_message':result=self.server.store.message(call_id,args)
                else:return self.respond(404,{'error':'Unknown tool.'})
                return self.respond(200,result)
            return self.respond(404,{'error':'Not found.'})
        except (RuleError,ValueError,UnicodeDecodeError) as e:
            # A tool rejection is a valid result the model must handle, not a transport retry.
            return self.respond(200 if route.startswith('/tools/') else 400,{'success':False,'error':str(e),'appointment_confirmed':False})
        except Exception:
            return self.respond(500,{'success':False,'error':'Request could not be confirmed. Do not claim success.'})

class Server(ThreadingHTTPServer):
    daemon_threads=True

if __name__=='__main__':
    load_env()
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=int(os.getenv('PORT','8765')))
    parser.add_argument('--host',default=os.getenv('HOST','127.0.0.1'))
    args=parser.parse_args()
    token=os.getenv('DASHBOARD_TOKEN','')
    if not token:
        if args.host not in {'127.0.0.1','localhost'}:
            raise SystemExit('Set DASHBOARD_TOKEN before exposing the server.')
        keyfile=ROOT/'runtime'/'dashboard-key.txt';keyfile.parent.mkdir(exist_ok=True)
        token=keyfile.read_text().strip() if keyfile.exists() else secrets.token_urlsafe(32)
        keyfile.write_text(token);keyfile.chmod(0o600)
        print('Local access key saved to runtime/dashboard-key.txt. It is not included in submission archives.')
    store=Store(ROOT/'runtime'/'calls.sqlite3')
    server=Server((args.host,args.port),Handler)
    server.store=store;server.dashboard_token=token
    stop=threading.Event()
    threading.Thread(target=notification_worker,args=(store,stop),daemon=True).start()
    print(f'Call feed: http://{args.host}:{args.port} — booking mode: request handoff')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close()
