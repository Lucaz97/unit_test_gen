#include <stdio.h>
#include <stdlib.h>
#define ARRAY_SIZE 20
int array[] = {5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100};
struct size_key {int size; int key; };



int linearSearch(int * arr, int* arr2, int arr3[][20], struct size_key sk) {
    for (int i = 0; i < sk.size; i++) {
        if (arr[i] == sk.key || arr2[i] == sk.key || arr3[0][i] == sk.key) {
            return i; // Return the index if the key is found
        }
    }
    return -1; // Return -1 if the key is not found
}

int main() {
    struct size_key sk = {ARRAY_SIZE, 55};
    int *array2 = malloc(ARRAY_SIZE * sizeof(int));
    for (int i = 0; i < ARRAY_SIZE; i++) {
        array2[i] = i;
    }
    for (int i = 5; i < ARRAY_SIZE-4; i++) {
        array2[i] = 5;
    }

    int array3[2][ARRAY_SIZE] = {{5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100}, {5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100}};

    int index = linearSearch(array, array2+5, array3+1, sk);

    if (index != -1) {
        printf("Key %d found at index %d\n", sk.key, index);
    } else {
        printf("Key %d not found\n", sk.key);
    }
    
    return 0;
}