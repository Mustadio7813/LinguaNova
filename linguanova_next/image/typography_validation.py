from .font_resolver import resolve_font


def validate_typography(game, profile, text):
    profile.validate()
    font=resolve_font(game,profile,text)
    return {'font_path':str(font),'font_hash':profile.font_hash,'profile_identity':profile.identity,
            'fidelity':'verified_identity' if profile.evidence=='identified' else profile.evidence,
            'reviewer':profile.reviewer,'in_game_visual_review':'not_executed'}
