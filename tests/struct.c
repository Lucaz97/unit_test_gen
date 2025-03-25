#include <stdio.h>

// Define the rgb struct
typedef struct {
    int red;
    int green;
    int blue;
} rgb;

// Function to calculate the average color
rgb averageColor(rgb color1, rgb color2) {
    rgb average;
    average.red = (color1.red + color2.red) / 2;
    average.green = (color1.green + color2.green) / 2;
    average.blue = (color1.blue + color2.blue) / 2;
    return average;
}

int main() {
    // Example usage
    rgb color1 = {255, 0, 0}; // Red color
    rgb color2 = {0, 0, 255}; // Blue color

    rgb average = averageColor(color1, color2);

    printf("Average color: R:%d G:%d B:%d\n", average.red, average.green, average.blue);

    return 0;
}