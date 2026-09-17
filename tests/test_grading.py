"""Test del modulo di valutazione qualitativa tramite l'API di Claude.

Tutte le chiamate all'API sono mockate: nessun test in questo file esegue
una richiesta di rete reale, quindi non e' necessaria ANTHROPIC_API_KEY.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest

from revisione_rapida.grading import (
    ErroreValutazioneLLM,
    ValoreNonValido,
    ValutazioneCriterio,
    valuta_criterio,
)
from revisione_rapida.griglia import Criterio, Livello

CRITERIO_DI_PROVA = Criterio(
    nome="Uso corretto di array e cicli",
    peso_punti=4,
    tipo="llm",
    livelli=[
        Livello(punti=4, descrizione="Ciclo unico, indicizzazione corretta"),
        Livello(punti=2, descrizione="Funziona ma con logica ridondante"),
        Livello(punti=0, descrizione="Uso scorretto o confuso dell'array"),
    ],
)


def _risposta_con_testo(testo: str) -> SimpleNamespace:
    """Costruisce un oggetto risposta fittizio con un unico blocco testo,
    imitando la forma di anthropic.types.Message."""
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=testo)])


def _errore_connessione() -> anthropic.APIConnectionError:
    """Costruisce un errore di connessione fittizio dell'SDK anthropic."""
    richiesta = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=richiesta)


@patch("revisione_rapida.grading.anthropic.Anthropic")
def test_risposta_valida_costruisce_valutazione_criterio(mock_anthropic_cls):
    """Una risposta ben formata dal modello deve produrre una
    ValutazioneCriterio con tutti i campi popolati correttamente."""
    corpo_json = json.dumps(
        {
            "punti_assegnati": 4,
            "descrizione_livello_scelto": "Ciclo unico, indicizzazione corretta",
            "motivazione": "Il ciclo alla riga 3 usa un solo indice coerente.",
        }
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _risposta_con_testo(corpo_json)
    mock_anthropic_cls.return_value = mock_client

    risultato = valuta_criterio(
        codice_sorgente="int main() { return 0; }",
        testo_esercizio="Testo di esempio",
        criterio=CRITERIO_DI_PROVA,
    )

    assert risultato == ValutazioneCriterio(
        nome_criterio="Uso corretto di array e cicli",
        punti_assegnati=4,
        descrizione_livello_scelto="Ciclo unico, indicizzazione corretta",
        motivazione="Il ciclo alla riga 3 usa un solo indice coerente.",
    )

    # Il client deve essere stato configurato con un timeout ragionevole.
    _, kwargs_client = mock_anthropic_cls.call_args
    assert kwargs_client["timeout"] == pytest.approx(30.0)

    # La chiamata deve usare output structured con schema json_schema.
    _, kwargs_create = mock_client.messages.create.call_args
    assert kwargs_create["output_config"]["format"]["type"] == "json_schema"
    assert kwargs_create["model"] == "claude-sonnet-4-6"


@patch("revisione_rapida.grading.anthropic.Anthropic")
def test_punti_non_tra_i_livelli_solleva_valore_non_valido(mock_anthropic_cls):
    """Se il modello restituisce un punteggio non previsto dai livelli del
    criterio, deve essere sollevata ValoreNonValido invece di accettarlo."""
    corpo_json = json.dumps(
        {
            "punti_assegnati": 3,  # non e' uno dei livelli (4, 2, 0)
            "descrizione_livello_scelto": "Ciclo unico, indicizzazione corretta",
            "motivazione": "Motivazione qualsiasi.",
        }
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _risposta_con_testo(corpo_json)
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(ValoreNonValido):
        valuta_criterio(
            codice_sorgente="int main() { return 0; }",
            testo_esercizio="Testo di esempio",
            criterio=CRITERIO_DI_PROVA,
        )


@patch("revisione_rapida.grading.anthropic.Anthropic")
def test_risposta_non_json_valido_produce_errore_chiaro(mock_anthropic_cls):
    """Se la risposta del modello non e' un JSON valido, deve essere
    sollevata un'eccezione con un messaggio chiaro, non un traceback
    criptico di json.JSONDecodeError."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _risposta_con_testo(
        "questo non e' JSON"
    )
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(ErroreValutazioneLLM) as informazioni_errore:
        valuta_criterio(
            codice_sorgente="int main() { return 0; }",
            testo_esercizio="Testo di esempio",
            criterio=CRITERIO_DI_PROVA,
        )

    assert "JSON valido" in str(informazioni_errore.value)


@patch("revisione_rapida.grading.anthropic.Anthropic")
def test_primo_tentativo_fallisce_secondo_riesce(mock_anthropic_cls):
    """Un primo tentativo fallito per errore di rete non deve propagare
    l'eccezione se il tentativo successivo (entro il limite previsto) va
    a buon fine: la funzione deve restituire un risultato valido."""
    corpo_json = json.dumps(
        {
            "punti_assegnati": 2,
            "descrizione_livello_scelto": "Funziona ma con logica ridondante",
            "motivazione": "Il ciclo e' ripetuto inutilmente due volte.",
        }
    )
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _errore_connessione(),
        _risposta_con_testo(corpo_json),
    ]
    mock_anthropic_cls.return_value = mock_client

    risultato = valuta_criterio(
        codice_sorgente="int main() { return 0; }",
        testo_esercizio="Testo di esempio",
        criterio=CRITERIO_DI_PROVA,
    )

    assert risultato.punti_assegnati == 2
    assert mock_client.messages.create.call_count == 2


@patch("revisione_rapida.grading.anthropic.Anthropic")
def test_errore_di_rete_persistente_viene_propagato(mock_anthropic_cls):
    """Se tutti i tentativi consentiti falliscono per errore di rete,
    l'eccezione deve essere propagata al chiamante."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _errore_connessione(),
        _errore_connessione(),
    ]
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(ErroreValutazioneLLM):
        valuta_criterio(
            codice_sorgente="int main() { return 0; }",
            testo_esercizio="Testo di esempio",
            criterio=CRITERIO_DI_PROVA,
        )

    assert mock_client.messages.create.call_count == 2
