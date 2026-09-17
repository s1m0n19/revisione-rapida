"""Test del modulo di esecuzione dei test case sui programmi compilati."""

import tempfile
from pathlib import Path

import pytest

from revisione_rapida.compiler import compila
from revisione_rapida.test_runner import esegui, esegui_test

_SORGENTE_OUTPUT_FISSO = """
#include <stdio.h>

int main(void) {
    printf("Ciao mondo\\n");
    return 0;
}
"""

_SORGENTE_LEGGE_INPUT = """
#include <stdio.h>

int main(void) {
    int numero;
    scanf("%d", &numero);
    printf("Risultato: %d\\n", numero * 2);
    return 0;
}
"""

_SORGENTE_LOOP_INFINITO = """
int main(void) {
    while (1) {
    }
    return 0;
}
"""

_SORGENTE_CRASH = """
int main(void) {
    int *puntatore = 0;
    *puntatore = 42;
    return 0;
}
"""


def _compila_sorgente(cartella: Path, nome_file: str, codice_c: str) -> str:
    """Scrive il codice C in un file temporaneo e lo compila, restituendo
    il percorso dell'eseguibile prodotto."""
    percorso_sorgente = cartella / nome_file
    percorso_sorgente.write_text(codice_c)

    risultato = compila(str(percorso_sorgente))
    assert risultato.successo is True
    assert risultato.percorso_eseguibile is not None
    return risultato.percorso_eseguibile


@pytest.fixture(scope="module")
def eseguibili():
    """Compila una volta sola tutti i programmi C usati nei test."""
    with tempfile.TemporaryDirectory() as cartella_temp:
        cartella = Path(cartella_temp)
        yield {
            "output_fisso": _compila_sorgente(cartella, "output_fisso.c", _SORGENTE_OUTPUT_FISSO),
            "legge_input": _compila_sorgente(cartella, "legge_input.c", _SORGENTE_LEGGE_INPUT),
            "loop_infinito": _compila_sorgente(cartella, "loop_infinito.c", _SORGENTE_LOOP_INFINITO),
            "crash": _compila_sorgente(cartella, "crash.c", _SORGENTE_CRASH),
        }


def test_output_fisso_senza_input_confronto_corretto(eseguibili):
    """Un programma che stampa un output fisso, senza leggere input, deve
    superare il test quando l'output corrisponde a quello atteso."""
    esito = esegui_test(
        eseguibili["output_fisso"],
        output_atteso="Ciao mondo\n",
    )

    assert esito.superato is True
    assert esito.output_prodotto == "Ciao mondo\n"
    assert esito.errore is None
    assert esito.timeout_scaduto is False


def test_input_stdin_passato_correttamente(eseguibili):
    """Un programma che legge un valore da stdin deve ricevere
    correttamente input_stdin ed elaborarlo."""
    esito = esegui_test(
        eseguibili["legge_input"],
        input_stdin="21\n",
        output_atteso="Risultato: 42\n",
    )

    assert esito.superato is True
    assert esito.output_prodotto == "Risultato: 42\n"
    assert esito.errore is None


def test_ciclo_infinito_va_in_timeout(eseguibili):
    """Un programma con un ciclo infinito deve far scadere il timeout,
    senza lasciare il processo in esecuzione in background."""
    esito = esegui_test(
        eseguibili["loop_infinito"],
        timeout_secondi=0.5,
    )

    assert esito.timeout_scaduto is True
    assert esito.superato is False
    assert esito.errore is not None
    assert "timeout" in esito.errore.lower()


def test_confronto_ignora_solo_whitespace_finale(eseguibili):
    """Una riga vuota in piu' rispetto all'atteso (solo whitespace
    finale) non deve far fallire il confronto."""
    esito = esegui_test(
        eseguibili["output_fisso"],
        output_atteso="Ciao mondo\n\n\n",
    )

    assert esito.superato is True
    assert esito.errore is None


def test_output_diverso_non_e_un_errore_di_esecuzione(eseguibili):
    """Un output diverso da quello atteso deve far fallire il test senza
    valorizzare errore, perche' non e' un problema di esecuzione."""
    esito = esegui_test(
        eseguibili["output_fisso"],
        output_atteso="Output completamente diverso\n",
    )

    assert esito.superato is False
    assert esito.errore is None
    assert esito.timeout_scaduto is False


def test_crash_imposta_errore_e_non_supera(eseguibili):
    """Un programma che termina in modo anomalo (crash) deve impostare
    errore e superato=False."""
    esito = esegui_test(eseguibili["crash"])

    assert esito.superato is False
    assert esito.errore is not None
    assert esito.timeout_scaduto is False


def test_esegui_senza_output_atteso_ha_successo_se_non_ci_sono_errori(eseguibili):
    """esegui() deve avere successo se il programma termina senza
    timeout ne' crash, indipendentemente dall'output prodotto."""
    esito = esegui(eseguibili["output_fisso"])

    assert esito.superato is True
    assert esito.output_prodotto == "Ciao mondo\n"
    assert esito.errore is None


def test_esegui_propaga_timeout(eseguibili):
    """esegui() deve comportarsi come esegui_test anche per i timeout."""
    esito = esegui(eseguibili["loop_infinito"], timeout_secondi=0.5)

    assert esito.superato is False
    assert esito.timeout_scaduto is True
    assert esito.errore is not None
