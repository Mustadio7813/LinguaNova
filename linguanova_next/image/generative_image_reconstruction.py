"""Cancelable external worker. Frozen sys.executable is never treated as Python."""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from ..util import atomic_json, load_json, file_hash
from ..contracts.worker_protocol import WorkerMessage
from ..core.work_queue import CancelledJob


async def restore_in_worker(original_path,mask_path,directory,model_directory,manifest,parameters,queue,emit=None):
    request_id=uuid.uuid4().hex
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    request_path=directory/(request_id+'.request.json')
    output=directory/(request_id+'.background.png')
    payload={'image':str(Path(original_path).resolve()),'mask':str(Path(mask_path).resolve()),
             'output':str(output.resolve()),'model_directory':str(Path(model_directory).resolve()),
             'model_manifest':manifest,'parameters':parameters}
    atomic_json(request_path,WorkerMessage(request_id,'request',payload))
    if getattr(sys,'frozen',False):
        if parameters.get('worker_manifest'):
            component=load_json(parameters['worker_manifest'])
        else:
            from ..models.component_installation import ComponentInstallation
            component=ComponentInstallation().resolve('inference')
        if not component or component.get('protocol_version')!=1:
            raise RuntimeError('Frozen creator requires a separately built inference worker component')
        worker=Path(component['executable'])
        if file_hash(worker)!=component['sha256']:
            raise ValueError('Inference worker hash mismatch')
        command=[str(worker),'--worker',str(request_path.resolve())]
    else:
        command=[sys.executable,'-m','linguanova_next.worker_main','--worker',str(request_path.resolve())]
    environment=os.environ.copy();environment['HF_HUB_OFFLINE']='1';environment['TRANSFORMERS_OFFLINE']='1'
    child=await asyncio.create_subprocess_exec(*command,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,env=environment)
    try:
        async def consume():
            result=None
            async for line in child.stdout:
                try:
                    message=WorkerMessage(**json.loads(line))
                except (ValueError,TypeError):
                    continue
                message.validate(request_id)
                queue.check()
                if emit: emit(message.kind,message.payload)
                if message.kind=='error': raise RuntimeError('Generative inference failed: '+message.payload.get('type','unknown'))
                if message.kind=='result': result=message.payload
            code=await child.wait()
            if code or not result or result['output']!=str(output.resolve()) or not output.exists():
                raise RuntimeError('Inference worker did not produce a correlated result')
            return output
        result=await queue.call(consume,timeout=float(parameters.get('timeout',1800)))
        queue.check()
        return result
    finally:
        if child.returncode is None:
            child.kill();await child.wait()
