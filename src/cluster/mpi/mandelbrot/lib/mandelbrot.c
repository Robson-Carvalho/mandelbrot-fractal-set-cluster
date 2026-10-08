#include <stdio.h>
#include "complex.h"
#include "mandelbrot.h"

Mandelbrot_check_return check_mandelbrot(Complex_number c, int max_iter){
    double fr = 0.0, fi = 0.0;

    for(int i = 0; i < max_iter; i++){
        // (fr + fi*i)² + c  →  (fr²-fi²) + (2·fr·fi)·i + c
        double fr2 = fr * fr;
        double fi2 = fi * fi;
        fi = 2.0 * fr * fi + c.imag;
        fr = fr2 - fi2 + c.real;

        if (fr * fr + fi * fi > 4.0) {
            Complex_number fval = {fr, fi};
            return (Mandelbrot_check_return){0, fval, i+1};
        }
    }

    Complex_number fval = {fr, fi};
    return (Mandelbrot_check_return){1, fval, max_iter};
}
