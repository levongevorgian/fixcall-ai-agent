#!/usr/bin/env python3
"""Connect the existing Retell draft after an approved HTTPS backend is running."""
import json,os,urllib.parse,urllib.request
from pathlib import Path
from configure import api,tools,analysis_fields
from server import ROOT,load_env

def main():
    load_env()
    agent_id=os.getenv('RETELL_AGENT_ID','')
    base=os.getenv('PUBLIC_BASE_URL','').rstrip('/')
    token=os.getenv('TOOL_TOKEN','')
    parsed=urllib.parse.urlparse(base)
    if not agent_id or not token or not os.getenv('RETELL_API_KEY'):
        raise SystemExit('Set the existing agent ID and local credentials first.')
    if parsed.scheme!='https' or not parsed.netloc:
        raise SystemExit('An approved, reachable HTTPS backend URL is required before connecting.')
    try:
        with urllib.request.urlopen(base+'/health',timeout=15) as r:
            healthy=r.status==200 and json.load(r).get('status')=='ok'
    except Exception:healthy=False
    if not healthy:raise SystemExit('The public backend health check failed. No Retell changes made.')
    agent=api('GET','/get-agent/'+urllib.parse.quote(agent_id,safe=''))
    if agent.get('is_published'):
        raise SystemExit('This helper updates an unpublished assessment draft only.')
    engine=agent.get('response_engine',{})
    if engine.get('type')!='retell-llm':raise SystemExit('The selected agent must use a Retell LLM.')
    llm_id=engine['llm_id']
    llm=api('GET','/get-retell-llm/'+urllib.parse.quote(llm_id,safe=''))
    private=ROOT/'runtime';private.mkdir(exist_ok=True)
    backup=private/'before-connect.json'
    if not backup.exists():
        backup.write_text(json.dumps({'agent':agent,'llm':llm},indent=2));backup.chmod(0o600)
    # Preserve the user's voice/model choices and the manually pasted prompt.
    api('PATCH','/update-retell-llm/'+urllib.parse.quote(llm_id,safe=''),{
        'general_tools':tools(base,token),
        'general_prompt':(ROOT/'agent'/'prompt.md').read_text(),
        'begin_message':'Thanks for calling appliance repair. How can I help?',
        'start_speaker':'agent'})
    api('PATCH','/update-agent/'+urllib.parse.quote(agent_id,safe=''),{
        'agent_name':'Appliance Repair — Levon Demo',
        'boosted_keywords':['LG','Samsung','General Electric','GE','Whirlpool','American Home Shield'],
        'webhook_url':base+'/webhooks/retell',
        'webhook_events':['call_ended','call_analyzed'],
        'post_call_analysis_data':analysis_fields()})
    result=api('GET','/get-retell-llm/'+urllib.parse.quote(llm_id,safe=''))
    expected={'prepare_booking','book_repair','take_message','end_call'}
    actual={t.get('name') for t in result.get('general_tools',[])}
    if not expected.issubset(actual):raise SystemExit('Readback verification failed; inspect the saved draft.')
    print('Existing draft connected and tool configuration verified. No calls placed; voice quality remains untested.')

if __name__=='__main__':main()
