"""Run against a temporary studio server: python tests/check_http.py URL."""
import json
import sys
import urllib.request
import urllib.error
base=sys.argv[1]
def post(route, data):
    req=urllib.request.Request(base+'/api/'+route,json.dumps(data).encode(),{'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as r:return json.load(r)
with urllib.request.urlopen(base) as r:assert r.status==200
sample={'template_name':'HTTP test','parameters':[], 'suggested_tasks':[{'title':'Implement','description':'Build feature','acceptance':'Tests pass','tool':''}]}
saved=post('save',{'document':sample})
assert post('validate',{'document':sample})=={'errors':[]}
release=post('publish',saved)
assert post('release',{**release,'values':{}})['suggested_tasks']==sample['suggested_tasks']
assert post('preview',{'document':sample})['template_name']=='HTTP test'
assert len(post('import',{'content':'## First\nBody\n### Child\nDetails'})['suggested_tasks'])==1
try:post('publish',{'id':saved['id'],'revision':0})
except urllib.error.HTTPError as e:assert e.code==400
else:raise AssertionError('Stale revision accepted')
print('HTTP checks passed: static page, save, validate, publish, release, preview, import, stale revision')
