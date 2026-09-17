"""Compilazione dei file C degli studenti e parsing di errori e warning."""

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_COMPILAZIONE_SECONDI = 30

# Riconosce le righe diagnostiche di gcc/clang nel formato
# "percorso/file.c:riga:colonna: error|warning: messaggio", catturando
# solo il numero di riga e il messaggio (il percorso e la colonna
# vengono scartati).
_PATTERN_DIAGNOSTICA = re.compile(
    r"^.*?:(?P<riga>\d+):(?:\d+:)?\s*(?P<tipo>error|warning):\s*(?P<messaggio>.*)$"
)


@dataclass
class RisultatoCompilazione:
    """Esito strutturato della compilazione di un file sorgente C."""

    successo: bool
    errori: list[str]
    warning: list[str]
    percorso_eseguibile: str | None


def _analizza_output(output_gcc: str) -> tuple[list[str], list[str]]:
    """Divide l'output di gcc in liste separate di errori e warning,
    ripulendo ogni riga dal percorso del file e mantenendo solo il
    numero di riga e il messaggio."""
    errori: list[str] = []
    warning: list[str] = []

    for riga_output in output_gcc.splitlines():
        corrispondenza = _PATTERN_DIAGNOSTICA.match(riga_output)
        if corrispondenza is None:
            continue

        riga_pulita = f"riga {corrispondenza['riga']}: {corrispondenza['messaggio']}"
        if corrispondenza["tipo"] == "error":
            errori.append(riga_pulita)
        else:
            warning.append(riga_pulita)

    return errori, warning


def compila(percorso_file: str) -> RisultatoCompilazione:
    """Compila un file sorgente C con gcc usando i flag -Wall -Wextra.

    L'eseguibile prodotto (in caso di successo) viene salvato in una
    cartella temporanea, non accanto al sorgente.

    Solleva FileNotFoundError se il file sorgente non esiste e
    RuntimeError se gcc non e' installato o non e' raggiungibile, o se
    la compilazione supera il timeout previsto.
    """
    sorgente = Path(percorso_file)
    if not sorgente.is_file():
        raise FileNotFoundError(f"File sorgente non trovato: {percorso_file}")

    cartella_output = tempfile.mkdtemp(prefix="revisione_rapida_compila_")
    percorso_output = str(Path(cartella_output) / sorgente.stem)

    comando = ["gcc", "-Wall", "-Wextra", "-o", percorso_output, str(sorgente)]

    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_COMPILAZIONE_SECONDI,
        )
    except FileNotFoundError as errore:
        raise RuntimeError(
            "gcc non e' installato o non e' raggiungibile nel PATH di sistema."
        ) from errore
    except subprocess.TimeoutExpired as errore:
        raise RuntimeError(
            f"Compilazione di '{percorso_file}' interrotta: superato il "
            f"timeout di {TIMEOUT_COMPILAZIONE_SECONDI} secondi."
        ) from errore

    errori, warning = _analizza_output(processo.stderr)
    successo = Path(percorso_output).is_file()

    return RisultatoCompilazione(
        successo=successo,
        errori=errori,
        warning=warning,
        percorso_eseguibile=percorso_output if successo else None,
    )
