"""Aplicación de práctica: OIDC y aprovisionamiento SCIM 2.0.
No incluye acceso alternativo con contraseña local.
"""
import hmac
import os
import re
import secrets
import sqlite3
from datetime import timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, abort, jsonify, redirect, render_template, request, session
from authlib.integrations.flask_client import OAuth
from store import PERMISSIONS, Store
from urllib.parse import urlsplit
from werkzeug.middleware.proxy_fix import ProxyFix

APP_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(APP_DIR / 'templates'), static_folder=str(APP_DIR / 'static'))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.environ['APP_SECRET']
BASE = os.environ['APP_BASE_URL'].rstrip('/')
SCIM_TOKEN = os.environ['SCIM_TOKEN']
OIDC_PROVIDER_NAME = os.environ.get('OIDC_PROVIDER_NAME', 'authentik').strip() or 'proveedor institucional'
DEVICE_TOKEN = os.environ['DEVICE_TOKEN']
CARD_PEPPER = os.environ['CARD_PEPPER']
if min(len(app.secret_key), len(SCIM_TOKEN), len(DEVICE_TOKEN), len(CARD_PEPPER)) < 32 or not BASE.startswith('https://'):
    raise RuntimeError('Configura secretos de al menos 32 caracteres y APP_BASE_URL HTTPS')
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(minutes=15), MAX_CONTENT_LENGTH=65536)
store = Store(os.environ.get('APP_DB', 'data/lab.sqlite'))
oauth = OAuth(app)
oauth.register(name='identity', client_id=os.environ['OIDC_CLIENT_ID'], client_secret=os.environ['OIDC_CLIENT_SECRET'], server_metadata_url=os.environ['OIDC_METADATA_URL'], client_kwargs={'scope': 'openid profile email'})
camera_url = os.environ.get('NVR_BASE_URL', '')
if camera_url:
    parsed = urlsplit(camera_url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError('NVR_BASE_URL debe ser HTTPS sin credenciales')


@app.after_request
def security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cache-Control'] = 'no-store'
    if request.path.startswith('/scim/v2/') and response.is_json:
        response.mimetype = 'application/scim+json'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


SCIM_V1_SCHEMA = 'urn:scim:schemas:core:1.0'
SCIM_V2_SCHEMA = 'urn:ietf:params:scim:schemas:core:2.0'
SCIM_V2_ERROR_SCHEMA = 'urn:ietf:params:scim:api:messages:2.0:Error'


def scim_v2_request():
    return '/scim/v2/' in request.path


def error(message, status):
    if scim_v2_request():
        return jsonify({'schemas': [SCIM_V2_ERROR_SCHEMA], 'detail': message, 'status': str(status)}), status
    return jsonify({'schemas': [SCIM_V1_SCHEMA], 'detail': message, 'status': str(status)}), status


def format_user_resource(user):
    """Return the wire representation for the active SCIM protocol version."""
    if not scim_v2_request():
        return user
    result = dict(user)
    result['schemas'] = [SCIM_V2_SCHEMA + ':User']
    result['meta'] = dict(result.get('meta') or {})
    result['meta'].update({
        'resourceType': 'User',
        'location': BASE + '/scim/v2/Users/' + result['id'],
    })
    return result


def list_response(resources, start, count):
    page = resources[start - 1:start - 1 + count]
    if scim_v2_request():
        return jsonify({
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
            'totalResults': len(resources), 'startIndex': start,
            'itemsPerPage': len(page), 'Resources': [format_user_resource(item) for item in page],
        })
    return jsonify({
        'schemas': [SCIM_V1_SCHEMA], 'totalResults': len(resources),
        'startIndex': start, 'itemsPerPage': len(page), 'Resources': page,
    })


def scim_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if not hmac.compare_digest(token, 'Bearer ' + SCIM_TOKEN):
            return error('No autorizado', 401)
        return fn(*args, **kwargs)
    return wrapped


def device_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not hmac.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + DEVICE_TOKEN):
            return jsonify({'error': 'No autorizado'}), 401
        return fn(*args, **kwargs)
    return wrapped


