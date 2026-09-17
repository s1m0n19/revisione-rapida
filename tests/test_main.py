"""Test dell'orchestrazione del flusso completo di correzione.

Le chiamate a valuta_criterio() sono mockate: nessun test in questo
file esegue una richiesta di rete reale. I file .c usati sono minimi e
vengono creati al volo in tmp_path, e vengono compilati davvero con
gcc tramite compiler.py.
"""

from pathlib import Path
from unittest.mock import patch

from revisione_rapida.grading import ValutazioneCriterio
from revisione_rapida.griglia import Criterio, Griglia, Livello, Parte
from revisione_rapida.main import processa_classe, processa_consegna

SORGENTE_VALIDO = "int main(void) { return 0; }\n"
SORGENTE_NON_VALIDO = "int main(void) { return 0 \n"  # manca ';' e la '}'


def _griglia_con_un_criterio_llm() -> Griglia:
    """Griglia minima con un'unica parte e un unico criterio di tipo llm."""
    criterio_llm = Criterio(
        nome="Leggibilita'",
        peso_punti=4,
        tipo="llm",
        livelli=[
            Livello(punti=4, descrizione="Codice chiaro"),
            Livello(punti=0, descrizione="Codice confuso"),
        ],
    )
    parte = Parte(nome="Parte 1", punti_totali=4, criteri=[criterio_llm])
    return Griglia(esercizio="Esercizio di prova", parti=[parte])


def test_processa_consegna_con_compilazione_riuscita_e_criterio_llm(tmp_path):
    """Con compilazione riuscita, ogni criterio llm della griglia deve
    essere valutato tramite valuta_criterio() e il risultato deve
    confluire in un RisultatoCriterio del RisultatoStudente finale."""
    file_studente = tmp_path / "mario_rossi.c"
    file_studente.write_text(SORGENTE_VALIDO)

    griglia = _griglia_con_un_criterio_llm()

    valutazione_finta = ValutazioneCriterio(
        nome_criterio="Leggibilita'",
        punti_assegnati=4,
        descrizione_livello_scelto="Codice chiaro",
        motivazione="Il codice e' semplice e ben formattato.",
    )

    with patch(
        "revisione_rapida.main.valuta_criterio", return_value=valutazione_finta
    ) as mock_valuta:
        risultato = processa_consegna(
            percorso_file_studente=str(file_studente),
            nome_studente="Mario Rossi",
            griglia=griglia,
            testo_esercizio="Testo dell'esercizio",
        )

    assert risultato.nome_studente == "Mario Rossi"
    assert risultato.esito_compilazione.successo is True
    assert len(risultato.parti) == 1

    parte_risultato = risultato.parti[0]
    assert parte_risultato.nome_parte == "Parte 1"
    assert parte_risultato.punti_totali == 4
    assert len(parte_risultato.criteri) == 1

    criterio_risultato = parte_risultato.criteri[0]
    assert criterio_risultato.nome_criterio == "Leggibilita'"
    assert criterio_risultato.peso_punti == 4
    assert criterio_risultato.punti_ottenuti == 4
    assert criterio_risultato.dettaglio == "Il codice e' semplice e ben formattato."

    mock_valuta.assert_called_once()
    _, kwargs_chiamata = mock_valuta.call_args
    assert kwargs_chiamata["codice_sorgente"] == SORGENTE_VALIDO
    assert kwargs_chiamata["testo_esercizio"] == "Testo dell'esercizio"


def test_processa_consegna_con_compilazione_fallita_non_chiama_grading(tmp_path):
    """Se la compilazione fallisce, la funzione deve ritornare subito un
    RisultatoStudente con parti vuota, senza mai chiamare valuta_criterio()."""
    file_studente = tmp_path / "luca_bianchi.c"
    file_studente.write_text(SORGENTE_NON_VALIDO)

    griglia = _griglia_con_un_criterio_llm()

    with patch("revisione_rapida.main.valuta_criterio") as mock_valuta:
        risultato = processa_consegna(
            percorso_file_studente=str(file_studente),
            nome_studente="Luca Bianchi",
            griglia=griglia,
            testo_esercizio="Testo dell'esercizio",
        )

    assert risultato.nome_studente == "Luca Bianchi"
    assert risultato.esito_compilazione.successo is False
    assert len(risultato.esito_compilazione.errori) > 0
    assert risultato.parti == []
    mock_valuta.assert_not_called()


def test_processa_classe_continua_dopo_errore_imprevisto_su_uno_studente(tmp_path):
    """Se processa_consegna solleva un'eccezione imprevista per uno
    studente, il batch deve continuare con gli altri: il report
    dell'altro studente deve comunque essere salvato."""
    cartella_consegne = tmp_path / "consegne"
    cartella_consegne.mkdir()
    (cartella_consegne / "studente_ok.c").write_text(SORGENTE_VALIDO)
    (cartella_consegne / "studente_errore.c").write_text(SORGENTE_VALIDO)

    percorso_griglia = tmp_path / "griglia.yaml"
    percorso_griglia.write_text(
        "esercizio: Prova\n"
        "parti:\n"
        "  - nome: Parte 1\n"
        "    punti_totali: 4\n"
        "    criteri:\n"
        "      - nome: Leggibilita'\n"
        "        peso_punti: 4\n"
        "        tipo: llm\n"
        "        livelli:\n"
        "          - {punti: 4, descrizione: Codice chiaro}\n"
        "          - {punti: 0, descrizione: Codice confuso}\n"
    )

    percorso_testo = tmp_path / "testo.md"
    percorso_testo.write_text("Testo dell'esercizio di prova")

    cartella_output = tmp_path / "output"

    from revisione_rapida.report import RisultatoStudente
    from revisione_rapida.compiler import RisultatoCompilazione

    risultato_studente_ok = RisultatoStudente(
        nome_studente="studente_ok",
        esito_compilazione=RisultatoCompilazione(
            successo=True, errori=[], warning=[], percorso_eseguibile="/tmp/fittizio"
        ),
        parti=[],
    )

    def _processa_consegna_finto(percorso_file_studente, nome_studente, griglia, testo_esercizio):
        if nome_studente == "studente_errore":
            raise RuntimeError("errore imprevisto di prova")
        return risultato_studente_ok

    with patch(
        "revisione_rapida.main.processa_consegna", side_effect=_processa_consegna_finto
    ):
        percorsi_report = processa_classe(
            cartella_consegne=str(cartella_consegne),
            percorso_griglia=str(percorso_griglia),
            percorso_testo_esercizio=str(percorso_testo),
            cartella_output=str(cartella_output),
        )

    assert len(percorsi_report) == 1
    assert Path(percorsi_report[0]).is_file()
    assert Path(percorsi_report[0]).name == "studente_ok.md"
    assert not (cartella_output / "studente_errore.md").exists()
