"""Hardware is probed on demand in the optional worker, never during imports."""
import importlib.util


def capability_report():
    if not importlib.util.find_spec('torch') or not importlib.util.find_spec('diffusers'):
        return {'available':False,'reason':'Install the separate inference worker/runtime', 'devices':[]}
    import torch
    devices=['cpu']
    if torch.cuda.is_available():
        devices.insert(0,'cuda')
    return {'available':True,'devices':devices,'cuda':torch.version.cuda,'torch':torch.__version__,
            'cuda_free_bytes':torch.cuda.mem_get_info()[0] if torch.cuda.is_available() else 0,
            'validation':'experimental; this machine must complete an inference check'}


def require_compatible(parameters):
    info=capability_report()
    if not info['available']:
        raise RuntimeError(info['reason'])
    from importlib.metadata import version
    from .model_registry import selected_manifest
    for package,expected in selected_manifest()['runtime'].items():
        if version(package).split('+')[0]!=expected:
            raise RuntimeError('Worker runtime version mismatch: '+package+' expected '+expected)
    device=parameters.get('device','cuda')
    if device not in info['devices']:
        raise RuntimeError('Requested accelerator unavailable')
    if not parameters.get('allow_unverified_hardware',False):
        raise RuntimeError('Inference on this hardware is unverified; explicitly enable experimental inference')
    if device=='cuda' and info['cuda_free_bytes']<8*1024**3:
        raise RuntimeError('CUDA budget below experimental 8 GiB admission limit; use classical reconstruction')
    return device
