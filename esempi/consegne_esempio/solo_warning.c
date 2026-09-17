#include <stdio.h>

/*
 * Dichiara una variabile mai utilizzata: con "-Wall" il compilatore
 * segnala un warning ("unused variable"), ma il programma resta
 * valido e produce comunque un eseguibile. Rappresenta il caso
 * "successo con soli warning".
 */
int main(void) {
    int non_usata = 42;
    printf("Ciao mondo\n");
    return 0;
}
