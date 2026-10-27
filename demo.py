#!/usr/bin/env python3
"""Populate only the local feed with clearly marked synthetic calls. No network calls."""
from pathlib import Path
from core import Store

ROOT=Path(__file__).resolve().parent

def populate(store):
    samples=[('demo-standard',{'call_category':'standard','customer_name':'Jordan Ellis','phone':'+1 202-555-0142','service_address':'125 Example Street, Arlington, VA 22201','appliance_type':'refrigerator','brand':'Whirlpool','issue':'Not cooling'},'Customer requested refrigerator repair. The $99 fee was accepted; no appointment time was confirmed.'),
      ('demo-warranty',{'call_category':'eligible_warranty','customer_name':'Taylor Morgan','phone':'+1 202-555-0116','service_address':'42 Sample Avenue, Arlington, VA 22201','appliance_type':'washer','brand':'LG','issue':'Not draining; caller mentioned warranty'},'Customer mentioned an LG warranty. No service call fee applies to this request.'),
      ('demo-representative',{'call_category':'warranty_representative','caller_name':'Casey Lee','company':'American Home Shield','callback_phone':'+1 202-555-0173','job_description':'Assigning a dryer repair request'},'Warranty company representative left a job message. No booking was made.'),
      ('demo-spam',{'call_category':'spam'},'Unrelated sales call. Agent declined politely and ended the call.')]
    for call_id,data,summary in samples:
        if data['call_category'] in {'standard','eligible_warranty'}:
            args={k:data[k] for k in ['customer_name','phone','service_address','appliance_type','brand','issue']}
            args.update({'caller_type':'customer','warranty_mentioned':data['call_category']=='eligible_warranty','notes':''})
            try:
                quote=store.prepare(call_id,args)
                evidence={'transcript':'Agent: The service call fee is ninety-nine dollars. Is that okay?\nUser: Yes, that works.'}
                store.book(call_id,{'quote_id':quote['quote_id'],'fee_accepted':data['call_category']=='standard','acceptance_words':'Yes, that works.'},evidence)
            except ValueError:
                pass  # Re-running fixtures preserves an existing synthetic handoff.
        elif data['call_category']=='warranty_representative':
            store.message(call_id,{'caller_type':'warranty_representative',**{k:data[k] for k in ['caller_name','company','callback_phone','job_description']}})
        store.webhook({'event':'call_analyzed','call':{'call_id':call_id,'call_status':'ended','metadata':{'synthetic':True},'call_analysis':{'custom_analysis_data':data,'call_summary':summary}}})
    return len(samples)

if __name__=='__main__':
    print(f'Added {populate(Store(ROOT/"runtime"/"calls.sqlite3"))} synthetic examples to the local feed. Nothing sent to Telegram.')
