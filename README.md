# Avvisi biglietti Korn

Monitor gratuito per **Korn, 21 novembre 2026 ore 21:00, Unipol Forum (Assago)**.
I controlli girano su GitHub Actions: il computer dell'utente puo restare spento.

Il workflow [Avvisi biglietti Korn](https://github.com/stemardo/Korn-avvisi/actions/workflows/monitor.yml)
controlla ogni 15 minuti circa il campo booleano `inStock` del catalogo pubblico Eventim,
nel mercato TicketOne Italia. La prima esecuzione completa e riuscita l'11 novembre 2026.

## Cosa fa

- Verifica l'ID evento 21443423, artista, data e luogo prima di usare la disponibilita.
- Invia un messaggio Telegram di attivazione e un avviso quando i biglietti tornano disponibili.
- Salva lo stato in `monitor-state.json` e evita avvisi ripetuti finche il risultato non cambia.
- Dopo tre verifiche fallite segnala che il controllo non funziona; limita questi avvisi a uno al giorno.
- Disattiva automaticamente il workflow al primo controllo dopo l'inizio del concerto.

Il campo `status: Available` da solo **non** indica biglietti acquistabili: il monitor
richiede `inStock: true`. Il catalogo puo aggiornarsi in ritardo rispetto alla vendita;
un avviso non garantisce posti ancora acquistabili o un numero di biglietti specifico.

## Configurazione

Nei segreti GitHub Actions del repository servono:

- `TELEGRAM_BOT_TOKEN`: token del bot.
- `TELEGRAM_CHAT_ID`: ID della propria chat privata.

Il token integrato GitHub salva lo stato e disattiva il workflow alla scadenza.
Non occorrono altri token o servizi a pagamento. Sono usati soltanto runner standard
Ubuntu pubblici, senza artifact o cache a pagamento.

Per istruzioni, limiti e gestione del monitor leggi [LEGGIMI.md](LEGGIMI.md).

## fanSALE: integrazione non attiva

La pagina richiesta e https://www.fansale.it/tickets/all/korn/460942.
Le prove dell'11 novembre 2026 dal runner GitHub non hanno consentito la lettura:
richiesta HTTP in timeout, Chromium con ERR_HTTP2_PROTOCOL_ERROR e una prova
HTTP/1.1 in timeout. Un ulteriore tentativo si e fermato nell'installazione
delle dipendenze; la prova corretta senza APT e arrivata al sito ma non ha
caricato la pagina.

**Non e stato attivato un controllo ricorrente fanSALE. Il monitor TicketOne
continua a funzionare.** La [diagnosi fanSALE](https://github.com/stemardo/Korn-avvisi/actions/workflows/verifica-fansale.yml)
resta eseguibile manualmente e non invia avvisi Telegram.

Una possibile alternativa da verificare nell'account dell'utente e la funzione
«Alert Offerte» documentata nei
[termini fanSALE, paragrafo 4.4](https://www.ticketone.it/campaign/termini-e-condizioni-fansale-ottobre-2024).
Non e stata verificata la sua presenza nell'interfaccia attuale, ne e stata
collegata al bot.
