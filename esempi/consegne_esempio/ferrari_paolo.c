#include <stdio.h>

int main(void) {
    int a[7] = {50, 60, 20, 45, 30, 70, 10};
    int t = 0;
    for (int j = 0; j < 7; j++) {
        if (a[j] > 40) {
            printf("Giorno di punta: giorno %d (%d unita)\n", j, a[j]);
            t = t + a[j] - 40;
        }
    }
    printf("Eccedenza totale nei giorni di punta: %d\n", t);
    return 0;
}
