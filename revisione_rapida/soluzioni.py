"""Soluzioni di riferimento per gli esercizi, come funzioni pure.

Le funzioni di questo modulo vengono richiamate dinamicamente per nome
(es. la stringa "soluzioni.parte1" nel campo soluzione_riferimento
della griglia), quindi i loro nomi devono restare identici a quelli
usati nei file griglia.yaml degli esercizi.
"""

SOGLIA_GIORNO_DI_PUNTA = 40


def parte1(vendite: list[int]) -> dict:
    """Soluzione di riferimento per l'esercizio 'Giorni di punta'.

    Un giorno e' di punta se le vendite superano SOGLIA_GIORNO_DI_PUNTA
    (strettamente, non nel caso limite di uguaglianza).

    Ritorna un dizionario con:
    - 'giorni_punta': indici (0-6) dei giorni di punta
    - 'eccedenza_totale': somma delle vendite eccedenti la soglia nei
      giorni di punta
    """
    giorni_punta = [
        indice
        for indice, vendite_giorno in enumerate(vendite)
        if vendite_giorno > SOGLIA_GIORNO_DI_PUNTA
    ]
    eccedenza_totale = sum(
        vendite_giorno - SOGLIA_GIORNO_DI_PUNTA
        for vendite_giorno in vendite
        if vendite_giorno > SOGLIA_GIORNO_DI_PUNTA
    )

    return {"giorni_punta": giorni_punta, "eccedenza_totale": eccedenza_totale}
