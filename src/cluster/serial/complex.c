#include <stdio.h>
#include "complex.h"

double real_part(Complex_number number){
	double real = number.real;
	return real;
}


double imag_part(Complex_number number){
	double imag = number.imag;
	return imag;
}

void print_complex(Complex_number number){
	printf("Complex Number: %.2f + j%.2f\n", number.real, number.imag);
	return;
}


