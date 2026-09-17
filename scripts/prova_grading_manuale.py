"""Script manuale per verificare valuta_criterio() con una chiamata reale
all'API di Claude.

Non e' un test automatico: va lanciato a mano dallo sviluppatore quando
vuole controllare il comportamento del modello vero, ad esempio con:

    python scripts/prova_grading_manuale.py

Richiede ANTHROPIC_API_KEY nel file .env nella cartella del progetto.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from revisione_rapida.grading import valuta_criterio
from revisione_rapida.griglia import carica_griglia

CARTELLA_ESERCIZIO = Path(__file__).resolve().parent.parent / "esempi" / "esercizio_esempio"
CARTELLA_CONSEGNE = Path(__file__).resolve().parent.parent / "esempi" / "consegne_esempio"


def main() -> None:
    """Valuta il primo criterio di tipo 'llm' della griglia di esempio
    sul codice di esempio 'pulito.c' e stampa il risultato."""
    griglia = carica_griglia(str(CARTELLA_ESERCIZIO / "griglia.yaml"))
    testo_esercizio = (CARTELLA_ESERCIZIO / "testo.md").read_text(encoding="utf-8")
    codice_sorgente = (CARTELLA_CONSEGNE / "pulito.c").read_text(encoding="utf-8")

    criterio_llm = next(
        criterio
        for parte in griglia.parti
        for criterio in parte.criteri
        if criterio.tipo == "llm"
    )

    risultato = valuta_criterio(
        codice_sorgente=codice_sorgente,
        testo_esercizio=testo_esercizio,
        criterio=criterio_llm,
    )

    print(f"Criterio: {risultato.nome_criterio}")
    print(f"Punti assegnati: {risultato.punti_assegnati}")
    print(f"Livello scelto: {risultato.descrizione_livello_scelto}")
    print(f"Motivazione: {risultato.motivazione}")


if __name__ == "__main__":
    main()
