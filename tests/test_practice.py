import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Implementacion/app'))

def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

startup = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'APP_SECRET':'A'*48,'SCIM_TOKEN':'B'*48,'DEVICE_TOKEN':'C'*48,'CARD_PEPPER':'D'*48,'APP_BASE_URL':'https://lab.example.test','OIDC_CLIENT_ID':'fixture','OIDC_CLIENT_SECRET':'fixture','OIDC_METADATA_URL':'https://idp.example.test/.well-known/openid-configuration','APP_DB':str(Path(startup.name)/'startup.sqlite'),'NVR_BASE_URL':''}):
    web = module('webapp','Implementacion/app/app.py')
hr = module('hr','Areas/RRHH/solicitudes.py')
soc = module('soc','Areas/SOC/linea_tiempo.py')
evidence = module('evidence','Areas/Auditoria/evidencias.py')
runtime = module('runtime','Areas/TI/preparar_runtime.py')

class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        web.store = web.Store(Path(self.temp.name)/'app.sqlite')
        self.client = web.app.test_client()
        self.headers = {'Authorization':'Bearer '+'B'*48}

    def tearDown(self):self.temp.cleanup()

    def account(self, role='mantenimiento'):
        return web.store.save({'userName':'ingeniero@example.test','externalId':'LAB-INGENIERO','title':role,'active':True})

    def session(self, user):
        with self.client.session_transaction() as s:s.update(uid=user['id'],csrf='fixture-csrf')

    def test_scim_requires_token(self):
        self.assertEqual(self.client.get('/scim/v1/Users').status_code,401)

    def test_scim_create_and_duplicate(self):
        payload={'userName':'ingeniero@example.test','title':'mantenimiento','active':True}
        self.assertEqual(self.client.post('/scim/v1/Users',json=payload,headers=self.headers).status_code,201)
        self.assertEqual(self.client.post('/scim/v1/Users',json=payload,headers=self.headers).status_code,409)

    def test_bad_scim_payload_rejected(self):
        self.assertEqual(self.client.post('/scim/v1/Users',json=['bad'],headers=self.headers).status_code,400)
        malformed=self.client.post('/scim/v2/Users',data='not-json',content_type='application/scim+json',headers=self.headers)
        self.assertEqual(malformed.status_code,400)
        self.assertEqual(malformed.json['schemas'],['urn:ietf:params:scim:api:messages:2.0:Error'])
        user=self.account()
        for payload in [[], {'Operations':'bad'}, {'Operations':['bad']}]:
            self.assertEqual(self.client.patch('/scim/v1/Users/'+user['id'],json=payload,headers=self.headers).status_code,400)

    def test_filter_returns_only_requested_user(self):
        self.account()
        r=self.client.get('/scim/v1/Users',query_string={'filter':'userName eq "ingeniero@example.test"'},headers=self.headers)
        self.assertEqual(r.json['totalResults'],1)

    def test_maintenance_changes_persistent_resource(self):
        self.session(self.account())
        r=self.client.post('/mantenimiento',data={'csrf':'fixture-csrf'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['maintenance_runs'],'1')
        self.assertEqual(web.Store(web.store.path).state()['maintenance_runs'],'1')

    def test_auditor_cannot_change_resource(self):
        self.session(self.account('auditor'))
        for path in ['/mantenimiento','/admin']:
            self.assertEqual(self.client.post(path,data={'csrf':'fixture-csrf','mode':'maintenance'}).status_code,403)
        self.assertEqual(web.store.state()['mode'],'ready')

    def test_admin_mode_changes_persistently(self):
        self.session(self.account('admin'))
        r=self.client.post('/admin',data={'csrf':'fixture-csrf','mode':'maintenance'})
        self.assertEqual(r.json['mode'],'maintenance')

    def test_invalid_mode_rejected(self):
        self.session(self.account('admin'))
        self.assertEqual(self.client.post('/admin',data={'csrf':'fixture-csrf','mode':'shell-command'}).status_code,400)

    def test_csrf_blocks_mutation(self):
        self.session(self.account())
        self.assertEqual(self.client.post('/mantenimiento',data={'csrf':'wrong'}).status_code,400)
        self.assertEqual(web.store.state()['maintenance_runs'],'0')

    def test_inactive_account_blocks_old_session(self):
        user=self.account();self.session(user)
        self.client.patch('/scim/v1/Users/'+user['id'],json={'active':False},headers=self.headers)
        self.assertEqual(self.client.post('/mantenimiento',data={'csrf':'fixture-csrf'}).status_code,403)

    def test_change_role_blocks_old_permission(self):
        user=self.account();self.session(user)
        self.client.patch('/scim/v1/Users/'+user['id'],json={'title':'auditor'},headers=self.headers)
        self.assertEqual(self.client.post('/mantenimiento',data={'csrf':'fixture-csrf'}).status_code,403)

    def test_deletion_preserves_identity_in_audit(self):
        user=self.account();self.session(user)
        self.assertEqual(self.client.delete('/scim/v1/Users/'+user['id'],headers=self.headers).status_code,204)
        self.assertEqual(self.client.get('/consulta').status_code,403)
        deletion=next(e for e in web.store.events() if e['action']=='SCIM_DELETE')
        self.assertEqual(deletion['employee'],'LAB-INGENIERO')

    def test_soc_reads_hub_without_admin_access(self):
        self.session(self.account('soc'))
        self.assertEqual(self.client.get('/hub').status_code,200)
        self.assertEqual(self.client.post('/admin',data={'csrf':'fixture-csrf','mode':'maintenance'}).status_code,403)

    def test_callback_requires_provisioned_identity(self):
        with patch.object(web.oauth.identity,'authorize_access_token',return_value={'userinfo':{'sub':'fixture-sub','email':'unknown@example.test'}}):
            self.assertEqual(self.client.get('/auth/callback').status_code,403)

    def test_callback_binds_subject_and_refuses_rebinding(self):
        self.account()
        with patch.object(web.oauth.identity,'authorize_access_token',return_value={'userinfo':{'sub':'fixture-sub','email':'ingeniero@example.test'}}):
            self.assertEqual(self.client.get('/auth/callback').status_code,302)
        with patch.object(web.oauth.identity,'authorize_access_token',return_value={'userinfo':{'sub':'other-sub','email':'ingeniero@example.test'}}):
            self.assertEqual(self.client.get('/auth/callback').status_code,403)

    def test_authentik_login_screen_uses_configured_provider_name(self):
        response=self.client.get('/')
        self.assertIn(b'Continuar con authentik',response.data)

    def test_scim_v2_create_list_and_get(self):
        payload={'schemas':['urn:ietf:params:scim:schemas:core:2.0:User'],'userName':'ingeniero@example.test','externalId':'EMP-001','title':'mantenimiento','active':True}
        created=self.client.post('/scim/v2/Users',json=payload,headers=self.headers)
        self.assertEqual(created.status_code,201)
        self.assertEqual(created.json['schemas'],['urn:ietf:params:scim:schemas:core:2.0:User'])
        self.assertTrue(created.headers['Location'].endswith('/scim/v2/Users/'+created.json['id']))
        listed=self.client.get('/scim/v2/Users?filter=userName%20eq%20%22ingeniero%40example.test%22',headers=self.headers)
        self.assertEqual(listed.status_code,200)
        self.assertEqual(listed.json['Resources'][0]['externalId'],'EMP-001')
        by_employee=self.client.get('/scim/v2/Users?filter=externalId%20eq%20%22EMP-001%22',headers=self.headers)
        self.assertEqual(by_employee.json['totalResults'],1)
        fetched=self.client.get('/scim/v2/Users/'+created.json['id'],headers=self.headers)
        self.assertEqual(fetched.json['title'],'mantenimiento')
        self.assertEqual(fetched.mimetype,'application/scim+json')

    def test_scim_v2_rejects_missing_schema_and_supports_discovery(self):
        invalid=self.client.post('/scim/v2/Users',json={'userName':'ingeniero@example.test'},headers=self.headers)
        self.assertEqual(invalid.status_code,400)
        self.assertEqual(invalid.json['schemas'],['urn:ietf:params:scim:api:messages:2.0:Error'])
        config=self.client.get('/scim/v2/ServiceProviderConfig',headers=self.headers)
        self.assertTrue(config.json['patch']['supported'])
        self.assertEqual(self.client.get('/scim/v2/ResourceTypes',headers=self.headers).json['totalResults'],1)
        self.assertEqual(self.client.get('/scim/v2/Schemas',headers=self.headers).json['totalResults'],1)

    def test_scim_v2_put_replaces_attributes_and_demotes_missing_role(self):
        payload={'schemas':['urn:ietf:params:scim:schemas:core:2.0:User'],'userName':'ingeniero@example.test','title':'mantenimiento','active':True}
        created=self.client.post('/scim/v2/Users',json=payload,headers=self.headers)
        user_id=created.json['id']
        replacement={'schemas':['urn:ietf:params:scim:schemas:core:2.0:User'],'userName':'ingeniero@example.test','active':True}
        updated=self.client.put('/scim/v2/Users/'+user_id,json=replacement,headers=self.headers)
        self.assertEqual(updated.status_code,200)
        self.assertNotIn('title',updated.json)
        self.assertFalse(web.store.permitted(user_id,'mantenimiento'))

    def test_scim_v2_errors_require_token(self):
        response=self.client.get('/scim/v2/ServiceProviderConfig')
        self.assertEqual(response.status_code,401)

    def test_device_api_requires_separate_token(self):
        payload={'reader':'PUERTA-01','credential':'A1B2C3D4','movement':'ENTRADA','result':'PERMITIDO'}
        self.assertEqual(self.client.post('/api/v1/access-events',json=payload).status_code,401)
        response=self.client.post('/api/v1/access-events',json=payload,headers={'Authorization':'Bearer '+'C'*48})
        self.assertEqual(response.status_code,201)
        stored=self.client.get('/api/v1/access-events',headers={'Authorization':'Bearer '+'C'*48}).json[0]['credential']
        self.assertNotEqual(stored,'A1B2C3D4')
        self.assertEqual(len(stored),12)

    def test_admin_can_render_operational_console(self):
        self.session(self.account('admin'))
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Security Hub',response.data)
        self.assertEqual(response.headers['X-Frame-Options'],'DENY')

    def test_unassigned_role_cannot_view_operational_console(self):
        self.session(self.account('sin_acceso'))
        self.assertEqual(self.client.get('/').status_code, 403)

    def test_ti_changes_role_and_security_registers_card(self):
        ti=self.account('ti');employee=web.store.save({'userName':'persona@example.test','externalId':'LAB-021','title':'consulta','active':True})
        self.session(ti)
        response=self.client.post('/usuarios/'+employee['id']+'/rol',data={'csrf':'fixture-csrf','role':'soc'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(web.store.permitted(employee['id'],'incidentes'))
        self.assertIn(b'LAB-021', self.client.get('/control-acceso').data)
        response=self.client.post('/tarjetas',data={'csrf':'fixture-csrf','uid':'A1 B2 C3 D4','label':'TARJETA-021','user_id':employee['id']})
        self.assertEqual(response.status_code,302)
        self.assertEqual(web.store.cards()[0]['employee'],'LAB-021')
        decision=self.client.post('/api/v1/access/check',json={'uid':'A1B2C3D4','reader':'PUERTA-01','movement':'ENTRADA'},headers={'Authorization':'Bearer '+'C'*48})
        self.assertTrue(decision.json['allowed'])

    def test_soc_cannot_change_roles(self):
        soc=self.account('soc');employee=web.store.save({'userName':'otra@example.test','externalId':'LAB-022','title':'consulta','active':True})
        self.session(soc)
        self.assertEqual(self.client.post('/usuarios/'+employee['id']+'/rol',data={'csrf':'fixture-csrf','role':'admin'}).status_code,403)

class OperationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_request_self_approval_blocked(self):
        store=hr.Requests(self.path/'hr.sqlite');req=store.create('PUESTO-004','LAB-INGENIERO','alta','aplicacion','mantenimiento')
        with self.assertRaises(ValueError):store.approve(req['id'],'PUESTO-004','TI')

    def test_wrong_owner_approval_blocked(self):
        store=hr.Requests(self.path/'hr.sqlite');req=store.create('PUESTO-004','LAB-INGENIERO','alta','aplicacion','mantenimiento')
        with self.assertRaises(ValueError):store.approve(req['id'],'PUESTO-014','IAM')

    def test_request_closes_only_after_approval(self):
        store=hr.Requests(self.path/'hr.sqlite');req=store.create('PUESTO-004','LAB-INGENIERO','alta','aplicacion','mantenimiento')
        with self.assertRaises(ValueError):store.close(req['id'],'PUESTO-008','EVIDENCIA-01')
        store.approve(req['id'],'PUESTO-008','TI')
        self.assertEqual(store.close(req['id'],'PUESTO-011','EVIDENCIA-01')['estado'],'implementada')

    def test_timeline_correlates_and_sorts_utc(self):
        rfid=self.path/'rfid.csv';app=self.path/'events.json'
        rfid.write_text('hora_utc,empleado,movimiento,resultado\n2026-01-01T10:00:00+00:00,LAB-INGENIERO,ENTRADA,PERMITIDO\n')
        app.write_text(json.dumps([{'time':'2026-01-01T09:01:00-01:00','employee':'LAB-INGENIERO','action':'LOGIN','result':'OK'}]))
        rows=soc.collect(rfid,app,'LAB-INGENIERO')
        self.assertEqual([r['source'] for r in rows],['RFID','Aplicación'])

    def test_timeline_rejects_missing_timezone(self):
        with self.assertRaises(ValueError):soc.utc('2026-01-01T10:00:00')

    def test_timeline_escapes_html(self):
        result=soc.render([{'time':'now','identity':'<script>','source':'RFID','action':'ENTRADA','result':'OK'}])
        self.assertNotIn('<script>',result);self.assertIn('&lt;script&gt;',result)

    def test_manifest_changes_if_evidence_changes(self):
        file=self.path/'evidence.txt';file.write_text('first');before=evidence.manifest(self.path)
        file.write_text('second');after=evidence.manifest(self.path)
        self.assertNotEqual(before[0]['sha256'],after[0]['sha256'])

    def test_runtime_refuses_repository_destination(self):
        with self.assertRaises(ValueError):runtime.prepare(ROOT/'private-runtime')

if __name__=='__main__':unittest.main()
