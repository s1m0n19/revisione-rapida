"""Chiamata all'API di Claude per la valutazione qualitativa del codice.

Il modulo e' testabile in isolamento: non carica alcun file .env e legge
la chiave API solo tramite il comportamento predefinito del client
anthropic (variabile d'ambiente ANTHROPIC_API_KEY), che deve essere
impostata dal chiamante (tipicamente main.py) prima dell'uso.
"""

import json
from dataclasses import dataclass

import anthropic

from revisione_rapida.griglia import Criterio

MODELLO = "claude-sonnet-4-6"
MAX_TOKEN_RISPOSTA = 2048
TIMEOUT_SECONDI = 30.0
NUMERO_MASSIMO_TENTATIVI = 2

# Eccezioni di rete/API considerate transitorie e quindi soggette a retry.
# anthropic.APITimeoutError e' una sottoclasse di APIConnectionError.
ERRORI_RITENTABILI = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class ErroreValutazioneLLM(Exception):
    """Errore generico durante la valutazione di un criterio tramite LLM."""


class ValoreNonValido(ErroreValutazioneLLM):
    """Il punteggio restituito dal modello non corrisponde a nessun
    livello previsto dal criterio."""


@dataclass
class ValutazioneCriterio:
    """Esito della valutazione di un singolo criterio tramite LLM."""

    nome_criterio: str
    punti_assegnati: int
    descrizione_livello_scelto: str
    motivazione: str


def _formatta_livelli(criterio: Criterio) -> str:
    """Formatta i livelli di un criterio come elenco leggibile per il prompt."""
    righe = [
        f"- {livello.punti} punti: {livello.descrizione}"
        for livello in criterio.livelli
    ]
    return "\n".join(righe)


def _costruisci_prompt(
    codice_sorgente: str, testo_esercizio: str, criterio: Criterio
) -> str:
    """Costruisce il prompt da inviare al modello per valutare il criterio."""
    return (
        "Sei un assistente che aiuta un docente a correggere un esercizio "
        "di programmazione in C. Devi valutare SOLO l'aspetto descritto dal "
        "criterio riportato sotto, scegliendo uno dei livelli elencati.\n\n"
        "Non valutare la correttezza funzionale del codice (cioe' se il "
        "programma produce l'output giusto): questo aspetto e' gia' "
        "verificato altrove in modo automatico e deterministico. Concentrati "
        "esclusivamente su quanto descritto dal criterio.\n\n"
        f"TESTO DELL'ESERCIZIO:\n{testo_esercizio}\n\n"
        f"CRITERIO DA VALUTARE: {criterio.nome} (massimo {criterio.peso_punti} punti)\n"
        "Livelli possibili (scegli ESATTAMENTE uno di questi, non punteggi "
        "intermedi o diversi):\n"
        f"{_formatta_livelli(criterio)}\n\n"
        f"CODICE DELLO STUDENTE:\n{codice_sorgente}\n\n"
        "Scegli il livello che meglio descrive il codice rispetto al "
        "criterio. Scrivi la motivazione in italiano, spiegando il perche' "
        "della scelta con riferimenti concreti a righe o parti specifiche "
        "del codice quando possibile."
    )


def _costruisci_schema(criterio: Criterio) -> dict:
    """Costruisce lo schema JSON che vincola la risposta del modello."""
    punti_possibili = [livello.punti for livello in criterio.livelli]
    return {
        "type": "object",
        "properties": {
            "punti_assegnati": {
                "type": "integer",
                "enum": punti_possibili,
            },
            "descrizione_livello_scelto": {"type": "string"},
            "motivazione": {"type": "string"},
        },
        "required": [
            "punti_assegnati",
            "descrizione_livello_scelto",
            "motivazione",
        ],
        "additionalProperties": False,
    }


def _chiama_modello_con_retry(
    client: "anthropic.Anthropic", prompt: str, schema: dict
) -> "anthropic.types.Message":
    """Chiama l'API di Claude, ritentando in caso di errori transitori di
    rete o dell'API, fino a NUMERO_MASSIMO_TENTATIVI tentativi in totale."""
    ultimo_errore: Exception | None = None

    for tentativo in range(1, NUMERO_MASSIMO_TENTATIVI + 1):
        try:
            return client.messages.create(
                model=MODELLO,
                max_tokens=MAX_TOKEN_RISPOSTA,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "format": {"type": "json_schema", "schema": schema}
                },
            )
        except ERRORI_RITENTABILI as errore:
            ultimo_errore = errore
            if tentativo == NUMERO_MASSIMO_TENTATIVI:
                raise ErroreValutazioneLLM(
                    "Chiamata all'API di Claude fallita dopo "
                    f"{NUMERO_MASSIMO_TENTATIVI} tentativi: {errore}"
                ) from errore

    # Punto irraggiungibile: il ciclo restituisce o solleva in ogni iterazione.
    raise ErroreValutazioneLLM(str(ultimo_errore))


def valuta_criterio(
    codice_sorgente: str,
    testo_esercizio: str,
    criterio: Criterio,
) -> ValutazioneCriterio:
    """Valuta un singolo criterio di tipo 'llm' della griglia sul codice
    di uno studente, chiamando l'API di Claude.

    Restituisce una ValutazioneCriterio con il livello scelto dal modello
    e la relativa motivazione in italiano. Solleva ValoreNonValido se il
    punteggio restituito non corrisponde a nessun livello del criterio, e
    ErroreValutazioneLLM per errori di rete/API (dopo i tentativi previsti)
    o per risposte non interpretabili come JSON.

    La funzione valuta un solo criterio: l'aggregazione del voto complessivo
    e' responsabilita' del chiamante.
    """
    prompt = _costruisci_prompt(codice_sorgente, testo_esercizio, criterio)
    schema = _costruisci_schema(criterio)

    client = anthropic.Anthropic(timeout=TIMEOUT_SECONDI)
    risposta = _chiama_modello_con_retry(client, prompt, schema)

    testo_risposta = next(
        blocco.text for blocco in risposta.content if blocco.type == "text"
    )

    try:
        dato = json.loads(testo_risposta)
    except json.JSONDecodeError as errore:
        raise ErroreValutazioneLLM(
            "La risposta del modello non e' un JSON valido: "
            f"{errore}. Contenuto ricevuto: {testo_risposta!r}"
        ) from errore

    punti_assegnati = dato["punti_assegnati"]
    punti_validi = {livello.punti for livello in criterio.livelli}
    if punti_assegnati not in punti_validi:
        raise ValoreNonValido(
            f"Il modello ha assegnato {punti_assegnati} punti per il "
            f"criterio '{criterio.nome}', ma i livelli previsti hanno "
            f"punteggi {sorted(punti_validi)}."
        )

    return ValutazioneCriterio(
        nome_criterio=criterio.nome,
        punti_assegnati=punti_assegnati,
        descrizione_livello_scelto=dato["descrizione_livello_scelto"],
        motivazione=dato["motivazione"],
    )
