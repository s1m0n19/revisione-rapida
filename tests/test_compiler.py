"""Test del modulo di compilazione dei file C."""

import subprocess
from pathlib import Path

import pytest

from revisione_rapida.compiler import compila

CARTELLA_ESEMPI = Path(__file__).resolve().parent.parent / "esempi" / "consegne_esempio"


def test_compilazione_pulita_ha_successo():
    """Un file senza errori ne' warning deve compilare con successo e
    produrre un eseguibile, con liste di errori e warning vuote."""
    risultato = compila(str(CARTELLA_ESEMPI / "pulito.c"))

    assert risultato.successo is True
    assert risultato.errori == []
    assert risultato.warning == []
    assert risultato.percorso_eseguibile is not None
    assert Path(risultato.percorso_eseguibile).is_file()


def test_errori_di_sintassi_falliscono_la_compilazione():
    """Un file con un errore di sintassi non deve produrre un
    eseguibile e deve riportare almeno un errore."""
    risultato = compila(str(CARTELLA_ESEMPI / "errori_sintassi.c"))

    assert risultato.successo is False
    assert len(risultato.errori) > 0
    assert risultato.percorso_eseguibile is None
    # I messaggi non devono contenere il percorso assoluto del file.
    for messaggio in risultato.errori:
        assert str(CARTELLA_ESEMPI) not in messaggio


def test_solo_warning_ha_comunque_successo():
    """Un file con soli warning (nessun errore) deve compilare con
    successo e riportare almeno un warning."""
    risultato = compila(str(CARTELLA_ESEMPI / "solo_warning.c"))

    assert risultato.successo is True
    assert risultato.errori == []
    assert len(risultato.warning) > 0
    assert risultato.percorso_eseguibile is not None
    assert Path(risultato.percorso_eseguibile).is_file()
    for messaggio in risultato.warning:
        assert str(CARTELLA_ESEMPI) not in messaggio


def test_percorso_file_inesistente_solleva_eccezione():
    """Un percorso che non corrisponde a nessun file deve sollevare
    FileNotFoundError, senza tentare di invocare gcc."""
    with pytest.raises(FileNotFoundError):
        compila(str(CARTELLA_ESEMPI / "file_che_non_esiste.c"))


def test_gcc_non_raggiungibile_solleva_runtime_error(monkeypatch):
    """Se gcc non e' installato (subprocess.run solleva FileNotFoundError),
    la funzione deve sollevare un RuntimeError esplicativo invece di
    lasciar propagare l'eccezione originale in modo silenzioso."""

    def subprocess_run_senza_gcc(*_args, **_kwargs):
        raise FileNotFoundError("gcc non trovato")

    monkeypatch.setattr(subprocess, "run", subprocess_run_senza_gcc)

    with pytest.raises(RuntimeError):
        compila(str(CARTELLA_ESEMPI / "pulito.c"))
