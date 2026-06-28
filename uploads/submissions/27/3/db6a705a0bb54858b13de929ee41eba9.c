#include <stdio.h>

int main(void)
{
    int x, y;
    printf("Entrez le premier nombre : ");
    scanf("%d", &x);
    printf("Entrez le deuxième nombre : ");
    scanf("%d", &y);
    printf("La moyenne est : %d\n", (x + y) / 2);
    return 0;
}   