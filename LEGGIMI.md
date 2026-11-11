# Primo test gratuito per Korn, TicketOne e Telegram

Questa versione verifica l'accesso a TicketOne da GitHub e, su richiesta,
manda un messaggio di prova Telegram. **Non monitora ancora la disponibilita\u0300**:
prima occorre vedere la pagina caricata dal browser e individuare il segnale
di disponibilita\u0300 nella vendita dell'evento di Assago del 21 novembre 2026.

1. Crea un account gratuito su https://github.com e un repository **Public**.
   Le esecuzioni standard Ubuntu nei repository pubblici sono gratuite.
   Non attivare runner a pagamento o caricamenti periodici di artifact.
2. Carica `verifica.py` nella cartella principale. Crea il secondo file con
   il percorso preciso `.github/workflows/verifica.yml` e incollaci il contenuto
   del file YAML qui fornito. Le cartelle che iniziano con un punto possono
   essere nascoste nel file manager.
3. In Settings > Secrets and variables > Actions > New repository secret,
   aggiungi `TELEGRAM_BOT_TOKEN`. Incolla il token di BotFather nel valore,
   mai nel codice, nei commenti o nella chat.
4. Invia `/start` nella chat privata del tuo nuovo bot subito prima del test.
5. La pubblicazione dei file avvia automaticamente il solo test della pagina.
   Per provare Telegram vai in Actions > Verifica TicketOne e Telegram > Run workflow, spunta
   la prova Telegram e premi Run workflow.
6. Controlla il messaggio Telegram e apri il riepilogo dell'esecuzione GitHub.
   La sezione Test di accesso TicketOne contiene il testo pubblico della pagina.
   Condividi il risultato per completare il riconoscimento dei biglietti.
7. Il messaggio di prova Telegram contiene il tuo chat ID: salvalo come secret
   `TELEGRAM_CHAT_ID`, per consentire agli avvisi futuri di raggiungerti anche
   dopo la scadenza degli aggiornamenti `/start`.

Se esistono piu\u0300 chat candidate, il test non sceglie un destinatario: configura
il tuo ID come secret `TELEGRAM_CHAT_ID`. Non imposta webhook, non acquista
biglietti e non tenta di superare CAPTCHA o blocchi del sito.

Il progetto pubblico espone codice e risultati dei test su una pagina pubblica;
i secret restano nei segreti GitHub. Usa solo il token del bot creato per questo
progetto. Se un token viene pubblicato, revocalo con BotFather.

Dopo un test riuscito, il programma potra\u0300 essere completato con uno stato
distinto per disponibilita\u0300, indisponibilita\u0300 e controllo non riuscito, senza
interpretare un errore o una pagina vuota come biglietti disponibili.

I controlli gratuiti programmati possono subire ritardi; nei repository pubblici
GitHub disattiva le pianificazioni dopo 60 giorni senza attivita\u0300. Le esecuzioni
future dovranno fermarsi dopo il concerto.

Fonti: https://docs.github.com/en/billing/concepts/product-billing/github-actions
e https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
