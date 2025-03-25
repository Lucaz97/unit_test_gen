#include <stdio.h>
#include <stdlib.h>
#define ARRAY_SIZE 20


int linearSearch(int * arr, int key, int size) {
    for (int i = 0; i < size+1; i++) {
        if (arr[i] == key) {
            return i; // Return the index if the key is found
        }
    }
    return -1; // Return -1 if the key is not found
}

int main() {
    int key = 7;
    int *array = malloc(ARRAY_SIZE * sizeof(int));
    int index = linearSearch(array, key, ARRAY_SIZE);

    if (index != -1) {
        printf("Key %d found at index %d\n", key, index);
    } else {
        printf("Key %d not found\n", key);
    }
    
    return 0;
}