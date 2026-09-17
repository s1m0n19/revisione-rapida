#include <stdio.h>

int main(void) {
    int vendite[7] = {5, 60, 42, 38, 70, 12, 45};
    int soglia = 40;
    int eccedenza_totale = 0;

    for (int i = 0; i < 7; i++) {
        if (vendite[i] > soglia) {
            printf("Giorno di punta: giorno %d (%d unita)\n", i, vendite[i])
            eccedenza_totale += vendite[i] - soglia;
        }
    }

    printf("Eccedenza totale nei giorni di punta: %d\n", eccedenza_totale);

    return 0;
}
