"""Script manuale per ispezionare visivamente l'output di
genera_report_markdown().

Non e' un test automatico: costruisce a mano alcune istanze di
RisultatoStudente con dati di esempio (nessuna chiamata reale a gcc o
all'API di Claude) e stampa a schermo il report Markdown risultante,
per un controllo visivo dello sviluppatore. Va lanciato a mano con:

    python scripts/prova_report_manuale.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from revisione_rapida.compiler import RisultatoCompilazione
from revisione_rapida.report import (
    RisultatoCriterio,
    RisultatoParte,
    RisultatoStudente,
    genera_report_markdown,
)

COMPILAZIONE_OK = RisultatoCompilazione(
    successo=True,
    errori=[],
    warning=[],
    percorso_eseguibile="/tmp/esempio_eseguibile",
)


def _studente_completo() -> RisultatoStudente:
    """Studente con 2 parti, ognuna con un criterio oggettivo gia'
    verificato e un criterio llm con una motivazione scritta a mano."""
    parte_correttezza = RisultatoParte(
        nome_parte="Correttezza",
        punti_totali=10,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Test dataset base",
                peso_punti=6,
                punti_ottenuti=6,
                dettaglio="3/3 dataset superati",
                verificato_automaticamente=True,
            ),
            RisultatoCriterio(
                nome_criterio="Uso corretto di array e cicli",
                peso_punti=4,
                punti_ottenuti=2,
                dettaglio=(
                    "Il codice usa un ciclo per elemento ma con logica "
                    "ridondante alla riga 12, dove l'array viene scorso "
                    "due volte invece di una."
                ),
                verificato_automaticamente=False,
            ),
        ],
    )
    parte_stile = RisultatoParte(
        nome_parte="Stile",
        punti_totali=6,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Assenza di warning",
                peso_punti=2,
                punti_ottenuti=2,
                dettaglio="Nessun warning prodotto dal compilatore",
                verificato_automaticamente=True,
            ),
            RisultatoCriterio(
                nome_criterio="Leggibilita'",
                peso_punti=4,
                punti_ottenuti=4,
                dettaglio=(
                    "Nomi di variabili chiari e commenti utili nei punti "
                    "piu' complessi del codice."
                ),
                verificato_automaticamente=False,
            ),
        ],
    )
    return RisultatoStudente(
        nome_studente="Mario Rossi",
        esito_compilazione=COMPILAZIONE_OK,
        parti=[parte_correttezza, parte_stile],
    )


def _studente_con_criterio_non_verificato() -> RisultatoStudente:
    """Studente con un criterio a sostituzione_dati non verificabile
    automaticamente (punti_ottenuti None), per vedere come appare la
    sezione 'DA VERIFICARE MANUALMENTE' nel report."""
    parte_dati = RisultatoParte(
        nome_parte="Sostituzione dati",
        punti_totali=5,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Calcolo su matrice",
                peso_punti=5,
                punti_ottenuti=None,
                dettaglio="dati non estraibili dal codice, verifica manuale necessaria",
                verificato_automaticamente=False,
            ),
        ],
    )
    parte_stile = RisultatoParte(
        nome_parte="Stile",
        punti_totali=3,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Leggibilita'",
                peso_punti=3,
                punti_ottenuti=3,
                dettaglio="Codice ben organizzato e commentato.",
                verificato_automaticamente=False,
            ),
        ],
    )
    return RisultatoStudente(
        nome_studente="Anna Verdi",
        esito_compilazione=COMPILAZIONE_OK,
        parti=[parte_dati, parte_stile],
    )


def main() -> None:
    """Genera e stampa il report Markdown per i due studenti di esempio."""
    print("=" * 70)
    print("ESEMPIO 1: tutti i criteri verificati")
    print("=" * 70)
    print(genera_report_markdown(_studente_completo()))

    print("=" * 70)
    print("ESEMPIO 2: un criterio non verificabile automaticamente")
    print("=" * 70)
    print(genera_report_markdown(_studente_con_criterio_non_verificato()))


if __name__ == "__main__":
    main()
