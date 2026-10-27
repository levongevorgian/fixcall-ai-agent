'use strict';
let accessKey=sessionStorage.getItem('repair-desk-key')||'',calls=[],filter='all';
const el=id=>document.getElementById(id);
function node(tag,cls,value){const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;}
function render(){
  el('total').textContent=calls.length;
  el('requests').textContent=calls.filter(c=>c.booking_reference).length;
  el('messages').textContent=calls.filter(c=>c.message_reference).length;
  const feed=el('feed');feed.replaceChildren();
  for(const call of calls.filter(c=>filter==='all'||c.call_type===filter)){
    const card=node('article','card'),top=node('div','card-top'),left=node('div');
    left.append(node('div','category',(call.call_type||'Unclassified').replaceAll('_',' ')));
    const title=node('h2','',call.customer_name||call.caller_name||(call.call_type==='spam'?'Unrelated caller':'Caller details not collected'));
    if(call.synthetic)title.append(node('span','demo','SYNTHETIC DEMO'));
    left.append(title,node('span','status',(call.outcome||'In progress').replaceAll('_',' ')));
    top.append(left,node('span','status',new Date(call.updated*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})));card.append(top);
    const details=node('div','details');
    const fields=[['Callback',call.phone||call.callback_phone],['Appliance',[call.brand,call.appliance_type].filter(Boolean).join(' ')],['Service call fee',call.service_fee===undefined?'':`$${call.service_fee}`],['Service address',call.service_address],['Issue / message',call.issue||call.job_description],['Company',call.company],['Reference',call.booking_reference||call.message_reference],['Notes',call.notes]];
    for(const [label,value]of fields){if(!value)continue;const f=node('div','field');f.append(node('small','',label),node('div','',String(value)));details.append(f);}card.append(details);
    if(call.summary)card.append(node('p','summary',call.summary));
    const delivery=call.synthetic?'Local demo only':`Telegram: ${(call.notification_status||'pending').replaceAll('_',' ')}`;
    card.append(node('p','status',delivery+(call.notification_error?' · '+call.notification_error:'')));
    if(call.transcript){const d=node('details'),s=node('summary','','Read conversation');d.append(s,node('pre','',call.transcript));card.append(d);}
    feed.append(card);
  }
  if(!feed.children.length){const d=node('div','empty');d.append(node('h2','','No calls in this view'),node('p','','Completed calls appear here automatically.'));feed.append(d);}
}
async function request(path){const r=await fetch(path,{headers:{Authorization:`Bearer ${accessKey}`}});if(!r.ok)throw new Error(r.status===401?'Access key not accepted.':'The feed is temporarily unavailable.');return r.json();}
async function refresh(){if(!accessKey)return;try{const [feed,status]=await Promise.all([request('/api/calls'),request('/api/status')]);calls=feed.calls;render();el('login').hidden=true;el('error').hidden=true;el('connection').textContent='Feed connected';el('delivery').textContent=status.telegram_ready?'Configured':'Not connected';el('updated').textContent='Updated '+new Date().toLocaleTimeString();}catch(e){el('error').textContent=e.message;el('error').hidden=false;el('connection').textContent='Not connected';el('login').hidden=false;}}
el('login-form').addEventListener('submit',e=>{e.preventDefault();accessKey=el('key').value.trim();sessionStorage.setItem('repair-desk-key',accessKey);el('key').value='';refresh();});
el('refresh').addEventListener('click',refresh);
el('disconnect').addEventListener('click',()=>{sessionStorage.removeItem('repair-desk-key');accessKey='';calls=[];render();el('login').hidden=false;el('connection').textContent='Disconnected';});
for(const b of document.querySelectorAll('[data-filter]'))b.addEventListener('click',()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));render();});
refresh();setInterval(refresh,5000);
