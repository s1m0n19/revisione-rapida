"""Test delle soluzioni di riferimento per gli esercizi."""

from revisione_rapida.soluzioni import parte1


def test_parte1_nessun_giorno_sopra_soglia():
    """Se nessuna vendita supera la soglia, non ci sono giorni di punta
    e l'eccedenza totale e' zero."""
    risultato = parte1([10, 20, 15, 30, 25, 18, 22])

    assert risultato == {"giorni_punta": [], "eccedenza_totale": 0}


def test_parte1_tutti_i_giorni_sopra_soglia():
    """Se tutte le vendite superano la soglia, tutti gli indici devono
    comparire tra i giorni di punta e l'eccedenza deve sommarli tutti."""
    risultato = parte1([41, 42, 50, 45, 60, 41, 100])

    assert risultato == {
        "giorni_punta": [0, 1, 2, 3, 4, 5, 6],
        "eccedenza_totale": 99,
    }


def test_parte1_caso_limite_esatto_a_quaranta_non_conta():
    """Un valore esattamente uguale alla soglia (40) non deve essere
    considerato un giorno di punta: la soglia va superata, non solo
    raggiunta."""
    risultato = parte1([40, 40, 41, 39, 40, 45, 40])

    assert risultato == {"giorni_punta": [2, 5], "eccedenza_totale": 6}
