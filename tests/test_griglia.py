"""Test del modulo di caricamento e validazione della griglia di valutazione."""

from pathlib import Path

import pytest

from revisione_rapida.griglia import carica_griglia, valida_griglia

CARTELLA_FIXTURE = Path(__file__).resolve().parent / "fixtures_griglia"


def test_caricamento_file_valido_non_produce_errori():
    """Un file conforme allo schema deve caricarsi senza sollevare
    eccezioni e produrre una struttura corretta."""
    griglia = carica_griglia(str(CARTELLA_FIXTURE / "valida.yaml"))

    assert griglia.esercizio == "Verifica 1 - Array e Matrici"
    assert len(griglia.parti) == 1

    parte = griglia.parti[0]
    assert parte.nome == "Parte 1 - Giorni di punta"
    assert parte.punti_totali == 25
    assert len(parte.criteri) == 3

    criterio_oggettivo = parte.criteri[0]
    assert criterio_oggettivo.tipo == "oggettivo"
    assert criterio_oggettivo.fonte_test == "sostituzione_dati"
    assert criterio_oggettivo.target.tipo_c == "int[7]"
    assert criterio_oggettivo.soluzione_riferimento == "soluzioni.parte1"
    assert len(criterio_oggettivo.dataset) == 2
    assert criterio_oggettivo.dataset[0].nome == "tutti sotto soglia"
    assert criterio_oggettivo.dataset[0].valori == [10, 20, 15, 30, 25, 18, 22]

    criterio_llm = parte.criteri[1]
    assert criterio_llm.tipo == "llm"
    assert len(criterio_llm.livelli) == 3
    assert criterio_llm.livelli[0].punti == 4
    assert criterio_llm.livelli[0].descrizione == "Ciclo unico, indicizzazione corretta"

    assert valida_griglia(griglia) == []


def test_pesi_non_coerenti_valida_griglia_restituisce_errore_specifico():
    """Se la somma dei peso_punti dei criteri non corrisponde a
    punti_totali della parte, valida_griglia deve segnalarlo con un
    messaggio che nomina la parte e i valori in conflitto."""
    griglia = carica_griglia_senza_sollevare(CARTELLA_FIXTURE / "pesi_non_coerenti.yaml")

    errori = valida_griglia(griglia)

    assert len(errori) == 1
    assert "Parte 1" in errori[0]
    assert "punti_totali" in errori[0]


def test_pesi_non_coerenti_carica_griglia_solleva_value_error():
    """carica_griglia deve sollevare ValueError se la griglia non e'
    valida, cosi' che l'errore sia visibile subito a chi la usa."""
    with pytest.raises(ValueError, match="punti_totali"):
        carica_griglia(str(CARTELLA_FIXTURE / "pesi_non_coerenti.yaml"))


def test_criterio_oggettivo_senza_fonte_test_e_rilevato():
    """Un criterio con tipo 'oggettivo' privo di fonte_test deve essere
    segnalato dalla validazione."""
    griglia = carica_griglia_senza_sollevare(
        CARTELLA_FIXTURE / "oggettivo_senza_fonte_test.yaml"
    )

    errori = valida_griglia(griglia)

    assert len(errori) == 1
    assert "fonte_test" in errori[0]

    with pytest.raises(ValueError, match="fonte_test"):
        carica_griglia(str(CARTELLA_FIXTURE / "oggettivo_senza_fonte_test.yaml"))


def test_yaml_malformato_solleva_errore_chiaro():
    """Un file con sintassi YAML non valida deve produrre un ValueError
    con un messaggio comprensibile, non un traceback grezzo di pyyaml."""
    with pytest.raises(ValueError) as errore:
        carica_griglia(str(CARTELLA_FIXTURE / "malformato.yaml"))

    assert "YAML" in str(errore.value)


def carica_griglia_senza_sollevare(percorso_file: Path):
    """Costruisce la Griglia da un file senza passare per la validazione
    di carica_griglia, cosi' da poter testare valida_griglia in isolamento
    anche su file che non rispettano lo schema."""
    from revisione_rapida.griglia import _costruisci_griglia
    import yaml

    with open(percorso_file, encoding="utf-8") as file_yaml:
        dato = yaml.safe_load(file_yaml)

    return _costruisci_griglia(dato)
