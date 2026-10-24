def require_preferences_only(result,complete=False):
    if not result.get('preferences_only') or result.get('forbidden') or not result.get('persistence_implemented'):
        raise ValueError('Native UI acceptance blocked: verified Preferences slot and zero generated shortcuts required')
    if complete and (result.get('visual_review')!='verified' or result.get('persistence_review')!='verified'):
        raise ValueError('Native visual/persistence execution evidence is pending')
    return result
