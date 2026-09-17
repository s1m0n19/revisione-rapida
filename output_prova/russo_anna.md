# Report di valutazione — russo_anna

**Voto proposto: 20.0/100**

## DA VERIFICARE MANUALMENTE

- **Parte 1 - Giorni di punta — Correttezza - individuazione giorni di punta ed eccedenza**: Impossibile individuare univocamente i dati da sostituire nel codice, verifica manuale necessaria

## Parte 1 - Giorni di punta — 5/25 punti

### Correttezza - individuazione giorni di punta ed eccedenza (non verificato automaticamente)

Impossibile individuare univocamente i dati da sostituire nel codice, verifica manuale necessaria

### Uso corretto di array e cicli (4/4 punti)

Il codice utilizza un singolo ciclo `for` (righe 15-20) che scorre l'intero array `vendite[7]` con indicizzazione corretta (da 0 a 6, ovvero `i < 7`). All'interno del ciclo viene eseguita in modo compatto sia la stampa dei giorni di punta che l'accumulo dell'eccedenza (`eccedenza_totale += vendite[i] - soglia`), senza alcuna ridondanza o ripetizione inutile. L'array è dichiarato e popolato correttamente e la logica è chiara e lineare.

### Leggibilità e commenti (1/3 punti)

Il codice non contiene alcun commento esplicativo. I nomi delle variabili sono abbastanza descrittivi (vendite, soglia, eccedenza_totale) e aiutano a comprendere il contesto, ma l'assenza totale di commenti riduce la leggibilità complessiva, soprattutto per spiegare la logica del ciclo o il significato della soglia. Si colloca quindi nel livello intermedio: nomi discretamente chiari ma commenti del tutto assenti.

---

Voto proposto automaticamente. Il voto definitivo deve essere confermato dall'insegnante.
