"""Verifica oggettiva a sostituzione dati: sostituisce nel codice C di
uno studente i valori di un array con valori noti, compila ed esegue
per confrontare il risultato con la soluzione di riferimento.
"""

import importlib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pycparser
from pycparser import c_ast, c_generator

from revisione_rapida.compiler import compila
from revisione_rapida.griglia import Criterio
from revisione_rapida.report import RisultatoCriterio
from revisione_rapida.test_runner import esegui

# Argomenti extra passati a gcc -E per neutralizzare le estensioni
# GNU/Clang usate negli header di sistema (__attribute__, __asm,
# __inline, ecc.), che il grammar di pycparser non riconosce. Anche con
# questi argomenti il preprocessamento di header di sistema complessi
# (es. quelli del SDK macOS) puo' comunque fallire: in tal caso il
# parsing fallisce e sostituisci_valori ritorna None, come previsto.
_ARGOMENTI_CPP = [
    "-E",
    "-D__attribute__(x)=",
    "-D__extension__=",
    "-D__asm(x)=",
    "-D__asm__(x)=",
    "-D__restrict=",
    "-D__restrict__=",
    "-D__inline=inline",
    "-D__inline__=inline",
    "-D__signed=signed",
    "-D__signed__=signed",
    "-D__const=const",
    "-D__builtin_va_list=void*",
]

_PATTERN_TIPO_C = re.compile(
    r"^\s*(?P<tipo_base>[a-zA-Z_][a-zA-Z_0-9\s]*?)\s*(?P<dimensioni>(?:\[\s*\d+\s*\])+)\s*$"
)
_PATTERN_DIMENSIONE = re.compile(r"\[\s*(\d+)\s*\]")


@dataclass
class EsitoVerificaOggettiva:
    """Esito della verifica di un singolo dataset per un criterio a
    sostituzione dati."""

    nome_dataset: str
    superato: bool
    dettaglio: str


def _analizza_tipo_c(tipo_c: str) -> tuple[str, list[int]] | None:
    """Estrae tipo base e dimensioni da una stringa come 'int[7]'.

    Ritorna None se la stringa non e' nel formato atteso (tipo base
    seguito da una o piu' dimensioni tra parentesi quadre)."""
    corrispondenza = _PATTERN_TIPO_C.match(tipo_c)
    if corrispondenza is None:
        return None

    tipo_base = corrispondenza.group("tipo_base").strip()
    dimensioni = [int(d) for d in _PATTERN_DIMENSIONE.findall(corrispondenza.group("dimensioni"))]
    return tipo_base, dimensioni


def _dimensioni_e_tipo_base_di(nodo_tipo: c_ast.Node) -> tuple[str, list[int]] | None:
    """Estrae tipo base e dimensioni da un nodo di tipo ArrayDecl (con
    eventuali ArrayDecl annidati per gli array multidimensionali).

    Ritorna None se il nodo non descrive un array di tipo base
    semplice con dimensioni costanti letterali."""
    dimensioni: list[int] = []
    nodo = nodo_tipo

    while isinstance(nodo, c_ast.ArrayDecl):
        if not isinstance(nodo.dim, c_ast.Constant) or nodo.dim.type != "int":
            return None
        dimensioni.append(int(nodo.dim.value))
        nodo = nodo.type

    if not isinstance(nodo, c_ast.TypeDecl) or not isinstance(nodo.type, c_ast.IdentifierType):
        return None

    tipo_base = " ".join(nodo.type.names)
    return tipo_base, dimensioni


class _RaccoglitoreDichiarazioniArray(c_ast.NodeVisitor):
    """Raccoglie tutte le dichiarazioni di array la cui forma (tipo
    base e dimensioni) corrisponde a quella cercata."""

    def __init__(self, tipo_base_cercato: str, dimensioni_cercate: list[int]):
        self.tipo_base_cercato = tipo_base_cercato
        self.dimensioni_cercate = dimensioni_cercate
        self.dichiarazioni_trovate: list[c_ast.Decl] = []

    def visit_Decl(self, nodo: c_ast.Decl) -> None:
        if isinstance(nodo.type, c_ast.ArrayDecl):
            forma = _dimensioni_e_tipo_base_di(nodo.type)
            if forma == (self.tipo_base_cercato, self.dimensioni_cercate):
                self.dichiarazioni_trovate.append(nodo)
        self.generic_visit(nodo)


class _RaccoglitoreAssegnazioniArray(c_ast.NodeVisitor):
    """Raccoglie le assegnazioni dirette a un array con indice
    letterale (es. 'arr[0] = 10;')."""

    def __init__(self, nome_variabile: str):
        self.nome_variabile = nome_variabile
        self.assegnazioni_trovate: list[c_ast.Assignment] = []

    def visit_Assignment(self, nodo: c_ast.Assignment) -> None:
        lvalue = nodo.lvalue
        if (
            nodo.op == "="
            and isinstance(lvalue, c_ast.ArrayRef)
            and isinstance(lvalue.name, c_ast.ID)
            and lvalue.name.name == self.nome_variabile
            and isinstance(lvalue.subscript, c_ast.Constant)
            and lvalue.subscript.type == "int"
        ):
            self.assegnazioni_trovate.append(nodo)
        self.generic_visit(nodo)


