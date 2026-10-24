"""Opt-in live Google probe. Sends one synthetic sentence, no game content."""
import asyncio
from pathlib import Path
import argparse
import json
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from linguanova_next.bootstrap import Services
from linguanova_next.adapters.provider_adapter import ProviderAdapter
from linguanova_next.contracts.entry import Occurrence
from linguanova_next.linguistic.profile_validator import validate
from linguanova_next.util import atomic_json,jsonable


async def probe(output):
    with tempfile.TemporaryDirectory(prefix='linguanova-live-') as temporary:
        root=Path(temporary);game=root/'project/game';game.mkdir(parents=True)
        (game/'script.rpy').write_text('label start:\n    "Welcome to the village."\n    return\n',encoding='utf-8')
        service=Services(data=root/'state')
        job=service.create_job(game.parent,'fr',provider='google',source='en')
        adapter=ProviderAdapter(job)
        statuses=[]
        adapter.set_status_callback(lambda level,message:statuses.append({'level':level,'message':service.diagnostics.redact(message)}))
        start=time.monotonic()
        result={'provider':'google','source':'en','target':'fr','fixture':'one synthetic public sentence','executed':True}
        try:
            entry=Occurrence.create('script.rpy',2,'Welcome to the village.','say','dialogue','probe')
            candidate=await asyncio.wait_for(adapter.translate(entry),timeout=35)
            verdict=validate(job,entry.original,candidate.text,entry.context)
            result.update(status='accepted' if verdict.accepted else 'rejected',candidate=jsonable(candidate),validation=jsonable(verdict))
        except Exception as exc:
            result.update(status='failed',exception=type(exc).__name__,reason=str(exc)[:500])
        finally:
            try:await adapter.close()
            except Exception as exc:result['close_error']=str(exc)
        result.update(seconds=round(time.monotonic()-start,2),provider_statuses=statuses)
        atomic_json(output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return result['status']=='accepted'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(probe(args.output)) else 1)
