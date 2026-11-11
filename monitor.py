"""Avvisi Korn: catalogo pubblico Eventim, Telegram e stato persistente GitHub."""
import base64
import copy
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

EVENT_ID = '21443423'
GROUP_ID = '4115252'
EVENT_START = dt.datetime.fromisoformat('2026-11-21T21:00:00+01:00')
EVENT_URL = 'https://www.ticketone.it/event/korn-unipol-forum-21443423/'
STATE_PATH = 'monitor-state.json'
UTC = dt.timezone.utc


class MonitorError(Exception):
    """Errore che puo essere pubblicato nei log senza credenziali."""


def stamp(now):
    return now.astimezone(UTC).isoformat(timespec='seconds')


def log(message):
    print(message, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(html.escape(message) + '\n\n')


def request_json(url, *, label, data=None, method='GET', headers=None, allow_404=False):
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and allow_404:
            return None
        # Non stampare URL, header o eccezioni: quelli Telegram contengono il token.
        raise MonitorError(f'{label}: HTTP {exc.code}.') from None
    except Exception:
        raise MonitorError(f'{label}: connessione non riuscita.') from None
    if len(raw) > 1024 * 1024:
        raise MonitorError(f'{label}: risposta troppo grande.')
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise MonitorError(f'{label}: risposta JSON non valida.') from None


def read_stock(payload):
    """Richiede ID, artista, data, luogo e un booleano esplicito inStock."""
    if not isinstance(payload, dict) or not isinstance(payload.get('products'), list):
        raise MonitorError('Eventim: elenco eventi mancante.')
    matches = [p for p in payload['products']
               if isinstance(p, dict) and str(p.get('productId')) == EVENT_ID]
    if len(matches) != 1:
        raise MonitorError('Eventim: il concerto atteso non compare una sola volta.')
    event = matches[0]
    details = event.get('typeAttributes', {}).get('liveEntertainment', {})
    try:
        date = dt.datetime.fromisoformat(details.get('startDate', ''))
    except (TypeError, ValueError):
        raise MonitorError('Eventim: data del concerto non valida.') from None
    if (event.get('name', '').casefold() != 'korn'
            or str(event.get('productGroupId')) != GROUP_ID
            or details.get('location', {}).get('name') != 'Unipol Forum'
            or date != EVENT_START):
        raise MonitorError('Eventim: artista, data o luogo diversi dal concerto atteso.')
    if type(event.get('inStock')) is not bool:
        raise MonitorError('Eventim: campo inStock assente o non booleano.')
    if event.get('inStock') and event.get('status') != 'Available':
        raise MonitorError('Eventim: segnali di disponibilita discordanti.')
    # Il campo status=Available da solo non indica biglietti acquistabili.
    return event['inStock']


def fetch_stock():
    params = {'webId': 'web__ticketone-it', 'language': 'it', 'search_term': 'Korn',
              'page': 1, 'top': 10, 'sort': 'DateAsc'}
    url = ('https://public-api.eventim.com/websearch/search/api/exploration/v1/products?'
           + urllib.parse.urlencode(params))
    payload = request_json(url, label='Eventim', headers={'Accept': 'application/json'})
    return read_stock(payload)


def github(path, *, method='GET', payload=None, allow_404=False):
    token = os.environ.get('GH_TOKEN', '').strip()
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not token or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise MonitorError('Configurazione GitHub mancante.')
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Korn-avvisi'}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    return request_json('https://api.github.com/repos/' + repo + path,
                        label='GitHub', method=method, headers=headers,
                        data=data, allow_404=allow_404)


def initial_state():
    return {'version': 1, 'event_id': EVENT_ID, 'announced': False,
            'last_stock': None, 'failures': 0, 'last_error_notice_utc': None}


def load_state():
    response = github('/contents/' + STATE_PATH, allow_404=True)
    if response is None:
        return initial_state(), None
    try:
        state = json.loads(base64.b64decode(response['content']))
        sha = response['sha']
        assert state['version'] == 1 and state['event_id'] == EVENT_ID
        assert state['last_stock'] is None or type(state['last_stock']) is bool
        assert type(state['announced']) is bool
        assert type(state['failures']) is int and 0 <= state['failures'] <= 3
        if state['last_error_notice_utc']:
            assert dt.datetime.fromisoformat(state['last_error_notice_utc']).tzinfo
    except (KeyError, TypeError, ValueError, AssertionError):
        raise MonitorError('Stato persistente non valido; nessun reset automatico.') from None
    return state, sha


