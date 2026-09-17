#include <stdio.h>

int main(void) {
    int vendite[7];
    int soglia = 40;
    int eccedenza_totale = 0;

    vendite[0] = 40;
    vendite[1] = 41;
    vendite[2] = 39;
    vendite[3] = 40;
    vendite[4] = 45;
    vendite[5] = 40;
    vendite[6] = 12;

    for (int i = 0; i < 7; i++) {
        if (vendite[i] > soglia) {
            printf("Giorno di punta: giorno %d (%d unita)\n", i, vendite[i]);
            eccedenza_totale += vendite[i] - soglia;
        }
    }

    printf("Eccedenza totale nei giorni di punta: %d\n", eccedenza_totale);

    return 0;
}
