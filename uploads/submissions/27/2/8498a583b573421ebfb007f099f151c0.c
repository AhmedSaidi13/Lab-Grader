#include <stdio.h>

int main() 
{
    long double nombre1, nombre2, somme, moyenne;

    // Saisie des deux nombres
    printf("Entrez le premier nombre : ");
    scanf("%Lf", &nombre1);

    printf("Entrez le deuxième nombre : ");
    scanf("%Lf", &nombre2);

    // Calcul
    somme = nombre1 + nombre2;
    moyenne = somme / 2;

    // Affichage
    printf("La moyenne des deux nombres est : %.2Lf\n", moyenne);

    return 0;
}