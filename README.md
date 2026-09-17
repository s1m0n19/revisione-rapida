# revisione-rapida

Assistente che aiuta a correggere codice C degli studenti: compila i sorgenti, esegue i test, valuta il codice con l'aiuto di un LLM secondo una griglia definita dal docente e propone un voto che il docente rivede e conferma.

## Stato attuale

Il progetto è agli inizi (MVP in sviluppo). Al momento è supportato solo il linguaggio C e non è presente alcuna interfaccia grafica.

## Come si esegue

TODO

## Struttura del progetto

```
revisione-rapida/
├── README.md
├── .gitignore
├── requirements.txt
├── revisione_rapida/
│   ├── __init__.py
│   ├── compiler.py       (vuoto, solo docstring del modulo in italiano che
│   │                       spiega cosa conterrà: compilazione file C e
│   │                       parsing errori/warning)
│   ├── test_runner.py    (vuoto, docstring: esecuzione test case e confronto
│   │                       output)
│   ├── grading.py        (vuoto, docstring: chiamata API Claude per
│   │                       valutazione qualitativa)
│   ├── griglia.py        (vuoto, docstring: caricamento e validazione file
│   │                       griglia YAML)
│   ├── report.py         (vuoto, docstring: generazione report per studente)
│   └── main.py           (vuoto, docstring: orchestrazione del flusso
│                           completo)
├── tests/
│   ├── __init__.py
│   ├── test_compiler.py      (vuoto)
│   ├── test_test_runner.py   (vuoto)
│   └── test_grading.py       (vuoto)
├── esempi/
│   ├── esercizio_esempio/
│   │   ├── testo.md       (placeholder: "# Testo esercizio di esempio")
│   │   ├── griglia.yaml   (vuoto)
│   │   └── test_case.yaml (vuoto)
│   └── consegne_esempio/
│       └── (cartella vuota, aggiungerò io i file .c di esempio)
└── docs/
    └── formato_griglia.md (placeholder: "# Formato della griglia di
                              valutazione", da completare in seguito)
```
