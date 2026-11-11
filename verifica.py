"""Primo test manuale. Non attiva controlli ricorrenti o avvisi di disponibilita'."""
import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = 'https://www.ticketone.it/artist/korn/'


def report(text):
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(text + '\n')


def api(method, **params):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Aggiungi il secret TELEGRAM_BOT_TOKEN al repository.')
    request = urllib.request.Request(
        'https://api.telegram.org/bot' + token + '/' + method,
        data=urllib.parse.urlencode(params).encode(), method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        # Non stampare l'eccezione: l'URL Telegram contiene il token.
        raise RuntimeError(f'Telegram ha restituito HTTP {exc.code}. Controlla i secret e che il bot non sia bloccato.') from None
    except Exception:
        raise RuntimeError('Impossibile contattare Telegram; nessuna credenziale e\u0300 stata stampata.') from None
    if not payload.get('ok'):
        raise RuntimeError('Telegram non ha confermato la richiesta.')
    return payload.get('result')


def telegram():
    api('getMe')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not chat_id:
        # Non consumare gli aggiornamenti e non pubblicare il chat ID nei log.
        updates = api('getUpdates', limit=100, timeout=0)
        ids = {
            item['message']['chat']['id']
            for item in updates
            if item.get('message', {}).get('chat', {}).get('type') == 'private'
            and item['message'].get('text', '').split('@')[0].strip() == '/start'
        }
        if len(ids) != 1:
            raise RuntimeError('Non trovo una sola chat privata con /start. Invia /start al bot e riprova. Se ci sono piu\u0300 chat, configura TELEGRAM_CHAT_ID nei secret.')
        chat_id = next(iter(ids))
    result = api('sendMessage', chat_id=chat_id,
                 text=('Prova riuscita: il tuo bot Korn riceve messaggi da GitHub. '
                       'I controlli dei biglietti non sono ancora attivi.\n\n'
                       f'Il tuo chat ID: {chat_id}\n'
                       'Salvalo nel secret TELEGRAM_CHAT_ID del repository GitHub.'))
    if not isinstance(result, dict) or not result.get('message_id'):
        raise RuntimeError('Messaggio di prova non confermato.')
    report('Messaggio di prova inviato. Controlla Telegram. Nessun monitoraggio attivato.')


def ticketone():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        options = {'headless': True}
        if os.environ.get('BROWSER_EXECUTABLE_PATH'):
            options['executable_path'] = os.environ['BROWSER_EXECUTABLE_PATH']
        browser = p.chromium.launch(**options)
        try:
            page = browser.new_page(locale='it-IT')
            response = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            # Attesa limitata per i dati caricati in JavaScript.
            page.wait_for_timeout(12000)
            body = page.locator('body').inner_text(timeout=10000)
            status = response.status if response else None
            links = page.locator('a[href]').evaluate_all(
                '(elements) => elements.map(a => ({text: a.innerText, url: a.href}))'
            )
            event_links = []
            for link in links:
                parsed = urllib.parse.urlparse(link['url'])
                if parsed.hostname in ('www.ticketone.it', 'ticketone.it') and '/event/' in parsed.path:
                    if link['url'] not in event_links:
                        event_links.append(link['url'])
            controls = page.locator('button, select, input[type="submit"], [role="button"]').evaluate_all(
                '''(els) => els.slice(0, 100).map(el => ({
                    tag: el.tagName, id: el.id, cssClass: el.className,
                    label: el.innerText || el.value || el.getAttribute('aria-label') || '',
                    disabled: !!el.disabled, visible: !!el.getClientRects().length
                }))'''
            )
            text = (
                '## Test di accesso TicketOne\n\n'
                f'HTTP: {status}\n\n'
                'Questo e\u0300 un test tecnico: non conferma la disponibilita\u0300 dei biglietti.\n\n'
                '<details><summary>Testo pubblico letto dal browser</summary>\n\n<pre>'
                + html.escape(body[:20000]) + '</pre>\n</details>\n\n'
                + 'Link a pagine evento rilevati:\n\n'
                + ('\n'.join('- ' + url for url in event_links[:10]) or 'Nessuno')
                + '\n\n<details><summary>Controlli della pagina pubblica</summary>\n\n<pre>'
                + html.escape(json.dumps(controls, ensure_ascii=False, indent=2))
                + '</pre>\n</details>\n'
            )
            report(text)
            if status is None or status >= 400 or 'korn' not in body.lower():
                raise RuntimeError('Accesso non riuscito o pagina inattesa. Nessun avviso di disponibilita\u0300 e\u0300 stato inviato.')
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--telegram', action='store_true')
    args = parser.parse_args()
    try:
        telegram() if args.telegram else ticketone()
    except Exception as exc:
        # Gli errori Playwright riguardano solo la pagina pubblica TicketOne.
        report('Test non completato: ' + str(exc))
        sys.exit(1)
