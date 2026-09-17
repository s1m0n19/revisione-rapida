#include <stdio.h>

/*
 * Parte 1 - Giorni di punta
 * Analizza le vendite settimanali delle Cuffie Bluetooth e individua
 * i giorni in cui le vendite superano la soglia di 40 unita.
 */

int main(void) {
    int vendite[7] = {12, 45, 33, 50, 28, 41, 39};
    int soglia = 40;
    int eccedenza_totale = 0;
    const char *nomi_giorni[7] = {
        "Lunedi", "Martedi", "Mercoledi", "Giovedi",
        "Venerdi", "Sabato", "Domenica"
    };

    for (int i = 0; i < 7; i++) {
        if (vendite[i] > soglia) {
            int eccedenza = vendite[i] - soglia;
            printf("Giorno di punta: %s (%d unita)\n", nomi_giorni[i], vendite[i]);
            eccedenza_totale += eccedenza;
        }
    }

    printf("Eccedenza totale nei giorni di punta: %d\n", eccedenza_totale);

    return 0;
}
