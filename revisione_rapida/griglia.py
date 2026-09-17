"""Caricamento e validazione del file di griglia di valutazione in formato YAML."""

from dataclasses import dataclass, field
from typing import Any, Literal

import yaml


@dataclass
class Livello:
    """Un livello di valutazione qualitativa per un criterio di tipo llm."""

    punti: int
    descrizione: str


@dataclass
class Dataset:
    """Un insieme di valori di input da usare per un criterio a
    sostituzione dati (i valori sono generici perche' potranno essere
    liste annidate, ad esempio per le matrici)."""

    nome: str
    valori: Any


@dataclass
class Target:
    """Il tipo C atteso per l'elemento da valutare (es. una funzione o
    una variabile) in un criterio oggettivo."""

    tipo_c: str


@dataclass
class Criterio:
    """Un singolo criterio di valutazione all'interno di una parte."""

    nome: str
    peso_punti: int
    tipo: Literal["oggettivo", "llm"]
    fonte_test: Literal["fornito", "llm", "sostituzione_dati"] | None = None
    target: Target | None = None
    soluzione_riferimento: str | None = None
    dataset: list[Dataset] = field(default_factory=list)
    livelli: list[Livello] = field(default_factory=list)


@dataclass
class Parte:
    """Una parte dell'esercizio, composta da uno o piu' criteri."""

    nome: str
    punti_totali: int
    criteri: list[Criterio]


@dataclass
class Griglia:
    """La griglia di valutazione completa di un esercizio."""

    esercizio: str
    parti: list[Parte]


def _costruisci_livello(dato: dict[str, Any]) -> Livello:
    """Costruisce un Livello a partire dal dizionario grezzo letto dallo YAML."""
    return Livello(punti=dato.get("punti"), descrizione=dato.get("descrizione"))


def _costruisci_dataset(dato: dict[str, Any]) -> Dataset:
    """Costruisce un Dataset a partire dal dizionario grezzo letto dallo YAML."""
    return Dataset(nome=dato.get("nome"), valori=dato.get("valori"))


def _costruisci_target(dato: dict[str, Any] | None) -> Target | None:
    """Costruisce un Target a partire dal dizionario grezzo letto dallo YAML,
    restituendo None se non presente."""
    if dato is None:
        return None
    return Target(tipo_c=dato.get("tipo_c"))


def _costruisci_criterio(dato: dict[str, Any]) -> Criterio:
    """Costruisce un Criterio a partire dal dizionario grezzo letto dallo YAML."""
    return Criterio(
        nome=dato.get("nome"),
        peso_punti=dato.get("peso_punti"),
        tipo=dato.get("tipo"),
        fonte_test=dato.get("fonte_test"),
        target=_costruisci_target(dato.get("target")),
        soluzione_riferimento=dato.get("soluzione_riferimento"),
        dataset=[_costruisci_dataset(d) for d in dato.get("dataset") or []],
        livelli=[_costruisci_livello(l) for l in dato.get("livelli") or []],
    )


def _costruisci_parte(dato: dict[str, Any]) -> Parte:
    """Costruisce una Parte a partire dal dizionario grezzo letto dallo YAML."""
    return Parte(
        nome=dato.get("nome"),
        punti_totali=dato.get("punti_totali"),
        criteri=[_costruisci_criterio(c) for c in dato.get("criteri") or []],
    )


def _costruisci_griglia(dato: dict[str, Any]) -> Griglia:
    """Costruisce una Griglia a partire dal dizionario grezzo letto dallo YAML."""
    return Griglia(
        esercizio=dato.get("esercizio"),
        parti=[_costruisci_parte(p) for p in dato.get("parti") or []],
    )


def carica_griglia(percorso_file: str) -> Griglia:
    """Legge il file YAML indicato e costruisce la Griglia corrispondente.

    Solleva ValueError se il file non e' uno YAML valido oppure se il
    contenuto non rispetta lo schema atteso: il messaggio contiene tutti
    gli errori di validazione rilevati, uno per riga, per permettere al
    docente di correggere il file in un solo passaggio.
    """
    with open(percorso_file, encoding="utf-8") as file_yaml:
        try:
            dato = yaml.safe_load(file_yaml)
        except yaml.YAMLError as errore:
            raise ValueError(
                f"Il file '{percorso_file}' non e' uno YAML valido: {errore}"
            ) from errore

    if not isinstance(dato, dict):
        raise ValueError(
            f"Il file '{percorso_file}' non contiene una griglia valida "
            "(atteso un oggetto YAML con le chiavi 'esercizio' e 'parti')."
        )

    griglia = _costruisci_griglia(dato)

    errori = valida_griglia(griglia)
    if errori:
        raise ValueError("\n".join(errori))

    return griglia


def _valida_criterio(criterio: Criterio, contesto: str) -> list[str]:
    """Valida un singolo criterio e restituisce la lista di messaggi di errore trovati."""
    errori: list[str] = []

    if criterio.tipo == "oggettivo":
        if criterio.fonte_test is None:
            errori.append(
                f"{contesto}: criterio oggettivo senza 'fonte_test' valorizzato."
            )

        if criterio.fonte_test == "sostituzione_dati":
            if criterio.target is None:
                errori.append(
                    f"{contesto}: criterio a sostituzione_dati senza 'target' valorizzato."
                )
            if criterio.soluzione_riferimento is None:
                errori.append(
                    f"{contesto}: criterio a sostituzione_dati senza "
                    "'soluzione_riferimento' valorizzato."
                )
            if not criterio.dataset:
                errori.append(
                    f"{contesto}: criterio a sostituzione_dati senza alcun dataset."
                )

    if criterio.tipo == "llm":
        if not criterio.livelli:
            errori.append(f"{contesto}: criterio llm senza alcun livello.")

        for livello in criterio.livelli:
            if livello.punti > criterio.peso_punti:
                errori.append(
                    f"{contesto}: il livello '{livello.descrizione}' ha "
                    f"{livello.punti} punti, superiori a peso_punti "
                    f"({criterio.peso_punti}) del criterio."
                )

    return errori


def valida_griglia(griglia: Griglia) -> list[str]:
    """Valida la griglia e restituisce la lista di messaggi di errore trovati.

    Restituisce una lista vuota se la griglia e' valida. Non solleva mai
    eccezioni: la validazione e' pensata per essere permissiva e
    descrittiva, cosi' da poter segnalare al docente tutti i problemi del
    file in un solo passaggio.
    """
    errori: list[str] = []

    for indice_parte, parte in enumerate(griglia.parti, start=1):
        contesto_parte = f"Parte {indice_parte} ('{parte.nome}')"

        somma_pesi = sum(criterio.peso_punti for criterio in parte.criteri)
        if somma_pesi != parte.punti_totali:
            errori.append(
                f"{contesto_parte}: la somma dei peso_punti dei criteri "
                f"({somma_pesi}) non corrisponde a punti_totali "
                f"({parte.punti_totali})."
            )

        for indice_criterio, criterio in enumerate(parte.criteri, start=1):
            contesto_criterio = (
                f"{contesto_parte}, criterio {indice_criterio} ('{criterio.nome}')"
            )
            errori.extend(_valida_criterio(criterio, contesto_criterio))

    return errori
