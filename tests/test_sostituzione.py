"""Test del modulo di verifica oggettiva a sostituzione dati.

I test di sostituisci_valori usano frammenti di codice C reali (senza
#include, per non dipendere dagli header di sistema durante il
parsing con pycparser) e compilano/eseguono davvero solo quando serve
verificarne il comportamento strutturale, non l'integrazione con gcc.

I test di verifica_criterio_sostituzione_dati mockano compiler.py e
test_runner.py per non dipendere da una vera toolchain C.
"""

from unittest.mock import patch

from revisione_rapida.compiler import RisultatoCompilazione
from revisione_rapida.griglia import Criterio, Dataset, Target
from revisione_rapida.sostituzione import (
    sostituisci_valori,
    verifica_criterio_sostituzione_dati,
)
from revisione_rapida.test_runner import EsitoTest

CODICE_CON_INIZIALIZZATORE = """
int main(void) {
    int vendite[7] = {10, 20, 15, 30, 25, 18, 22};
    return 0;
}
"""

CODICE_CON_ASSEGNAZIONI = """
int main(void) {
    int vendite[7];
    vendite[0] = 1;
    vendite[1] = 2;
    vendite[2] = 3;
    vendite[3] = 4;
    vendite[4] = 5;
    vendite[5] = 6;
    vendite[6] = 7;
    return 0;
}
"""

CODICE_AMBIGUO_DUE_ARRAY = """
int main(void) {
    int a[7] = {1, 2, 3, 4, 5, 6, 7};
    int b[7] = {1, 2, 3, 4, 5, 6, 7};
    return 0;
}
"""

CODICE_SENZA_ARRAY_CERCATO = """
int main(void) {
    int x = 5;
    return 0;
}
"""


def test_sostituisci_valori_con_inizializzatore_letterale():
    """Un array con inizializzatore letterale deve avere i suoi valori
    sostituiti con nuovi_valori, mantenendo il resto del codice."""
    risultato = sostituisci_valori(
        CODICE_CON_INIZIALIZZATORE, "int[7]", [1, 2, 3, 4, 5, 6, 7]
    )

    assert risultato is not None
    assert "{1, 2, 3, 4, 5, 6, 7}" in risultato
    assert "int main" in risultato


def test_sostituisci_valori_con_assegnazioni_singole():
    """Un array senza inizializzatore, valorizzato con assegnazioni
    singole a indici letterali, deve avere i valori di quelle
    assegnazioni sostituiti con nuovi_valori."""
    risultato = sostituisci_valori(
        CODICE_CON_ASSEGNAZIONI, "int[7]", [10, 20, 30, 40, 50, 60, 70]
    )

    assert risultato is not None
    for indice, valore in enumerate([10, 20, 30, 40, 50, 60, 70]):
        assert f"vendite[{indice}] = {valore};" in risultato


def test_sostituisci_valori_con_due_array_ambigui_ritorna_none():
    """Se ci sono due dichiarazioni candidate dello stesso tipo e
    dimensione, la sostituzione non puo' essere univoca e deve
    ritornare None invece di indovinare quale array modificare."""
    risultato = sostituisci_valori(
        CODICE_AMBIGUO_DUE_ARRAY, "int[7]", [1, 2, 3, 4, 5, 6, 7]
    )

    assert risultato is None


def test_sostituisci_valori_senza_array_del_tipo_cercato_ritorna_none():
    """Se nel codice non c'e' nessun array del tipo/dimensione cercati,
    non c'e' nulla da sostituire e la funzione deve ritornare None."""
    risultato = sostituisci_valori(
        CODICE_SENZA_ARRAY_CERCATO, "int[7]", [1, 2, 3, 4, 5, 6, 7]
    )

    assert risultato is None


def test_sostituisci_valori_con_codice_non_valido_ritorna_none():
    """Se il codice non e' sintatticamente valido, il parsing con
    pycparser fallisce e la funzione deve ritornare None invece di
    propagare l'eccezione di pycparser."""
    codice_non_valido = "int main( { questo non e' C valido"

    risultato = sostituisci_valori(codice_non_valido, "int[7]", [1, 2, 3])

    assert risultato is None


def _criterio_sostituzione_dati() -> Criterio:
    """Criterio di prova a sostituzione dati con due dataset, analogo
    a quello dell'esercizio di esempio 'Giorni di punta'."""
    return Criterio(
        nome="Correttezza - individuazione giorni di punta",
        peso_punti=18,
        tipo="oggettivo",
        fonte_test="sostituzione_dati",
        target=Target(tipo_c="int[7]"),
        soluzione_riferimento="soluzioni.parte1",
        dataset=[
            Dataset(nome="tutti sotto soglia", valori=[10, 20, 15, 30, 25, 18, 22]),
            Dataset(nome="caso limite esatto", valori=[40, 40, 41, 39, 40, 45, 40]),
        ],
    )


def _compilazione_riuscita() -> RisultatoCompilazione:
    return RisultatoCompilazione(
        successo=True, errori=[], warning=[], percorso_eseguibile="/tmp/finto"
    )