def allowed(action):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            uid = session.get('uid')
            if not uid:
                return redirect('/login')
            if not store.permitted(uid, action):
                store.event(uid, action, 'DENEGADO')
                abort(403)
            if request.method == 'POST' and not hmac.compare_digest(request.form.get('csrf', ''), session.get('csrf', '')):
                abort(400)
            store.event(uid, action, 'PERMITIDO')
            return fn(*args, **kwargs)
        return wrapped
    return decorator


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@app.get('/')
def home():
    uid = session.get('uid')
    user = store.get(uid) if uid else None
    if user and not user.get('active', False):
        session.clear()
        user = None
    if not user:
        return render_template('login.html', idp_name=OIDC_PROVIDER_NAME)
    if not store.permitted(uid, 'consulta'):
        store.event(uid, 'DASHBOARD', 'DENEGADO')
        abort(403)
    session.setdefault('csrf', secrets.token_urlsafe(32))
    return render_template('dashboard.html', user=user, idp_name=OIDC_PROVIDER_NAME, current_role=store.effective_role(uid), csrf=session['csrf'], metrics=store.dashboard(),
                           devices=store.devices(), access_events=store.access_events(12),
                           incidents=store.incidents(), state=store.state(), camera_url=camera_url)


@app.get('/login')
def login():
    return oauth.identity.authorize_redirect(BASE + '/auth/callback', prompt='login')


@app.get('/auth/callback')
def callback():
    try:
        token = oauth.identity.authorize_access_token()
        identity = token.get('userinfo')
        if not identity or not identity.get('sub') or not identity.get('email'):
            abort(403)
        user = store.by_name(identity['email'])
        if not user or not user.get('active', False) or not store.bind_identity(user['id'], str(identity['sub'])):
            store.event('desconocido', 'LOGIN', 'DENEGADO')
            abort(403)
        session.clear()
        session['uid'] = user['id']
        session['csrf'] = secrets.token_urlsafe(32)
        session.permanent = True
        store.event(user['id'], 'LOGIN_OIDC', 'PERMITIDO')
        return redirect('/')
    except Exception:
        app.logger.warning('Inicio de sesión OIDC no completado; revisar configuración y eventos del proveedor')
        abort(403)


@app.get('/consulta')
@allowed('consulta')
def consult():
    return jsonify(store.state())


@app.post('/mantenimiento')
@allowed('mantenimiento')
def maintenance():
    return jsonify(store.maintain())


@app.post('/admin')
@allowed('admin')
def admin():
    try:
        return jsonify(store.set_mode(request.form.get('mode', '')))
    except ValueError:
        abort(400)


@app.get('/hub')
@allowed('hub')
def hub():
    return render_template('hub.html', events=store.events(), access_events=store.access_events(),
                           incidents=store.incidents(), camera_url=camera_url)


@app.get('/control-acceso')
@allowed('tarjetas')
def access_control():
    uid = session['uid']
    return render_template('access_control.html', user=store.get(uid), current_role=store.effective_role(uid),
                           csrf=session['csrf'], users=store.users_with_access(), cards=store.cards(), roles=sorted(PERMISSIONS))


@app.post('/usuarios/<user_id>/rol')
@allowed('usuarios')
def change_role(user_id):
    try:
        store.set_role(user_id, request.form.get('role', ''), session['uid'])
        return redirect('/control-acceso')
    except ValueError:
        abort(400)


@app.post('/tarjetas')
@allowed('tarjetas')
def create_card():
    try:
        store.add_card(request.form, session['uid'], CARD_PEPPER)
        return redirect('/control-acceso')
    except (ValueError, sqlite3.IntegrityError):
        abort(400)


@app.post('/tarjetas/<card_id>/estado')
@allowed('tarjetas')
def card_status(card_id):
    try:
        store.set_card_active(card_id, request.form.get('active') == '1', session['uid'])
        return redirect('/control-acceso')
    except ValueError:
        abort(400)


@app.post('/inventario')
@allowed('inventario')
def inventory():
    try:
        store.save_device(request.form)
        return redirect('/')
    except ValueError:
        abort(400)


@app.post('/incidentes')
@allowed('incidentes')
def incidents():
    try:
        store.add_incident(request.form, session['uid'])
        return redirect('/')
    except ValueError:
        abort(400)


@app.post('/api/v1/access-events')
@device_required
def receive_access_event():
    try:
        payload = dict(request.get_json(force=True))
        _, payload['credential'] = store.card_fingerprint(payload.get('credential', ''), CARD_PEPPER)
        return jsonify(store.add_access_event(payload)), 201
    except (ValueError, TypeError):
        return jsonify({'error': 'Evento no válido'}), 400