def save_state(state, sha):
    encoded = base64.b64encode((json.dumps(state, indent=2) + '\n').encode()).decode()
    payload = {'message': 'Aggiorna stato del monitor Korn [skip ci]', 'content': encoded}
    if sha:
        payload['sha'] = sha
    response = github('/contents/' + STATE_PATH, method='PUT', payload=payload)
    if not response or not response.get('content', {}).get('sha'):
        raise MonitorError('GitHub non ha confermato il salvataggio dello stato.')


def notify(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not re.fullmatch(r'[1-9][0-9]*', chat_id):
        raise MonitorError('Token Telegram o chat ID privato mancante/non valido.')
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': message,
                                  'disable_web_page_preview': 'true'}).encode()
    response = request_json('https://api.telegram.org/bot' + token + '/sendMessage',
                            label='Telegram', method='POST', data=data)
    if (not isinstance(response, dict) or response.get('ok') is not True
            or not response.get('result', {}).get('message_id')):
        raise MonitorError('Telegram non ha confermato il messaggio.')


def update_known(state, stock, now, send):
    result = copy.deepcopy(state)
    if not state['announced']:
        current = ('Eventim segnala biglietti disponibili: apri subito TicketOne.' if stock
                   else 'Al momento Eventim non segnala biglietti disponibili.')
        send('Monitoraggio Korn attivato: Assago, 21 novembre 2026.\n'
             'Controllo ogni 15 minuti circa, anche con il tuo PC spento.\n\n'
             + current + '\n' + EVENT_URL + '\n\n'
             'Ti avviso quando il catalogo segnala nuove disponibilita. '
             'I dati possono aggiornarsi in ritardo e i posti possono esaurirsi prima dell\'acquisto.')
        result['announced'] = True
    elif stock and state['last_stock'] is not True:
        send('Korn: Eventim segnala biglietti tornati disponibili!\n'
             '21 novembre 2026, Unipol Forum, Assago.\n'
             'Controlla subito i settori su TicketOne:\n' + EVENT_URL
             + '\n\nLa disponibilita puo cambiare e non garantisce un numero di posti specifico.')
        result['last_alert_utc'] = stamp(now)
    elif state['failures'] >= 3 and state['last_error_notice_utc']:
        send('Il controllo dei biglietti Korn e ripreso. '
             + ('Eventim segnala disponibilita.' if stock else 'Al momento nessuna disponibilita segnalata.'))
    if state['last_stock'] is not stock:
        result['last_change_utc'] = stamp(now)
    result['last_stock'] = stock
    result['failures'] = 0
    return result


def update_failure(state, now, send):
    result = copy.deepcopy(state)
    result['failures'] = min(3, state['failures'] + 1)
    previous = state['last_error_notice_utc']
    due = previous is None or (now - dt.datetime.fromisoformat(previous)).total_seconds() >= 86400
    if result['failures'] >= 3 and due:
        send('Non riesco a verificare i biglietti Korn da almeno tre controlli. '
             'La disponibilita e sconosciuta; continuero a riprovare.\n' + EVENT_URL)
        result['last_error_notice_utc'] = stamp(now)
    # Un controllo fallito non cambia mai l'ultima disponibilita conosciuta.
    return result


def run(now=None):
    now = now or dt.datetime.now(UTC)
    if now >= EVENT_START:
        github('/actions/workflows/monitor.yml/disable', method='PUT')
        log('Concerto iniziato: pianificazione disattivata automaticamente.')
        return
    state, sha = load_state()
    try:
        stock = fetch_stock()
    except MonitorError as exc:
        result = update_failure(state, now, notify)
        if result != state:
            save_state(result, sha)
        raise MonitorError(str(exc) + ' Disponibilita sconosciuta; nessun avviso di biglietti disponibili.') from None
    result = update_known(state, stock, now, notify)
    if result != state:
        save_state(result, sha)
    status = 'disponibili secondo Eventim' if stock else 'non disponibili secondo Eventim'
    log(f'Controllo {stamp(now)}: Korn {EVENT_ID}, {status}.')


if __name__ == '__main__':
    try:
        run()
    except MonitorError as exc:
        log(str(exc))
        sys.exit(1)
    except Exception:
        log('Errore inatteso nel monitor. Nessuna credenziale pubblicata nei log.')
        sys.exit(1)
