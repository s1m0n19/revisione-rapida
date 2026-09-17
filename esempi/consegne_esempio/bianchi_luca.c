#include <stdio.h>

int main() {
    int vendite[7] = {10, 20, 15, 30, 25, 18, 22};
    int i;
    int eccedenza = 0;
    int contatore_giorni_punta = 0;
    int totale_settimana;

    for (i = 0; i <= 6; i++) {
        if (vendite[i] > 40) {
            printf("Giorno di punta: giorno %d (%d unita)\n", i, vendite[i]);
            eccedenza = eccedenza + (vendite[i] - 40);
            contatore_giorni_punta++;
        }
    }

    printf("Eccedenza totale nei giorni di punta: %d\n", eccedenza);

    return 0;
}
