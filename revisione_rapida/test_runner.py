"""Esecuzione dei test case sui programmi compilati e confronto dell'output."""

import subprocess
from dataclasses import dataclass


@dataclass
class EsitoTest:
    """Esito strutturato dell'esecuzione di un eseguibile su un test case."""

    superato: bool
    output_prodotto: str
    output_atteso: str
    errore: str | None
    timeout_scaduto: bool


def _normalizza(testo: str) -> str:
    """Normalizza un output per il confronto, ignorando le differenze di
    fine riga (\\n vs \\r\\n) e gli spazi bianchi finali di ogni riga e
    dell'intero testo."""
    righe = testo.splitlines()
    righe_pulite = [riga.rstrip() for riga in righe]
    return "\n".join(righe_pulite).rstrip()


def esegui_test(
    percorso_eseguibile: str,
    input_stdin: str = "",
    output_atteso: str = "",
    timeout_secondi: float = 5.0,
) -> EsitoTest:
    """Esegue un eseguibile compilato passandogli input_stdin come input
    standard, cattura l'output prodotto e lo confronta con output_atteso.

    Gestisce timeout (terminando il processo se supera timeout_secondi) e
    crash del programma (return code diverso da zero). In entrambi i casi
    superato e' False ed errore viene valorizzato. Se il programma termina
    normalmente ma produce un output diverso da quello atteso, superato e'
    False ma errore resta None: non si tratta di un problema di
    esecuzione, solo di un risultato errato.
    """
    try:
        processo = subprocess.run(
            [percorso_eseguibile],
            input=input_stdin,
            capture_output=True,
            text=True,
            timeout=timeout_secondi,
        )
    except subprocess.TimeoutExpired:
        return EsitoTest(
            superato=False,
            output_prodotto="",
            output_atteso=output_atteso,
            errore=(
                "Timeout: il programma non ha terminato entro "
                f"{timeout_secondi} secondi"
            ),
            timeout_scaduto=True,
        )

    output_prodotto = processo.stdout

    if processo.returncode != 0:
        return EsitoTest(
            superato=False,
            output_prodotto=output_prodotto,
            output_atteso=output_atteso,
            errore=(
                "Il programma e' terminato in modo anomalo "
                f"(codice di uscita {processo.returncode})"
            ),
            timeout_scaduto=False,
        )

    superato = _normalizza(output_prodotto) == _normalizza(output_atteso)

    return EsitoTest(
        superato=superato,
        output_prodotto=output_prodotto,
        output_atteso=output_atteso,
        errore=None,
        timeout_scaduto=False,
    )


def esegui(
    percorso_eseguibile: str,
    input_stdin: str = "",
    timeout_secondi: float = 5.0,
) -> EsitoTest:
    """Esegue un eseguibile senza confrontarlo con un output atteso.

    Utile quando serve solo eseguire il programma e osservarne il
    comportamento (ad esempio con dataset multipli). superato e' True se
    non si sono verificati timeout o crash.
    """
    esito = esegui_test(
        percorso_eseguibile,
        input_stdin=input_stdin,
        output_atteso="",
        timeout_secondi=timeout_secondi,
    )
    if esito.errore is not None:
        return esito

    return EsitoTest(
        superato=True,
        output_prodotto=esito.output_prodotto,
        output_atteso="",
        errore=None,
        timeout_scaduto=False,
    )
