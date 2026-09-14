from api.seed_content import make_cases
from api.providers import local_candidate
c=make_cases()[1]; st=c['characters'][0]['statements']
qs=['案发时你在哪里？','你观察到了什么异常？','录音笔是谁给你的？','为什么这么晚还在巡查？']
for q in qs: print(q, local_candidate(q,st,{}))
