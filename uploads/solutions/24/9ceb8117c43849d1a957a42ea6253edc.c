#include <stdlib.h> // for exit()
#include <stdio.h> // for printf() and scanf()

int main() {
    int n;

    // Ask the user for the number of terms
    printf("Enter the number of terms for the Fibonacci sequence: ");
    if (scanf("%d", &n) != 1) {
        printf("Invalid input. Please enter an integer.\n");
        return 1;
    }

    // Validate input
    if (n <= 0) {
        printf("Number of terms must be a positive integer.\n");
        return 1;
    }

    // First two Fibonacci numbers
    unsigned long long first = 0, second = 1, next;

    printf("Fibonacci sequence (%d terms):\n", n);

    for (int i = 0; i < n; i++) {
        if (i == 0) {
            next = first;
        } else if (i == 1) {
            next = second;
        } else {
            next = first + second;
            first = second;
            second = next;
        }
        printf("%llu ", next);
    }
    printf("\n");

    return 0;
}
