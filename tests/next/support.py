"""Controlled provider and fixtures: these are NEVER live-provider evidence."""
from pathlib import Path
import shutil
import uuid
from linguanova_next.contracts.entry import Candidate

TARGETS=[('es','latam_neutro_sin_modismos'),('es','espana_estandar_sin_modismos'),('fr',None),('pt',None),('ru',None),('en',None)]
TRANSLATIONS={
 'Start':['Iniciar','Empezar','Commencer','Iniciar','Начать','Begin'],
 'Preferences':['Preferencias','Preferencias','Préférences','Preferências','Настройки','Settings'],
 'Quit':['Salir','Salir','Quitter','Sair','Выйти','Exit'],
 'Return':['Volver','Volver','Retour','Voltar','Назад','Back'],
 'Continue':['Continuar','Continuar','Continuer','Continuar','Продолжить','Proceed'],
 'Welcome to our quiet village.':['Te damos la bienvenida a nuestro tranquilo pueblo.','Te damos la bienvenida a nuestro tranquilo pueblo.','Bienvenue dans notre paisible village.','Bem-vindo à nossa tranquila aldeia.','Добро пожаловать в нашу тихую деревню.','Welcome to this peaceful village.'],
 'Hello [player_name], this is a controlled test.':['Hola [player_name], esta es una prueba controlada.','Hola [player_name], esta es una prueba controlada.','Bonjour [player_name], ceci est un test contrôlé.','Olá [player_name], este é um teste controlado.','Привет, [player_name], это контролируемый тест.','Hi [player_name], this is a controlled demonstration.'],
}


class FixtureProvider:
    calls=[]
    def __init__(self,job,provider_id=None):
        self.job=job;self.provider_id=provider_id or job.provider_id;self.model='controlled-dictionary-v1'
    async def translate(self,entry,source_language=None,attempt=1):
        self.calls.append((self.job.target_identity,entry.original,source_language,attempt,self.provider_id))
        index=[('es','es-419'),('es','es-ES'),('fr','fr'),('pt','pt'),('ru','ru'),('en','en')].index((self.job.target_language_id,self.job.target_locale))
        text=TRANSLATIONS.get(entry.original,[entry.original]*6)[index]
        return Candidate(entry.occurrence_id,text,'fixture_dictionary',self.model,source_language or self.job.source_mode,uuid.uuid4().hex,self.job.identity,attempt)
    async def close(self):pass


def copy_fixture(tmp_path):
    root=Path(__file__).resolve().parents[2]
    dest=tmp_path/'Juego con espacios y acentos áé'
    shutil.copytree(root/'next_fixtures/native_slot_game',dest,ignore=shutil.ignore_patterns('*.rpyc','cache','saves','log.txt','traceback.txt','errors.txt'))
    return dest
