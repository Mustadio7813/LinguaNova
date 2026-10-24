"""Creator-only import of explicit observations, never a translation source."""
from ..util import load_json


def read_observations(path, job):
    data=load_json(path,{})
    if data.get('job_identity')!=job.identity:
        raise ValueError('Observation does not belong to this job')
    return {'observed':sorted(set(data.get('observed',[]))),
            'unverified':sorted(set(data.get('unverified',[]))), 'kind':'creator_observation'}
