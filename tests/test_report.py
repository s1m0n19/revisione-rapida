"""Test del modulo di aggregazione dei risultati e generazione del report."""

from pathlib import Path

from revisione_rapida.compiler import RisultatoCompilazione
from revisione_rapida.report import (
    NOTA_FINALE,
    RisultatoCriterio,
    RisultatoParte,
    RisultatoStudente,
    genera_report_markdown,
    salva_report,
)

COMPILAZIONE_OK = RisultatoCompilazione(
    successo=True, errori=[], warning=[], percorso_eseguibile="/tmp/finto"
)

COMPILAZIONE_FALLITA = RisultatoCompilazione(
    successo=False,
    errori=["riga 3: expected ';' before 'return'"],
    warning=[],
    percorso_eseguibile=None,
)


def _studente_tutto_verificato() -> RisultatoStudente:
    """Studente con tutti i criteri verificati automaticamente, senza
    parti mancanti."""
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
                nome_criterio="Gestione errori",
                peso_punti=4,
                punti_ottenuti=4,
                dettaglio="2/2 dataset superati",
                verificato_automaticamente=True,
            ),
        ],
    )
    parte_stile = RisultatoParte(
        nome_parte="Stile",
        punti_totali=6,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Leggibilita'",
                peso_punti=6,
                punti_ottenuti=4,
                dettaglio="Codice leggibile, qualche nome di variabile poco chiaro",
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
    """Studente con un unico criterio non verificabile automaticamente
    (punti_ottenuti None)."""
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
    return RisultatoStudente(
        nome_studente="Anna Verdi",
        esito_compilazione=COMPILAZIONE_OK,
        parti=[parte_dati],
    )


def _studente_compilazione_fallita() -> RisultatoStudente:
    """Studente il cui codice non compila: le parti non devono comparire
    nel report, anche se qui sono valorizzate per verificarlo."""
    parte_correttezza = RisultatoParte(
        nome_parte="Correttezza",
        punti_totali=10,
        criteri=[
            RisultatoCriterio(
                nome_criterio="Test dataset base",
                peso_punti=10,
                punti_ottenuti=10,
                dettaglio="3/3 dataset superati",
                verificato_automaticamente=True,
            ),
        ],
    )
    return RisultatoStudente(
        nome_studente="Luca Bianchi",
        esito_compilazione=COMPILAZIONE_FALLITA,
        parti=[parte_correttezza],
    )


def test_voto_calcolato_correttamente_con_tutti_i_criteri_verificati():
    """Il voto totale deve essere la somma pesata dei punti ottenuti su
    base 100, arrotondata a 1 decimale, e non ci devono essere parti non
    verificate."""
    risultato = _studente_tutto_verificato()

    # Punti ottenuti: 6 + 4 + 4 = 14 su 16 totali -> 14/16*100 = 87.5
    assert risultato.voto_totale_proposto == 87.5
    assert risultato.ha_parti_non_verificate is False

    report = genera_report_markdown(risultato)

    assert "# Report di valutazione — Mario Rossi" in report
    assert "**Voto proposto: 87.5/100**" in report
    assert "DA VERIFICARE MANUALMENTE" not in report
    assert "## Correttezza — 10/10 punti" in report
    assert "## Stile — 4/6 punti" in report
    assert "### Test dataset base (6/6 punti)" in report
    assert "3/3 dataset superati" in report
    assert NOTA_FINALE in report


def test_criterio_non_verificato_segnalato_e_contato_come_zero():
    """Un criterio con punti_ottenuti None deve essere segnalato
    chiaramente nel report come da verificare manualmente, contare come 0
    nel calcolo del voto, e far scattare ha_parti_non_verificate."""
    risultato = _studente_con_criterio_non_verificato()

    assert risultato.ha_parti_non_verificate is True
    assert risultato.parti[0].punti_ottenuti_parte == 0
    assert risultato.voto_totale_proposto == 0.0

    report = genera_report_markdown(risultato)

    assert "DA VERIFICARE MANUALMENTE" in report
    assert "Calcolo su matrice" in report
    assert "dati non estraibili dal codice, verifica manuale necessaria" in report
    assert "### Calcolo su matrice (non verificato automaticamente)" in report
    assert NOTA_FINALE in report


def test_compilazione_fallita_report_si_ferma_alla_sezione_errori():
    """Se la compilazione e' fallita il report deve contenere solo
    l'intestazione e la sezione degli errori, senza mostrare parti,
    criteri, voto o la nota finale."""
    risultato = _studente_compilazione_fallita()

    report = genera_report_markdown(risultato)

    assert "Codice non compilabile, valutazione non effettuata" in report
    assert "riga 3: expected ';' before 'return'" in report
    assert "Correttezza" not in report
    assert "Test dataset base" not in report
    assert "Voto proposto" not in report
    assert NOTA_FINALE not in report


def test_salva_report_crea_file_con_contenuto_atteso(tmp_path):
    """salva_report deve creare la cartella di output se necessario,
    salvare un file con nome sanificato a partire dal nome dello
    studente, e il contenuto deve corrispondere a genera_report_markdown."""
    risultato = _studente_tutto_verificato()
    cartella_output = tmp_path / "report_non_ancora_esistente"

    percorso = salva_report(risultato, str(cartella_output))

    assert percorso == str(cartella_output / "mario_rossi.md")
    assert Path(percorso).is_file()
    assert Path(percorso).read_text(encoding="utf-8") == genera_report_markdown(
        risultato
    )


def test_salva_report_sanifica_nomi_con_caratteri_non_alfanumerici(tmp_path):
    """Il nome del file deve essere minuscolo, con spazi sostituiti da
    underscore e senza caratteri non alfanumerici (es. apostrofi)."""
    risultato = RisultatoStudente(
        nome_studente="Anna D'Amico",
        esito_compilazione=COMPILAZIONE_OK,
        parti=[],
    )

    percorso = salva_report(risultato, str(tmp_path))

    assert percorso == str(tmp_path / "anna_damico.md")
    assert Path(percorso).is_file()
