"""Versioned process protocol; stdout is JSONL and GPU imports stay here."""
import json
import os
import sys
from pathlib import Path
from ..contracts.worker_protocol import WorkerMessage
from ..util import jsonable, load_json, atomic_json


def worker_main(request_path):
    request=load_json(request_path)
    request_id=request.get('request_id','')
    def emit(kind,payload):
        print(json.dumps(jsonable(WorkerMessage(request_id,kind,payload))),flush=True)
    try:
        WorkerMessage(**request).validate(request_id)
        payload=request['payload']
        from PIL import Image
        from ..models.model_manifest import verify_model
        from ..adapters.generative_inpainting_adapter import DiffusersInpaintingAdapter
        verify_model(payload['model_directory'],payload['model_manifest'])
        with Image.open(payload['image']) as original, Image.open(payload['mask']) as mask:
            result=DiffusersInpaintingAdapter().restore(original.convert('RGBA'),mask.convert('L'),payload['model_directory'],
                payload['parameters'],progress=lambda n,total:emit('progress',{'current':n,'total':total}))
            result.save(payload['output'],format='PNG')
        emit('result',{'output':payload['output'],'revision':payload['model_manifest']['revision']})
        return 0
    except Exception as exc:
        emit('error',{'type':type(exc).__name__,'message':str(exc)[:500]})
        return 1
