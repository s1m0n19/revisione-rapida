"""Orchestrazione del flusso completo di correzione: compilazione, test, valutazione e report."""

import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from revisione_rapida.compiler import compila
from revisione_rapida.grading import valuta_criterio
from revisione_rapida.griglia import Criterio, Griglia, carica_griglia
from revisione_rapida.report import (
    RisultatoCriterio,
    RisultatoParte,
    RisultatoStudente,
    salva_report,
)
from revisione_rapida.sostituzione import verifica_criterio_sostituzione_dati


def _valuta_criterio_griglia(
    criterio: Criterio, codice_sorgente: str, testo_esercizio: str
) -> RisultatoCriterio:
    """Valuta un singolo criterio della griglia e costruisce il
    RisultatoCriterio corrispondente.

    Solleva ValueError per i tipi di criterio non ancora gestiti da
    questa versione dell'orchestrazione, invece di ignorarli in
    silenzio.
    """
    if criterio.tipo == "oggettivo" and criterio.fonte_test == "sostituzione_dati":
        return verifica_criterio_sostituzione_dati(
            codice_sorgente=codice_sorgente, criterio=criterio
        )

    if criterio.tipo == "llm":
        valutazione = valuta_criterio(
            codice_sorgente=codice_sorgente,
            testo_esercizio=testo_esercizio,
            criterio=criterio,
        )
        return RisultatoCriterio(
            nome_criterio=valutazione.nome_criterio,
            peso_punti=criterio.peso_punti,
            punti_ottenuti=valutazione.punti_assegnati,
            dettaglio=valutazione.motivazione,
            verificato_automaticamente=False,
        )

    raise ValueError(
        f"Criterio '{criterio.nome}' non gestito da questa versione "
        f"dell'orchestrazione: tipo={criterio.tipo!r}, "
        f"fonte_test={criterio.fonte_test!r}."
    )


def processa_consegna(
    percorso_file_studente: str,
    nome_studente: str,
    griglia: Griglia,
    testo_esercizio: str,
) -> RisultatoStudente:
    """Compila, valuta e aggrega i risultati per la consegna di un
    singolo studente.

    Se la compilazione fallisce, ritorna subito un RisultatoStudente
    con la lista delle parti vuota: non ha senso proseguire con la
    valutazione di un codice che non compila.
    """
    esito_compilazione = compila(percorso_file_studente)
    if not esito_compilazione.successo:
        return RisultatoStudente(
            nome_studente=nome_studente,
            esito_compilazione=esito_compilazione,
            parti=[],
        )

    codice_sorgente = Path(percorso_file_studente).read_text(encoding="utf-8")

    parti_risultato = [
        RisultatoParte(
            nome_parte=parte.nome,
            punti_totali=parte.punti_totali,
            criteri=[
                _valuta_criterio_griglia(criterio, codice_sorgente, testo_esercizio)
                for criterio in parte.criteri
            ],
        )
        for parte in griglia.parti
    ]

    return RisultatoStudente(
        nome_studente=nome_studente,
        esito_compilazione=esito_compilazione,
        parti=parti_risultato,
    )


def processa_classe(
    cartella_consegne: str,
    percorso_griglia: str,
    percorso_testo_esercizio: str,
    cartella_output: str,
) -> list[str]:
    """Elabora tutte le consegne (.c) presenti in cartella_consegne
    rispetto alla griglia indicata, e salva un report per ognuna.

    Un'eccezione imprevista nella correzione di un singolo studente
    viene segnalata a schermo ma non interrompe il resto del batch.
    Ritorna la lista dei percorsi dei report generati.
    """
    griglia = carica_griglia(percorso_griglia)
    testo_esercizio = Path(percorso_testo_esercizio).read_text(encoding="utf-8")

    file_consegne = sorted(Path(cartella_consegne).glob("*.c"))

    percorsi_report: list[str] = []
    numero_processati = 0
    numero_errori_imprevisti = 0
    numero_compilazione_fallita = 0

    for file_consegna in file_consegne:
        nome_studente = file_consegna.stem
        try:
            risultato = processa_consegna(
                str(file_consegna), nome_studente, griglia, testo_esercizio
            )
        except Exception as errore:  # noqa: BLE001 - non deve bloccare il batch
            numero_errori_imprevisti += 1
            print(
                f"Attenzione: errore imprevisto durante la correzione di "
                f"'{nome_studente}', studente saltato: {errore}"
            )
            continue

        numero_processati += 1
        if not risultato.esito_compilazione.successo:
            numero_compilazione_fallita += 1

        percorsi_report.append(salva_report(risultato, cartella_output))

    print(
        f"Correzione completata: {numero_processati} studenti processati, "
        f"{numero_errori_imprevisti} con errori imprevisti, "
        f"{numero_compilazione_fallita} con compilazione fallita."
    )

    return percorsi_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Corregge automaticamente le consegne di una classe: compila, "
            "valuta secondo la griglia e genera un report per ogni studente."
        )
    )
    parser.add_argument(
        "cartella_consegne",
        help="Cartella contenente i file .c delle consegne degli studenti (un file per studente).",
    )
    parser.add_argument(
        "percorso_griglia",
        help="Percorso del file YAML con la griglia di valutazione dell'esercizio.",
    )
    parser.add_argument(
        "percorso_testo_esercizio",
        help="Percorso del file di testo con la consegna dell'esercizio, usato per la valutazione llm.",
    )
    parser.add_argument(
        "cartella_output",
        help="Cartella in cui salvare i report Markdown generati (creata se non esiste).",
    )
    argomenti = parser.parse_args()

    processa_classe(
        cartella_consegne=argomenti.cartella_consegne,
        percorso_griglia=argomenti.percorso_griglia,
        percorso_testo_esercizio=argomenti.percorso_testo_esercizio,
        cartella_output=argomenti.cartella_output,
    )