def _costruisci_costante(valore: object) -> c_ast.Constant:
    """Costruisce un nodo Constant di pycparser a partire da un valore
    Python, scegliendo il tipo C piu' plausibile."""
    if isinstance(valore, bool):
        return c_ast.Constant(type="int", value="1" if valore else "0")
    if isinstance(valore, int):
        return c_ast.Constant(type="int", value=str(valore))
    if isinstance(valore, float):
        return c_ast.Constant(type="double", value=repr(valore))
    return c_ast.Constant(type="string", value=f'"{valore}"')


def _sostituisci_inizializzatore(dichiarazione: c_ast.Decl, nuovi_valori: list) -> bool:
    """Sostituisce gli elementi dell'inizializzatore letterale di una
    dichiarazione con nuovi_valori. Ritorna True se e' stato possibile."""
    if not isinstance(dichiarazione.init, c_ast.InitList):
        return False

    dichiarazione.init.exprs = [_costruisci_costante(valore) for valore in nuovi_valori]
    return True


def _sostituisci_assegnazioni(ast: c_ast.Node, nome_variabile: str, nuovi_valori: list) -> bool:
    """Cerca le assegnazioni singole successive allo stesso array con
    indici letterali e ne sostituisce i valori assegnati.

    Ritorna True solo se sono state trovate esattamente le assegnazioni
    per tutti e soli gli indici da 0 a len(nuovi_valori) - 1, in modo
    che la sostituzione sia univoca e completa."""
    raccoglitore = _RaccoglitoreAssegnazioniArray(nome_variabile)
    raccoglitore.visit(ast)
    assegnazioni = raccoglitore.assegnazioni_trovate

    if len(assegnazioni) != len(nuovi_valori):
        return False

    indici_trovati = sorted(int(assegnazione.lvalue.subscript.value) for assegnazione in assegnazioni)
    if indici_trovati != list(range(len(nuovi_valori))):
        return False

    assegnazioni_per_indice = {
        int(assegnazione.lvalue.subscript.value): assegnazione for assegnazione in assegnazioni
    }
    for indice, valore in enumerate(nuovi_valori):
        assegnazioni_per_indice[indice].rvalue = _costruisci_costante(valore)

    return True


def sostituisci_valori(codice_sorgente: str, tipo_c: str, nuovi_valori: list) -> str | None:
    """Sostituisce nel codice sorgente C i valori di un array del tipo
    indicato con nuovi_valori, e ritorna il codice C rigenerato.

    Ritorna None (senza sollevare eccezioni) se il parsing fallisce, se
    non viene trovata esattamente una dichiarazione candidata, o se non
    e' possibile individuare in modo univoco ne' un inizializzatore
    letterale ne' un insieme completo di assegnazioni singole da
    sostituire: si tratta di casi previsti, da gestire come "non
    verificabile automaticamente" da parte del chiamante.
    """
    forma_cercata = _analizza_tipo_c(tipo_c)
    if forma_cercata is None:
        return None
    tipo_base_cercato, dimensioni_cercate = forma_cercata

    ast = _analizza_codice(codice_sorgente)
    if ast is None:
        return None

    raccoglitore = _RaccoglitoreDichiarazioniArray(tipo_base_cercato, dimensioni_cercate)
    raccoglitore.visit(ast)
    candidate = raccoglitore.dichiarazioni_trovate

    if len(candidate) != 1:
        return None

    dichiarazione = candidate[0]

    sostituito = _sostituisci_inizializzatore(dichiarazione, nuovi_valori)
    if not sostituito:
        sostituito = _sostituisci_assegnazioni(ast, dichiarazione.name, nuovi_valori)

    if not sostituito:
        return None

    return c_generator.CGenerator().visit(ast)


def _analizza_codice(codice_sorgente: str) -> c_ast.Node | None:
    """Fa il parsing del codice sorgente C con pycparser, usando il
    preprocessore reale (gcc -E) per gestire gli #include standard.

    Ritorna None se il parsing fallisce per qualsiasi motivo (errori di
    sintassi nel codice dello studente, o header di sistema che il
    grammar semplificato di pycparser non riesce a interpretare):
    e' un caso previsto, non un errore da propagare.
    """
    file_temporaneo = tempfile.NamedTemporaryFile(
        mode="w", suffix=".c", delete=False, encoding="utf-8"
    )
    try:
        file_temporaneo.write(codice_sorgente)
        file_temporaneo.close()
        return pycparser.parse_file(
            file_temporaneo.name,
            use_cpp=True,
            cpp_path="gcc",
            cpp_args=_ARGOMENTI_CPP,
        )
    except Exception:
        return None
    finally:
        Path(file_temporaneo.name).unlink(missing_ok=True)


def _numeri_in(valore: object) -> list:
    """'Srotola' liste e dict annidati in una lista piatta di numeri."""
    if isinstance(valore, bool):
        return []
    if isinstance(valore, (int, float)):
        return [valore]
    if isinstance(valore, dict):
        numeri = []
        for elemento in valore.values():
            numeri.extend(_numeri_in(elemento))
        return numeri
    if isinstance(valore, (list, tuple)):
        numeri = []
        for elemento in valore:
            numeri.extend(_numeri_in(elemento))
        return numeri
    return []


