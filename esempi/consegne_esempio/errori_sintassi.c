#include <stdio.h>

/*
 * Contiene un errore di sintassi deliberato (punto e virgola mancante
 * dopo la dichiarazione di "x"): rappresenta il caso in cui la
 * compilazione fallisce e non produce alcun eseguibile.
 */
int main(void) {
    int x = 5
    printf("%d\n", x);
    return 0;
}
