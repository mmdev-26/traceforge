"""Validate agent trace trees, distinguish wall time from exclusive time and diff paired runs."""
from collections import defaultdict
import hashlib,json,math

def summarize(spans):
    if not isinstance(spans,list) or not spans:raise ValueError('spans must be a non-empty list')
    by_id={};warnings=[]
    for s in spans:
        sid=s['id']
        if not isinstance(sid,str) or not sid or sid in by_id:raise ValueError('Span IDs must be unique non-empty strings')
        for k in ['startMs','endMs']:
            if not isinstance(s.get(k),(int,float)) or not math.isfinite(s[k]):raise ValueError('Span timestamps must be finite numbers')
        if s['endMs']<s['startMs']:raise ValueError('Span ends before it starts: '+sid)
        for k in ['inputTokens','outputTokens','cost']:
            v=s.get(k,0)
            if not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError(k+' must be nonnegative and finite')
        by_id[sid]=s
    children=defaultdict(list);roots=[]
    for s in spans:
        parent=s.get('parentId')
        if parent is None:roots.append(s['id'])
        elif parent not in by_id:raise ValueError('Missing parent: '+str(parent))
        else:
            children[parent].append(s['id']);p=by_id[parent]
            if s['startMs']<p['startMs'] or s['endMs']>p['endMs']:raise ValueError('Child span outside parent bounds: '+s['id'])
    visiting=set();visited=set()
    def visit(sid):
        if sid in visiting:raise ValueError('Trace contains a parent cycle')
        if sid in visited:return
        visiting.add(sid)
        for child in children[sid]:visit(child)
        visiting.remove(sid);visited.add(sid)
    for sid in by_id:visit(sid)
    def union(intervals):
        merged=[]
        for a,b in sorted(intervals):
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
            else:merged.append((a,b))
        return sum(b-a for a,b in merged)
    details=[];by_name=defaultdict(lambda:{'calls':0,'durationMs':0,'exclusiveMs':0,'errors':0,'cost':0})
    for sid,s in by_id.items():
        duration=s['endMs']-s['startMs'];exclusive=duration-union([(by_id[x]['startMs'],by_id[x]['endMs']) for x in children[sid]])
        name=s.get('name',sid);item={'id':sid,'name':name,'parentId':s.get('parentId'),'durationMs':duration,'exclusiveMs':exclusive,'status':s.get('status','ok'),'cost':s.get('cost',0)};details.append(item)
        g=by_name[name];g['calls']+=1;g['durationMs']+=duration;g['exclusiveMs']+=exclusive;g['errors']+=item['status']=='error';g['cost']+=item['cost']
        if s.get('status')=='error':warnings.append({'severity':'error','code':'span_error','spanId':sid,'detail':s.get('error','Span reported an error')})
    start=min(s['startMs'] for s in spans);end=max(s['endMs'] for s in spans)
    return {'summary':{'spans':len(spans),'wallMs':end-start,'errors':sum(s.get('status')=='error' for s in spans),'cost':sum(s.get('cost',0) for s in spans),'inputTokens':sum(s.get('inputTokens',0) for s in spans),'outputTokens':sum(s.get('outputTokens',0) for s in spans)},'roots':roots,'spans':details,'byName':dict(by_name),'findings':warnings}

def analyze(data):
    current=summarize(data['spans']);result={'product':'TraceForge','version':'0.1.0',**current}
    if 'baseline' in data:
        old=summarize(data['baseline']);result['comparison']={k:{'before':old['summary'][k],'after':current['summary'][k],'delta':current['summary'][k]-old['summary'][k]} for k in ['wallMs','errors','cost','inputTokens','outputTokens']}
    result['provenance']={'inputSha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()}
    result['limitations']=['Analyzes recorded spans only; does not execute or replay agent tools.','Cost and tokens are additive per-span values: provide usage only on the owning span, not repeated aggregate parent totals.','Exclusive time subtracts the union of immediate-child intervals, so overlapping child work is not double-counted.']
    return result