@app.get('/api/v1/access-events')
@device_required
def list_access_events():
    return jsonify(store.access_events(request.args.get('limit', 100, type=int)))


@app.post('/api/v1/access/check')
@device_required
def check_access():
    try:
        payload = request.get_json(silent=True)
        decision = store.check_card(payload.get('uid', ''), CARD_PEPPER)
        event = store.add_access_event({'reader': payload.get('reader', ''), 'credential': decision['label'],
            'movement': payload.get('movement', ''), 'result': 'PERMITIDO' if decision['allowed'] else 'DENEGADO',
            'reason': decision['reason']})
        return jsonify({**decision, 'event_id': event['id']})
    except (ValueError, TypeError):
        return jsonify({'error': 'Solicitud no válida'}), 400


@app.get('/registros')
@allowed('registros')
def records():
    return jsonify(store.events())


@app.post('/logout')
def logout():
    if not session.get('uid') or not hmac.compare_digest(request.form.get('csrf', ''), session.get('csrf', '')):
        abort(400)
    store.event(session['uid'], 'LOGOUT_APP', 'OK')
    session.clear()
    return redirect('/')


@app.route('/scim/v1/Users', methods=['GET', 'POST'])
@app.route('/scim/v2/Users', methods=['GET', 'POST'])
@scim_required
def users():
    if request.method == 'GET':
        query = request.args.get('filter', '')
        if query:
            match = re.fullmatch(r'(userName|externalId)\s+eq\s+"([^"]+)"', query, re.IGNORECASE)
            if not match:
                return error('Solo se admite filtro userName o externalId eq "valor"', 400)
            if match.group(1).lower() == 'username':
                found = store.by_name(match.group(2))
            else:
                found = next((user for user in store.all() if user.get('externalId') == match.group(2)), None)
            resources = [found] if found else []
        else:
            resources = store.all()
        start = max(1, request.args.get('startIndex', 1, type=int))
        count = max(0, min(100, request.args.get('count', 100, type=int)))
        return list_response(resources, start, count)
    try:
        payload = request.get_json(silent=True)
        if scim_v2_request() and (not isinstance(payload, dict) or SCIM_V2_SCHEMA + ':User' not in payload.get('schemas', [])):
            return error('El recurso debe declarar el esquema SCIM 2.0 User', 400)
        data = store.save(payload)
        version = 'v2' if scim_v2_request() else 'v1'
        return jsonify(format_user_resource(data)), 201, {'Location': BASE + f'/scim/{version}/Users/' + data['id']}
    except sqlite3.IntegrityError:
        return error('Usuario duplicado', 409)
    except (ValueError, TypeError):
        return error('Datos de usuario no válidos', 400)


@app.route('/scim/v1/Users/<user_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@app.route('/scim/v2/Users/<user_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@scim_required
def user_resource(user_id):
    previous = store.get(user_id)
    if not previous:
        return error('Usuario no encontrado', 404)
    if request.method == 'GET':
        return jsonify(format_user_resource(previous))
    if request.method == 'DELETE':
        store.remove(user_id)
        return '', 204
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict):
            return error('Debe enviarse un objeto JSON', 400)
        if scim_v2_request() and request.method == 'PUT' and SCIM_V2_SCHEMA + ':User' not in payload.get('schemas', []):
            return error('El recurso debe declarar el esquema SCIM 2.0 User', 400)
        if request.method == 'PATCH' and 'Operations' in payload:
            if not isinstance(payload['Operations'], list):
                return error('Operations debe ser una lista', 400)
            changes = {}
            for operation in payload['Operations']:
                if not isinstance(operation, dict):
                    return error('Operación no válida', 400)
                if operation.get('op', '').lower() not in ('replace', 'add'):
                    return error('Operación PATCH no admitida', 400)
                path = operation.get('path')
                if path and path.lower() in ('active', 'title', 'username', 'externalid'):
                    path = {'active': 'active', 'title': 'title', 'username': 'userName', 'externalid': 'externalId'}[path.lower()]
                    changes[path] = operation.get('value')
                elif path is None and isinstance(operation.get('value'), dict):
                    changes.update(operation['value'])
                else:
                    return error('Ruta PATCH no admitida', 400)
            payload = changes
        data = store.save(payload, user_id, replace=(scim_v2_request() and request.method == 'PUT'))
        return jsonify(format_user_resource(data))
    except sqlite3.IntegrityError:
        return error('Usuario duplicado', 409)
    except (ValueError, TypeError):
        return error('Datos de usuario no válidos', 400)


