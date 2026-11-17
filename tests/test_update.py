import datetime as dt,sys,unittest
sys.path.insert(0,'scripts')
from update_calls import *
H='<title>Transportation Research Part A Policy and Practice</title>Special issues open for submissions<ul class="calls-list"><li class="call-row"><a href="https://www.sciencedirect.com/special-issue/123/test">Title &amp; more</a><time datetime="2027-01-01"></time></li></ul>'
NOW=dt.datetime(2026,11,17,tzinfo=dt.timezone.utc)
class Tests(unittest.TestCase):
 def test_parse(self):self.assertEqual(parse_calls(H)[0]['title'],'Title & more')
 def test_fake200(self):
  with self.assertRaises(ValueError):parse_calls('<html>Site Unavailable</html>')
 def test_empty(self):
  with self.assertRaises(ValueError):parse_calls('Special issues open for submissions <ul class="calls-list"></ul>')
 def test_bad_destination(self):
  with self.assertRaises(ValueError):parse_calls(H.replace('www.sciencedirect.com','evil.test'))
 def test_bad_date(self):
  with self.assertRaises(ValueError):parse_calls(H.replace('2027-01-01','2027-02-31'))
 def test_due(self):
  d={'refresh':{'last_success_at':(NOW-dt.timedelta(days=9)).isoformat()}}
  self.assertFalse(due(d,NOW));self.assertTrue(due(d,NOW+dt.timedelta(days=1)));self.assertTrue(due(d,NOW,True))
 def test_exact_240_hour_gate(self):
  d={'refresh':{'last_success_at':'2026-11-17T04:14:00+00:00'}}
  self.assertFalse(due(d,dt.datetime(2026,11,27,1,17,tzinfo=dt.timezone.utc)))
  self.assertTrue(due(d,dt.datetime(2026,11,27,4,17,tzinfo=dt.timezone.utc)))
  self.assertFalse(due(d,dt.datetime(2026,11,26,1,17,tzinfo=dt.timezone.utc)))
 def test_truncated_row(self):
  with self.assertRaises(ValueError):parse_calls(H.replace('</li>',''))
 def test_wrong_journal(self):
  with self.assertRaises(ValueError):parse_calls(H,'B')
 def test_details_preserved(self):
  details={'scope_summary':'curated','checked_at':'2026-11-16','sources':[{'url':'https://example.org'}]}
  data={'records':[{'part':'A','url':'https://www.sciencedirect.com/special-issue/123/test','deadline':'2027-01-01','note':'期限冲突保留','details':details}]}
  out,_=update(data,NOW,lambda u:H if u==SOURCES['A'] else 'Unavailable')
  r=out['records'][0];self.assertEqual(r['details'],details);self.assertTrue(r['deadline_conflict'])
 def test_omission_not_closed(self):
  data={'records':[{'part':'A','url':'https://www.sciencedirect.com/special-issue/456/old','deadline':'2027-01-01','note':''}]}
  out,_=update(data,NOW,lambda u:H if u==SOURCES['A'] else 'Unavailable')
  old=[r for r in out['records'] if r['url'].endswith('/old')][0]
  self.assertEqual(old['source_status'],'not_listed_unconfirmed')
 def test_failure_preserves(self):
  data={'checked_at':'2026-11-16','records':[{'part':'A','url':'old','deadline':'2026-11-30','note':'conflict'}]}
  out,errors=update(data,NOW,lambda _: '<html>Site Unavailable</html>')
  self.assertEqual(len(errors),6);self.assertEqual(out['records'],data['records']);self.assertEqual(out['checked_at'],data['checked_at']);self.assertNotIn('last_success_at',out['refresh'])
 def test_conflict_preserves(self):
  data={'records':[{'part':'A','url':'https://www.sciencedirect.com/special-issue/123/test','deadline':'2026-12-01','note':'existing warning'}]}
  def f(url):return H if url==SOURCES['A'] else '<html>Unavailable</html>'
  out,errors=update(data,NOW,f);r=out['records'][0]
  self.assertEqual(r['deadline'],'2026-12-01');self.assertEqual(r['reported_deadline'],'2027-01-01');self.assertTrue(r['deadline_conflict']);self.assertEqual(r['note'],'existing warning')
if __name__=='__main__':unittest.main()