def test_verifica_criterio_con_tutti_i_dataset_superati():
    """Se l'output del programma contiene tutti i valori attesi per
    ogni dataset, il criterio deve ottenere il punteggio pieno ed
    essere segnato come verificato automaticamente."""
    criterio = _criterio_sostituzione_dati()

    # Output plausibile per entrambi i dataset: contiene sia i giorni
    # di punta sia l'eccedenza attesi dalla soluzione di riferimento.
    output_per_dataset = {
        "tutti sotto soglia": "giorni_punta=[] eccedenza=0",
        "caso limite esatto": "giorni_punta=[2, 5] eccedenza=6",
    }

    def _esegui_finto(percorso_eseguibile, *args, **kwargs):
        return EsitoTest(
            superato=True,
            output_prodotto="placeholder",
            output_atteso="",
            errore=None,
            timeout_scaduto=False,
        )

    with patch(
        "revisione_rapida.sostituzione.sostituisci_valori",
        side_effect=lambda codice_sorgente, tipo_c, nuovi_valori: "codice finto",
    ), patch(
        "revisione_rapida.sostituzione.compila", return_value=_compilazione_riuscita()
    ), patch(
        "revisione_rapida.sostituzione.esegui"
    ) as mock_esegui:
        mock_esegui.side_effect = [
            EsitoTest(
                superato=True,
                output_prodotto=output_per_dataset["tutti sotto soglia"],
                output_atteso="",
                errore=None,
                timeout_scaduto=False,
            ),
            EsitoTest(
                superato=True,
                output_prodotto=output_per_dataset["caso limite esatto"],
                output_atteso="",
                errore=None,
                timeout_scaduto=False,
            ),
        ]

        risultato = verifica_criterio_sostituzione_dati(
            codice_sorgente="codice sorgente qualsiasi", criterio=criterio
        )

    assert risultato.punti_ottenuti == 18
    assert risultato.verificato_automaticamente is True
    assert "tutti sotto soglia: superato" in risultato.dettaglio
    assert "caso limite esatto: superato" in risultato.dettaglio


def test_verifica_criterio_con_un_dataset_fallito_da_zero_punti():
    """Se l'output non contiene i valori attesi anche solo per un
    dataset, il criterio deve ottenere zero punti (tutto-o-niente),
    restando comunque verificato automaticamente, con il dettaglio che
    spiega quale dataset e' fallito."""
    criterio = _criterio_sostituzione_dati()

    with patch(
        "revisione_rapida.sostituzione.sostituisci_valori",
        side_effect=lambda codice_sorgente, tipo_c, nuovi_valori: "codice finto",
    ), patch(
        "revisione_rapida.sostituzione.compila", return_value=_compilazione_riuscita()
    ), patch(
        "revisione_rapida.sostituzione.esegui"
    ) as mock_esegui:
        mock_esegui.side_effect = [
            EsitoTest(
                superato=True,
                output_prodotto="giorni_punta=[] eccedenza=0",
                output_atteso="",
                errore=None,
                timeout_scaduto=False,
            ),
            EsitoTest(
                superato=True,
                output_prodotto="output completamente sbagliato",
                output_atteso="",
                errore=None,
                timeout_scaduto=False,
            ),
        ]

        risultato = verifica_criterio_sostituzione_dati(
            codice_sorgente="codice sorgente qualsiasi", criterio=criterio
        )

    assert risultato.punti_ottenuti == 0
    assert risultato.verificato_automaticamente is True
    assert "tutti sotto soglia: superato" in risultato.dettaglio
    assert "caso limite esatto: fallito" in risultato.dettaglio


def test_verifica_criterio_con_dati_non_estraibili_e_non_verificabile():
    """Se sostituisci_valori non riesce a individuare i dati da
    sostituire per un dataset, l'intero criterio deve risultare non
    verificabile, senza tentare compilazione o esecuzione."""
    criterio = _criterio_sostituzione_dati()

    with patch(
        "revisione_rapida.sostituzione.sostituisci_valori", return_value=None
    ), patch("revisione_rapida.sostituzione.compila") as mock_compila:
        risultato = verifica_criterio_sostituzione_dati(
            codice_sorgente="codice sorgente qualsiasi", criterio=criterio
        )

    assert risultato.punti_ottenuti is None
    assert risultato.verificato_automaticamente is False
    assert "verifica manuale necessaria" in risultato.dettaglio
    mock_compila.assert_not_called()


def test_verifica_criterio_con_compilazione_modificata_fallita_e_non_verificabile():
    """Se il codice modificato non compila, il criterio deve risultare
    non verificabile con lo stesso messaggio del caso di estrazione
    fallita, senza tentare l'esecuzione."""
    criterio = _criterio_sostituzione_dati()
    compilazione_fallita = RisultatoCompilazione(
        successo=False, errori=["errore fittizio"], warning=[], percorso_eseguibile=None
    )

    with patch(
        "revisione_rapida.sostituzione.sostituisci_valori",
        side_effect=lambda codice_sorgente, tipo_c, nuovi_valori: "codice finto",
    ), patch(
        "revisione_rapida.sostituzione.compila", return_value=compilazione_fallita
    ), patch("revisione_rapida.sostituzione.esegui") as mock_esegui:
        risultato = verifica_criterio_sostituzione_dati(
            codice_sorgente="codice sorgente qualsiasi", criterio=criterio
        )

    assert risultato.punti_ottenuti is None
    assert risultato.verificato_automaticamente is False
    assert "verifica manuale necessaria" in risultato.dettaglio
    mock_esegui.assert_not_called()