@app.get('/scim/v1/Groups')
@app.get('/scim/v2/Groups')
@scim_required
def groups():
    if scim_v2_request():
        return jsonify({'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'], 'totalResults': 0, 'startIndex': 1, 'itemsPerPage': 0, 'Resources': []})
    return jsonify({'schemas': [SCIM_V1_SCHEMA], 'totalResults': 0, 'startIndex': 1, 'itemsPerPage': 0, 'Resources': []})


@app.get('/scim/v2/ServiceProviderConfig')
@scim_required
def scim_service_provider_config():
    return jsonify({
        'schemas': ['urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig'],
        'patch': {'supported': True},
        'bulk': {'supported': False, 'maxOperations': 0, 'maxPayloadSize': 0},
        'filter': {'supported': True, 'maxResults': 100},
        'changePassword': {'supported': False},
        'sort': {'supported': False},
        'etag': {'supported': False},
        'authenticationSchemes': [{
            'type': 'oauthbearertoken', 'name': 'HTTP Bearer',
            'description': 'Bearer token estático de aprovisionamiento',
            'specUri': 'https://www.rfc-editor.org/rfc/rfc6750', 'primary': True,
        }],
    })


@app.get('/scim/v2/ResourceTypes')
@scim_required
def scim_resource_types():
    return jsonify({
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
        'totalResults': 1, 'startIndex': 1, 'itemsPerPage': 1,
        'Resources': [{
            'schemas': ['urn:ietf:params:scim:schemas:core:2.0:ResourceType'],
            'id': 'User', 'name': 'User', 'endpoint': '/Users',
            'description': 'Cuenta de usuario del Security Hub',
            'schema': SCIM_V2_SCHEMA + ':User',
            'meta': {'resourceType': 'ResourceType', 'location': BASE + '/scim/v2/ResourceTypes/User'},
        }],
    })


@app.get('/scim/v2/ResourceTypes/User')
@scim_required
def scim_user_resource_type():
    return jsonify({
        'schemas': ['urn:ietf:params:scim:schemas:core:2.0:ResourceType'],
        'id': 'User', 'name': 'User', 'endpoint': '/Users',
        'description': 'Cuenta de usuario del Security Hub',
        'schema': SCIM_V2_SCHEMA + ':User',
        'meta': {'resourceType': 'ResourceType', 'location': BASE + '/scim/v2/ResourceTypes/User'},
    })


SCIM_USER_SCHEMA = {
    'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Schema'],
    'id': SCIM_V2_SCHEMA + ':User', 'name': 'User',
    'description': 'Cuenta de usuario aprovisionada para el Security Hub',
    'attributes': [
        {'name': 'userName', 'type': 'string', 'multiValued': False, 'required': True, 'caseExact': False, 'mutability': 'readWrite', 'returned': 'always', 'uniqueness': 'server'},
        {'name': 'externalId', 'type': 'string', 'multiValued': False, 'required': False, 'caseExact': True, 'mutability': 'readWrite', 'returned': 'default', 'uniqueness': 'none'},
        {'name': 'active', 'type': 'boolean', 'multiValued': False, 'required': False, 'caseExact': False, 'mutability': 'readWrite', 'returned': 'default', 'uniqueness': 'none'},
        {'name': 'title', 'type': 'string', 'multiValued': False, 'required': False, 'caseExact': False, 'mutability': 'readWrite', 'returned': 'default', 'uniqueness': 'none'},
    ],
    'meta': {'resourceType': 'Schema', 'location': BASE + '/scim/v2/Schemas/' + SCIM_V2_SCHEMA + ':User'},
}


@app.get('/scim/v2/Schemas')
@scim_required
def scim_schemas():
    return jsonify({
        'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
        'totalResults': 1, 'startIndex': 1, 'itemsPerPage': 1,
        'Resources': [SCIM_USER_SCHEMA],
    })


@app.get('/scim/v2/Schemas/<path:schema_id>')
@scim_required
def scim_schema(schema_id):
    if schema_id != SCIM_V2_SCHEMA + ':User':
        return error('Esquema no encontrado', 404)
    return jsonify(SCIM_USER_SCHEMA)
