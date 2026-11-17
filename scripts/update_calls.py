#!/usr/bin/env python3
"""Refresh secondary-source CFP candidates. No deletion or claim of official verification."""
import argparse, copy, datetime as dt, json, os, re, tempfile, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SLUGS = {
 'A':'transportation-research-part-a-policy-and-practice-09658564',
 'B':'transportation-research-part-b-methodological-01912615',
 'C':'transportation-research-part-c-emerging-technologies-0968090x',
 'D':'transportation-research-part-d-transport-and-environment-13619209',
 'E':'transportation-research-part-e-logistics-and-transportation-review-13665545',
 'F':'transportation-research-part-f-traffic-psychology-and-behaviour-13698478'}
SOURCES = {p:'https://journalcompass.com/en/journals/'+s+'.html' for p,s in SLUGS.items()}
VERIFY = '转载源自动采集，尚未完成出版社详情页核验'

class CallsParser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.rows=[]; self.row=None; self.in_title=False
 def handle_starttag(self, tag, attrs):
  a=dict(attrs)
  if tag=='li' and 'call-row' in a.get('class','').split():
   if self.row is not None: raise ValueError('nested call-row')
   self.row={'title':'','url':'','deadline':''}
  if self.row is not None:
   if tag=='a': self.in_title=True; self.row['url']=a.get('href','')
   if tag=='time': self.row['deadline']=a.get('datetime','')
 def handle_data(self,data):
  if self.row is not None and self.in_title:self.row['title']+=data
 def handle_endtag(self,tag):
  if tag=='a':self.in_title=False
  if tag=='li' and self.row is not None:
   self.rows.append(self.row);self.row=None

def parse_calls(html):
 if 'Special issues open for submissions' not in html or 'calls-list' not in html:
  raise ValueError('expected CFP section missing (blocked or changed page)')
 p=CallsParser();p.feed(html)
 if not p.rows:raise ValueError('empty CFP list needs manual verification; preserving old records')
 if len(p.rows)>100:raise ValueError('unexpected count')
 seen=set()
 for r in p.rows:
  r['title']=' '.join(r['title'].split())
  u=urlparse(r['url'])
  if u.scheme!='https' or u.hostname!='www.sciencedirect.com' or not u.path.startswith('/special-issue/'):
   raise ValueError('unexpected destination')
  if not r['title'] or len(r['title'])>600:raise ValueError('invalid title')
  if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['deadline']):raise ValueError('invalid deadline')
  dt.date.fromisoformat(r['deadline'])
  if r['url'] in seen:raise ValueError('duplicate URL')
  seen.add(r['url'])
 return p.rows

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'PartCFPTracker/1.0 (academic call-for-papers monitor)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read(3_000_001)
  if len(raw)>3_000_000:raise ValueError('response too large')
  return raw.decode('utf-8')

def due(data,now,force=False):
 if force:return True
 last=data.get('refresh',{}).get('last_success_at')
 if not last:return True
 try:return (now-dt.datetime.fromisoformat(last.replace('Z','+00:00'))).total_seconds()>=10*86400
 except (ValueError,TypeError):return True

def update(data,now,fetcher=fetch):
 out=copy.deepcopy(data); rows=out.setdefault('records',[]); stamp=now.isoformat(); day=now.date().isoformat()
 by_url={r['url']:r for r in rows}; reports={}; failures=[]
 for part,url in SOURCES.items():
  try:
   candidates=parse_calls(fetcher(url)); present=set()
   for item in candidates:
    present.add(item['url']); old=by_url.get(item['url'])
    if old is None:
     old={'part':part,'title':item['title'],'english':item['title'],'deadline':item['deadline'],'url':item['url'],'note':''}
     rows.append(old);by_url[item['url']]=old
    if old.get('part')!=part:raise ValueError('journal mismatch for existing URL')
    history=old.setdefault('deadline_observations',[])
    observation={'date':item['deadline'],'source':url}
    if not any(x.get('date')==item['deadline'] and x.get('source')==url for x in history):history.append(dict(observation,observed_at=stamp))
    # Never silently replace a conflicting earlier deadline.
    old['reported_deadline']=item['deadline']
    old['deadline_conflict']=old.get('deadline')!=item['deadline'] or bool(old.get('deadline_conflict'))
    old['english']=item['title'];old['source_url']=url;old['source_checked_at']=stamp
    old['verification']=VERIFY;old['source_status']='listed';old['last_seen_at']=stamp
   for old in rows:
    if old.get('part')==part and old['url'] not in present:old['source_status']='not_listed_unconfirmed'
   reports[part]={'status':'ok','count':len(candidates),'source':url,'checked_at':stamp}
  except Exception as e:
   # Restore this journal's old records on any fetch/parse/merge failure.
   rows[:]=[r for r in rows if r.get('part')!=part]+copy.deepcopy([r for r in data.get('records',[]) if r.get('part')==part])
   by_url={r['url']:r for r in rows}
   failures.append(part);reports[part]={'status':'failed','source':url,'error':str(e)[:300],'attempted_at':stamp}
 refresh=out.setdefault('refresh',{});refresh.update(last_attempt_at=stamp,sources=reports,status='partial_failure' if failures else 'success',interval_days=10)
 if not failures:refresh['last_success_at']=stamp;out['checked_at']=day
 out['coverage_notice']='自动更新转载目录中的候选征稿，不保证完整覆盖；出版社通知为最终依据。未出现的条目不会自动判定为结束征稿。'
 return out,failures

def atomic_write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def main():
 a=argparse.ArgumentParser();a.add_argument('--file',default='data.json');a.add_argument('--force',action='store_true');args=a.parse_args()
 data=json.loads(Path(args.file).read_text());now=dt.datetime.now(dt.timezone.utc)
 if not due(data,now,args.force):print('Not due; keeping existing data.');return 0
 new,errors=update(data,now);atomic_write(args.file,new)
 print(json.dumps({'status':new['refresh']['status'],'records':len(new['records']),'failed_parts':errors}))
 return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
