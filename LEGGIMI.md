# Gestione del monitor Korn

Il monitor operativo e `monitor.py`, eseguito dal workflow **Avvisi biglietti Korn**.
I vecchi workflow di verifica restano disponibili soltanto per prove manuali.

## Fonte e riconoscimento

Fonte: https://public-api.eventim.com/websearch/search/api/exploration/v1/products
con mercato `web__ticketone-it` e ricerca Korn. L'accesso e stato verificato
dal runner GitHub. Non vengono caricati browser ne usate credenziali TicketOne.

Il concerto e identificato da ID `21443423`, gruppo `4115252`, nome Korn,
Unipol Forum e inizio `2026-11-21T21:00:00+01:00`.
Il risultato deve contenere un booleano `inStock`: assenze, risposte ambigue o
errori vengono trattati come disponibilita sconosciuta.

## Avvisi e frequenza

Il controllo e programmato ogni 15 minuti ai minuti 7, 22, 37 e 52.
GitHub puo avviarlo in ritardo o saltare un'esecuzione in caso di congestione.
Il bot invia un messaggio all'attivazione, poi solo quando la disponibilita
passa da assente a presente. Dopo tre errori consecutivi invia un avviso tecnico,
al massimo una volta ogni 24 ore; segnala anche il ripristino.

Lo stato pubblico `monitor-state.json` contiene soltanto l'ID evento, lo stato
del controllo e date tecniche. Non contiene token o chat ID. I segreti restano
in Settings > Secrets and variables > Actions.

Se Telegram conferma un messaggio e il salvataggio dello stato su GitHub fallisce,
il messaggio puo essere ripetuto al controllo successivo. Se il catalogo e in ritardo,
l'avviso puo arrivare dopo che la disponibilita reale e gia cambiata.
Non vengono verificati quantita, contiguita dei posti o settori specifici.

Il monitor si disattiva automaticamente al primo controllo dopo il
**21 novembre 2026 alle 21:00, ora italiana**. I permessi del workflow sono:
`contents: write` per salvare lo stato e `actions: write` per fermare la pianificazione.
La disattivazione a scadenza e verificata con un test simulato.

## Pausa, ripresa e controllo manuale

Apri https://github.com/stemardo/Korn-avvisi/actions/workflows/monitor.yml

- Per una verifica aggiuntiva: Run workflow, seleziona main, poi Run workflow.
- Per mettere in pausa: menu con i tre puntini, Disable workflow.
- Per riprendere prima del concerto: Enable workflow.
- Per controllare l'esito: apri l'ultima esecuzione e il suo riepilogo.

## Costi e limiti

Le esecuzioni standard GitHub-hosted sono gratuite nei repository pubblici.
Il workflow non carica artifact e non usa cache o runner a pagamento.
Non e un servizio con tempi di esecuzione garantiti e non riserva biglietti.

GitHub puo disattivare i workflow programmati pubblici dopo 60 giorni di inattivita,
oltre la durata prevista di questo monitor.

Fonti:
https://docs.github.com/en/billing/concepts/product-billing/github-actions
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## Verifiche del codice

`python3 -m unittest -v test_monitor.py` verifica segnali ambigui, corrispondenza
dell'evento, avvisi sui cambi di disponibilita, errori, mancata consegna e scadenza.
I test vengono eseguiti anche prima di ogni controllo GitHub.
