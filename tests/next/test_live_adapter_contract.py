"""Real HTTP adapter calls against a controlled local service; not live MT."""
import asyncio
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import re
import threading
import pytest
from linguanova_next.adapters.config_view import ConfigView
from linguanova_next.adapters.provider_adapter import ProviderAdapter
from linguanova_next.contracts.entry import Occurrence
from linguanova_next.dictionary.term_protection import protect_terms,restore_terms,contains_term
from linguanova_next.linguistic.profile_validator import validate


@pytest.fixture
def http_provider():
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):return
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append(payload)
            content=[text.replace('Open ','Ouvrir ').replace('Hello','Bonjour') for text in payload['q']]
            body=json.dumps({'translatedText':content}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:yield 'http://127.0.0.1:'+str(server.server_port),requests
    finally:server.shutdown();server.server_close();worker.join(timeout=5)


def test_provider_configuration_implements_public_text_api(services,project):
    view=ConfigView(services.create_job(project))
    assert view.get_ui_text('test','Message {value}')=='Message {value}'
    assert view.get_log_text('test','Log')=='Log'
    with pytest.raises(TypeError):view.translation_settings.target_language='fr'


def test_real_http_request_preserves_syntax_and_approved_dictionary(services,project,http_provider):
    endpoint,requests=http_provider
    job=services.create_job(project,'fr',provider='libretranslate',glossary={'Preferences':'Réglages'},options={'endpoint':endpoint})
    entry=Occurrence.create('script.rpy',10,'Open Preferences [player_name].','say','dialogue','source')
    async def execute():
        provider=ProviderAdapter(job)
        try:return await provider.translate(entry)
        finally:await provider.close()
    candidate=asyncio.run(execute())
    assert candidate.text=='Ouvrir Réglages [player_name].'
    assert validate(job,entry.original,candidate.text,entry.context).accepted
    assert len(requests)==1 and requests[0]['target']=='fr' and requests[0]['source']=='auto'
    assert requests[0]['format']=='html'
    assert 'Preferences' not in requests[0]['q'][0]


def test_dictionary_protection_obeys_word_boundaries_and_token_integrity():
    original='Rosemary sees Rose, [Rose] and {color=Rose}.'
    protected,mapping=protect_terms(original,{'Rose':'Rosa'})
    assert 'Rosemary' in protected and '[Rose]' in protected and '{color=Rose}' in protected
    assert len(mapping)==1
    assert restore_terms(protected,mapping)=='Rosemary sees Rosa, [Rose] and {color=Rose}.'
    assert not contains_term('Rosemary [Rose] {color=Rose}','Rose')
    with pytest.raises(ValueError,match='alteró'):restore_terms('provider dropped token',mapping)