def _chiama_soluzione_riferimento(soluzione_riferimento: str, valori_dataset: object) -> object:
    """Importa dinamicamente e chiama la funzione di soluzione di
    riferimento indicata, es. 'soluzioni.parte1'."""
    nome_modulo, nome_funzione = soluzione_riferimento.rsplit(".", 1)
    modulo = importlib.import_module(f"revisione_rapida.{nome_modulo}")
    funzione = getattr(modulo, nome_funzione)
    return funzione(valori_dataset)


_DETTAGLIO_NON_VERIFICABILE = (
    "Impossibile individuare univocamente i dati da sostituire nel codice, "
    "verifica manuale necessaria"
)


def _risultato_non_verificabile(criterio: Criterio) -> RisultatoCriterio:
    """Costruisce il RisultatoCriterio da usare quando un dataset non e'
    verificabile automaticamente (estrazione o compilazione fallita)."""
    return RisultatoCriterio(
        nome_criterio=criterio.nome,
        peso_punti=criterio.peso_punti,
        punti_ottenuti=None,
        dettaglio=_DETTAGLIO_NON_VERIFICABILE,
        verificato_automaticamente=False,
    )


def _verifica_dataset(
    criterio: Criterio, dataset, codice_sorgente: str
) -> EsitoVerificaOggettiva | None:
    """Verifica un singolo dataset del criterio. Ritorna None se il
    dataset non e' verificabile automaticamente (estrazione dei dati o
    compilazione del codice modificato falliti)."""
    codice_modificato = sostituisci_valori(
        codice_sorgente=codice_sorgente,
        tipo_c=criterio.target.tipo_c,
        nuovi_valori=dataset.valori,
    )
    if codice_modificato is None:
        return None

    file_temporaneo = tempfile.NamedTemporaryFile(
        mode="w", suffix=".c", delete=False, encoding="utf-8"
    )
    try:
        file_temporaneo.write(codice_modificato)
        file_temporaneo.close()
        esito_compilazione = compila(file_temporaneo.name)
    finally:
        Path(file_temporaneo.name).unlink(missing_ok=True)

    if not esito_compilazione.successo:
        return None

    esito_esecuzione = esegui(esito_compilazione.percorso_eseguibile)

    if esito_esecuzione.errore is not None:
        return EsitoVerificaOggettiva(
            nome_dataset=dataset.nome,
            superato=False,
            dettaglio=f"Errore di esecuzione: {esito_esecuzione.errore}",
        )

    risultato_atteso = _chiama_soluzione_riferimento(
        criterio.soluzione_riferimento, dataset.valori
    )
    numeri_attesi = _numeri_in(risultato_atteso)
    numeri_mancanti = [
        numero
        for numero in numeri_attesi
        if str(numero) not in esito_esecuzione.output_prodotto
    ]

    if numeri_mancanti:
        return EsitoVerificaOggettiva(
            nome_dataset=dataset.nome,
            superato=False,
            dettaglio=(
                f"valori attesi {numeri_attesi}, mancanti nell'output: "
                f"{numeri_mancanti}. Output prodotto: {esito_esecuzione.output_prodotto!r}"
            ),
        )

    return EsitoVerificaOggettiva(
        nome_dataset=dataset.nome,
        superato=True,
        dettaglio=f"valori attesi {numeri_attesi} tutti presenti nell'output",
    )


def verifica_criterio_sostituzione_dati(
    codice_sorgente: str, criterio: Criterio
) -> RisultatoCriterio:
    """Verifica un criterio oggettivo a sostituzione dati eseguendo,
    per ogni dataset della griglia, la sostituzione dei valori,
    compilazione ed esecuzione del codice, confrontando il risultato
    con la soluzione di riferimento.

    Se anche un solo dataset non e' verificabile automaticamente
    (dati non individuabili nel codice, o compilazione del codice
    modificato fallita), l'intero criterio viene considerato non
    verificabile: il problema e' strutturale al codice dello studente,
    non ha senso continuare con gli altri dataset.
    """
    esiti: list[EsitoVerificaOggettiva] = []
    for dataset in criterio.dataset:
        esito = _verifica_dataset(criterio, dataset, codice_sorgente)
        if esito is None:
            return _risultato_non_verificabile(criterio)
        esiti.append(esito)

    righe_dettaglio = [
        f"- {esito.nome_dataset}: {'superato' if esito.superato else 'fallito'} "
        f"({esito.dettaglio})"
        for esito in esiti
    ]
    dettaglio = "\n".join(righe_dettaglio)

    tutti_superati = all(esito.superato for esito in esiti)

    return RisultatoCriterio(
        nome_criterio=criterio.nome,
        peso_punti=criterio.peso_punti,
        punti_ottenuti=criterio.peso_punti if tutti_superati else 0,
        dettaglio=dettaglio,
        verificato_automaticamente=True,
    )
