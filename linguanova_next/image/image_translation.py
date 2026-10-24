async def translate_regions(bridge, resource, regions):
    """All images go through the same job-bound translation service."""
    result=[]
    for region in regions:
        request=bridge.request(resource,region)
        result.append(await bridge.translate(request))
    return result
