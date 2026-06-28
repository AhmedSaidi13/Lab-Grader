#include <stdio.h>

int main(void)
{
    long double x, y;
    printf("Entrez le premier nombre : ");
    scanf("%Lf", &x);
    printf("Entrez le deuxième nombre : ");
    scanf("%Lf", &y);
    printf("La moyenne est : %Lf\n", (x + y) / 2);
    return 0;
}   