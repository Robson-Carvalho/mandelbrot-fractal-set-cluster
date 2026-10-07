#ifndef COMPLEX_H
#define COMPLEX_H

typedef struct {
    double real;
    double imag;
} Complex_number;

double real_part(Complex_number number);
double imag_part(Complex_number number);
void print_complex(Complex_number number);


#endif
