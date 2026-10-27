#!/usr/bin/env python3
"""Generate inspectable Retell payloads; optionally create the agent in your account."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from server import ROOT,load_env

def string(description):return {'type':'string','description':description}

def schema(properties, required):
    return {'type':'object','properties':properties,'required':required,'additionalProperties':False}

def tools(base,token):
    properties={k:string(v) for k,v in {
      'appliance_type':'Appliance requiring repair, as stated by caller.',
      'issue':'Symptoms reported by caller. Do not diagnose.',
      'brand':'Brand stated by caller. GE means General Electric.',
      'customer_name':'Customer full name.',
      'phone':'Confirmed callback phone number; do not assume caller ID is preferred.',
      'service_address':'Full service address including city, state, ZIP, and unit if applicable.',
      'notes':'Additional volunteered information; empty string when absent.'}.items()}
    properties.update({'caller_type':{'type':'string','enum':['customer']},
                       'warranty_mentioned':{'type':'boolean','description':'True only if customer has mentioned warranty; do not ask every caller.'}})
    definitions=[('prepare_booking','Validate complete customer intake and determine the fee before booking. No scheduling occurs.',schema(properties,list(properties))),
       ('book_repair','Hand the validated repair request to booking. Standard customers must first hear and explicitly accept $99. Warranty customers need no fee agreement.',schema({
         'quote_id':string('Latest quote_id returned by prepare_booking for the current details.'),
         'fee_accepted':{'type':'boolean','description':'True only after explicit standard-fee agreement; false for warranty.'},
         'acceptance_words':string('Exact short affirmative words spoken by customer after hearing $99; empty for warranty.')},['quote_id','fee_accepted','acceptance_words'])),
       ('take_message','Save a relevant caller message. Warranty company representatives never enter booking.',schema({
         'caller_type':{'type':'string','enum':['warranty_representative','message']},
         'caller_name':string('Name, or empty if a non-representative refuses.'),
         'company':string('Warranty company name; empty for ordinary callers.'),
         'callback_phone':string('Confirmed callback number; empty only if an ordinary caller refuses.'),
         'job_description':string('Job/message details, including amendments or references when relevant.')},['caller_type','caller_name','company','callback_phone','job_description']))]
    result=[]
    for name,description,parameters in definitions:
        result.append({'type':'custom','name':name,'description':description,'url':base+'/tools/'+name,
          'method':'POST','headers':{'Authorization':'Bearer '+token},'parameters':parameters,
          'speak_during_execution':False,'speak_after_execution':True,'timeout_ms':8000,'args_at_root':False})
    result.append({'type':'end_call','name':'end_call','description':'End after a natural goodbye, or immediately after rejecting spam.'})
    return result

def analysis_fields():
    fields=[{'type':'enum','name':'call_category','description':'Classify caller purpose based on the actual conversation. Customer brand alone does not imply warranty.',
             'choices':['standard','eligible_warranty','warranty_representative','message','spam','unknown']}]
    for name in ['customer_name','caller_name','company','phone','callback_phone','service_address','appliance_type','brand','issue','job_description','notes']:
        fields.append({'type':'string','name':name,'description':f'Extract {name.replace("_"," ")} only when explicitly provided. Empty string if missing. Never invent details, coverage, dates, or outcomes.'})
    for field in fields:
        if field['name']=='company':
            field['description']='The company represented by a business caller, only when explicitly stated. Empty for ordinary repair customers, including warranty customers. Never use the appliance brand or the called repair business as company.'
        elif field['name']=='issue':
            field['description']='Describe the appliance symptom in clear words using the whole conversation. Resolve obvious transcription ambiguity from context (for example, will not drain). Do not diagnose or invent symptoms.'
    return fields

def payloads(base,voice,token,llm_id='REPLACE_WITH_CREATED_LLM_ID'):
    llm={'model':'gpt-4.1','model_temperature':0.2,'start_speaker':'agent',
         'begin_message':'Thanks for calling appliance repair. How can I help?',
         'general_prompt':(ROOT/'agent'/'prompt.md').read_text(),'general_tools':tools(base,token)}
    agent={'agent_name':'Appliance Repair — Levon Demo','response_engine':{'type':'retell-llm','llm_id':llm_id},
           'boosted_keywords':['LG','Samsung','General Electric','GE','Whirlpool','American Home Shield'],
           'voice_id':voice,'language':'en-US','voice_speed':0.97,
           'responsiveness':0.8,'interruption_sensitivity':0.75,'enable_backchannel':False,
           'reminder_trigger_ms':12000,'reminder_max_count':1,
           'max_call_duration_ms':900000,'end_call_after_silence_ms':45000,
           'webhook_url':base+'/webhooks/retell','webhook_events':['call_ended','call_analyzed'],
           'post_call_analysis_data':analysis_fields()}
    return llm,agent

def api(method,path,payload=None):
    request=urllib.request.Request('https://api.retellai.com'+path,
       data=None if payload is None else json.dumps(payload).encode(),
       headers={'Authorization':'Bearer '+os.environ['RETELL_API_KEY'],'Content-Type':'application/json'},method=method)
    try:
        with urllib.request.urlopen(request,timeout=30) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        # API errors may echo configuration containing tokens. Keep them off stdout.
        raise SystemExit(f'Retell rejected {path} (HTTP {e.code}). Inspect the payload fields against the current Retell docs; secrets are not printed.') from None
    except Exception:
        raise SystemExit('Could not reach Retell. Check network access and retry.') from None

def main():
    load_env()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['export','voices','create','status'])
    args=parser.parse_args()
    if args.action in {'voices','create','status'} and not os.getenv('RETELL_API_KEY'):
        raise SystemExit('Add RETELL_API_KEY to your local .env first.')
    if args.action=='voices':
        voices=api('GET','/list-voices')
        for v in voices:
            if str(v.get('gender','')).lower()=='female':
                print(json.dumps({k:v.get(k) for k in ['voice_id','voice_name','provider','accent','gender','preview_audio_url']}))
        return
    if args.action=='status':
        if not os.getenv('RETELL_AGENT_ID'):raise SystemExit('No RETELL_AGENT_ID configured.')
        a=api('GET','/get-agent/'+urllib.parse.quote(os.environ['RETELL_AGENT_ID'],safe=''))
        print(json.dumps({k:a.get(k) for k in ['agent_id','agent_name','voice_id','is_published','version']},indent=2));return
    base=os.getenv('PUBLIC_BASE_URL','https://YOUR_PUBLIC_HTTPS_HOST').rstrip('/')
    voice=os.getenv('RETELL_VOICE_ID','SELECT_FEMALE_VOICE_FROM_ACCOUNT')
    token=os.getenv('TOOL_TOKEN','LOCAL_TOOL_TOKEN_NOT_YET_CONFIGURED')
    llm,agent=payloads(base,voice,token)
    if args.action=='export':
        # Always sanitize authorization values in distributable payloads.
        llm,_=payloads(base,voice,'REPLACE_WITH_LOCAL_TOOL_TOKEN')
        (ROOT/'agent'/'retell-llm.template.json').write_text(json.dumps(llm,indent=2))
        (ROOT/'agent'/'retell-agent.template.json').write_text(json.dumps(agent,indent=2))
        print('Sanitized templates saved under agent/. These are API payloads, not dashboard import bundles.');return
    parsed=urllib.parse.urlparse(base)
    if parsed.scheme!='https' or not parsed.netloc or 'YOUR_' in base:raise SystemExit('Set PUBLIC_BASE_URL to the working public HTTPS backend URL.')
    if 'SELECT_' in voice or not os.getenv('TOOL_TOKEN'):raise SystemExit('Choose RETELL_VOICE_ID and set TOOL_TOKEN first.')
    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
    marker=runtime/'retell-created.json'
    if marker.exists():raise SystemExit('A Retell resource marker already exists. Reuse the existing agent rather than creating duplicates.')
    # Store each created resource before taking the next step, for recoverable partial setup.
    llm_result=api('POST','/create-retell-llm',llm)
    state={'llm_id':llm_result['llm_id']};marker.write_text(json.dumps(state,indent=2));marker.chmod(0o600)
    _,agent=payloads(base,voice,token,llm_result['llm_id'])
    result=api('POST','/create-agent',agent)
    state['agent_id']=result['agent_id'];marker.write_text(json.dumps(state,indent=2))
    print('Created agent '+result['agent_id']+'. Add it as RETELL_AGENT_ID in .env. Test it in the Retell dashboard before publishing.')

if __name__=='__main__':main()
