"""Generazione del report di valutazione per lo studente."""

import re
from dataclasses import dataclass
from pathlib import Path

from revisione_rapida.compiler import RisultatoCompilazione

NOTA_FINALE = (
    "Voto proposto automaticamente. Il voto definitivo deve essere "
    "confermato dall'insegnante."
)


@dataclass
class RisultatoCriterio:
    """Esito di un singolo criterio gia' valutato, oggettivo o llm.

    dettaglio contiene: per i criteri oggettivi quali dataset sono
    passati/falliti, per i criteri llm la motivazione della valutazione,
    per i criteri non verificabili il motivo (es. dati non estraibili
    dal codice, verifica manuale necessaria).
    """

    nome_criterio: str
    peso_punti: int
    punti_ottenuti: int | None
    dettaglio: str
    verificato_automaticamente: bool


@dataclass
class RisultatoParte:
    """Esito di una parte dell'esercizio, composta da uno o piu' criteri
    gia' valutati."""

    nome_parte: str
    punti_totali: int
    criteri: list[RisultatoCriterio]

    @property
    def punti_ottenuti_parte(self) -> int:
        """Somma dei punti ottenuti dai criteri della parte, trattando i
        criteri non verificabili (punti_ottenuti None) come 0 nel calcolo."""
        return sum(criterio.punti_ottenuti or 0 for criterio in self.criteri)


@dataclass
class RisultatoStudente:
    """Esito complessivo della correzione di uno studente: compilazione,
    valutazione di ogni parte e voto proposto risultante."""

    nome_studente: str
    esito_compilazione: RisultatoCompilazione
    parti: list[RisultatoParte]

    @property
    def voto_totale_proposto(self) -> float:
        """Voto complessivo su base 100, calcolato come somma pesata dei
        punti ottenuti in tutte le parti rispetto ai punti totali
        possibili, arrotondato a 1 decimale."""
        punti_totali_possibili = sum(parte.punti_totali for parte in self.parti)
        if punti_totali_possibili == 0:
            return 0.0

        punti_ottenuti = sum(parte.punti_ottenuti_parte for parte in self.parti)
        return round(punti_ottenuti / punti_totali_possibili * 100, 1)

    @property
    def ha_parti_non_verificate(self) -> bool:
        """True se almeno un criterio di almeno una parte non e' stato
        verificabile automaticamente (punti_ottenuti None)."""
        return any(
            criterio.punti_ottenuti is None
            for parte in self.parti
            for criterio in parte.criteri
        )


def _sezione_errori_compilazione(risultato: RisultatoStudente) -> str:
    """Costruisce la sezione del report da mostrare quando la
    compilazione e' fallita: in questo caso il resto della valutazione
    non ha senso e il report si ferma qui."""
    righe = [
        f"# Report di valutazione — {risultato.nome_studente}",
        "",
        "**Codice non compilabile, valutazione non effettuata.**",
        "",
        "## Errori di compilazione",
        "",
    ]
    righe.extend(f"- {errore}" for errore in risultato.esito_compilazione.errori)
    return "\n".join(righe) + "\n"


def _sezione_da_verificare_manualmente(risultato: RisultatoStudente) -> list[str]:
    """Costruisce le righe della sezione, ben visibile in cima al report,
    che elenca i criteri non verificati automaticamente."""
    righe = ["", "## DA VERIFICARE MANUALMENTE", ""]
    for parte in risultato.parti:
        for criterio in parte.criteri:
            if criterio.punti_ottenuti is None:
                righe.append(
                    f"- **{parte.nome_parte} — {criterio.nome_criterio}**: "
                    f"{criterio.dettaglio}"
                )
    return righe


def _sezione_parte(parte: RisultatoParte) -> list[str]:
    """Costruisce le righe di dettaglio di una singola parte, con il
    punteggio ottenuto e il dettaglio di ogni criterio."""
    righe = [
        "",
        f"## {parte.nome_parte} — "
        f"{parte.punti_ottenuti_parte}/{parte.punti_totali} punti",
    ]
    for criterio in parte.criteri:
        punti_testo = (
            "non verificato automaticamente"
            if criterio.punti_ottenuti is None
            else f"{criterio.punti_ottenuti}/{criterio.peso_punti} punti"
        )
        righe.append("")
        righe.append(f"### {criterio.nome_criterio} ({punti_testo})")
        righe.append("")
        righe.append(criterio.dettaglio)
    return righe


def genera_report_markdown(risultato: RisultatoStudente) -> str:
    """Genera il report di valutazione in formato Markdown per uno
    studente.

    Se la compilazione e' fallita il report contiene solo l'intestazione
    e la sezione degli errori di compilazione: il resto della
    valutazione non ha senso in quel caso e non viene generato.
    """
    if not risultato.esito_compilazione.successo:
        return _sezione_errori_compilazione(risultato)

    righe = [
        f"# Report di valutazione — {risultato.nome_studente}",
        "",
        f"**Voto proposto: {risultato.voto_totale_proposto}/100**",
    ]

    if risultato.ha_parti_non_verificate:
        righe.extend(_sezione_da_verificare_manualmente(risultato))

    for parte in risultato.parti:
        righe.extend(_sezione_parte(parte))

    righe.extend(["", "---", "", NOTA_FINALE])

    return "\n".join(righe) + "\n"


def _sanifica_nome_file(nome_studente: str) -> str:
    """Sanifica il nome di uno studente per usarlo come nome di file
    valido: minuscolo, spazi sostituiti da underscore, rimozione di
    ogni carattere che non sia lettera, cifra o underscore."""
    nome_minuscolo = nome_studente.strip().lower()
    nome_con_underscore = re.sub(r"\s+", "_", nome_minuscolo)
    return re.sub(r"[^a-z0-9_]", "", nome_con_underscore)


def salva_report(risultato: RisultatoStudente, cartella_output: str) -> str:
    """Genera il report Markdown per lo studente e lo salva in un file
    dentro cartella_output, creando la cartella se non esiste.

    Il nome del file e' il nome dello studente sanificato (minuscolo,
    spazi sostituiti da underscore, senza caratteri non alfanumerici)
    con estensione .md. Restituisce il percorso del file creato.
    """
    contenuto = genera_report_markdown(risultato)

    cartella = Path(cartella_output)
    cartella.mkdir(parents=True, exist_ok=True)

    percorso_file = cartella / f"{_sanifica_nome_file(risultato.nome_studente)}.md"
    percorso_file.write_text(contenuto, encoding="utf-8")

    return str(percorso_file)
