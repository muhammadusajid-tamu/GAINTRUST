#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * A simple C program demonstrating various C features
 * that need to be transpiled to Rust.
 */

// Structure definition
typedef struct {
    char* name;
    int age;
    float score;
} Student;

// Function to create a new student
Student* create_student(const char* name, int age, float score) {
    Student* student = (Student*)malloc(sizeof(Student));
    if (student == NULL) {
        return NULL;
    }
    
    student->name = (char*)malloc(strlen(name) + 1);
    if (student->name == NULL) {
        free(student);
        return NULL;
    }
    
    strcpy(student->name, name);
    student->age = age;
    student->score = score;
    
    return student;
}

// Function to free a student
void free_student(Student* student) {
    if (student != NULL) {
        if (student->name != NULL) {
            free(student->name);
        }
        free(student);
    }
}

// Function to print student information
void print_student(const Student* student) {
    if (student == NULL) {
        printf("Student is NULL\n");
        return;
    }
    
    printf("Name: %s, Age: %d, Score: %.2f\n", 
           student->name, student->age, student->score);
}

// Function to calculate average score
float calculate_average(Student** students, int count) {
    if (students == NULL || count <= 0) {
        return 0.0f;
    }
    
    float sum = 0.0f;
    int valid_count = 0;
    
    for (int i = 0; i < count; i++) {
        if (students[i] != NULL) {
            sum += students[i]->score;
            valid_count++;
        }
    }
    
    return valid_count > 0 ? sum / valid_count : 0.0f;
}

// Main function
int main() {
    // Create an array of students
    const int NUM_STUDENTS = 3;
    Student** students = (Student**)malloc(NUM_STUDENTS * sizeof(Student*));
    
    if (students == NULL) {
        printf("Memory allocation failed\n");
        return 1;
    }
    
    // Initialize students
    students[0] = create_student("Alice", 20, 85.5f);
    students[1] = create_student("Bob", 22, 92.0f);
    students[2] = create_student("Charlie", 21, 78.5f);
    
    // Print student information
    for (int i = 0; i < NUM_STUDENTS; i++) {
        print_student(students[i]);
    }
    
    // Calculate and print average score
    float average = calculate_average(students, NUM_STUDENTS);
    printf("Average score: %.2f\n", average);
    
    // Free memory
    for (int i = 0; i < NUM_STUDENTS; i++) {
        free_student(students[i]);
    }
    free(students);
    
    return 0;
}
