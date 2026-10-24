from ..contracts.entry import Occurrence
from ..util import digest


class ModAdapter:
    """Independent scanner, no classic generator/hook/queue/cache calls."""
    def extract(self, game):
        from src.ui_mod.scanner import ModProjectScanner
        report=ModProjectScanner().scan(str(game))
        entries=[]
        for c in report.candidates:
            entries.append(Occurrence.create(c.file_path,c.line_number,c.text,c.screen,'ui',digest([c.file_path,c.text]),
                                             provenance='isolated_mod_scanner',publishable=c.confidence=='high'))
        diagnostics=[{'status':'mod_scanner_warning','cause':x} for x in report.parse_errors]
        if report.skipped_compiled_files:
            diagnostics.append({'status':'compiled_unverified','count':report.skipped_compiled_files})
        return list({o.occurrence_id:o for o in entries}.values()),diagnostics
