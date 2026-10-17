#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <sys/resource.h>
#include "complex.h"
#include "mandelbrot.h"

static double elapsed_s(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / 1e9;
}

int main(int argc, char *argv[]) {
    if (argc < 9) {
        printf("Uso: %s <rows> <cols> <minX> <maxX> <minY> <maxY> <max_iter> <output_filename>\n", argv[0]);
        return 1;
    }

    int columns = atoi(argv[1]);
    int rows = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);
    char *filename = argv[8];

    size_t total_bytes = (size_t)rows * (size_t)columns * 3;
    unsigned char *buffer = (unsigned char *)malloc(total_bytes);
    if (!buffer) {
        fprintf(stderr, "Falha no malloc de %zu bytes\n", total_bytes);
        return 1;
    }
    memset(buffer, 0, total_bytes);

    struct timespec t_start, t_end;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    double unidades_largura = maxX - minX;
    double unidades_altura = maxY - minY;
    size_t idx = 0;

    for (int i = 0; i < rows; i++) {
        for (int e = 0; e < columns; e++) {
            Complex_number c;

            double proporcao_x = (e / (double)columns);
            double proporcao_y = (i / (double)rows);

            double deslocamento_x = unidades_largura * proporcao_x;
            double deslocamento_y = unidades_altura * proporcao_y;

            c.real = minX + deslocamento_x;
            c.imag = maxY - deslocamento_y;

            Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

            unsigned char pixel_value;
            if (result.check == 1 || result.iterations_to_scape == max_iter) {
                pixel_value = 0;
            } else {
                int iter = result.iterations_to_scape;
                pixel_value = (unsigned char)(sin(0.1 * iter) * 127.5 + 127.5);
            }

            buffer[idx++] = pixel_value; // R
            buffer[idx++] = pixel_value; // G
            buffer[idx++] = pixel_value; // B
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t_end);
    double t_comp = elapsed_s(t_start, t_end);

    struct timespec io_start, io_end;
    clock_gettime(CLOCK_MONOTONIC, &io_start);
    FILE *file_image = fopen(filename, "wb");
    if (!file_image) {
        perror("Erro ao abrir arquivo para escrita");
        return 1;
    }
    fprintf(file_image, "P6\n%d %d\n255\n", columns, rows);
    fwrite(buffer, sizeof(unsigned char), total_bytes, file_image);
    fclose(file_image);
    clock_gettime(CLOCK_MONOTONIC, &io_end);
    double t_io = elapsed_s(io_start, io_end);

    free(buffer);

    printf("\nSerial\n");
    printf("  Tcomp  = %.6f s\n", t_comp);
    printf("  Ttotal = %.6f s\n", t_comp);
    printf("  Tio    = %.6f s\n", t_io);

    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    printf("\n=== RECURSOS DO SISTEMA ===\n");
    printf("Memoria maxima usada (Max RSS)   : %ld KB\n", usage.ru_maxrss);
    printf("Page faults (Soft/Recuperaveis)  : %ld\n", usage.ru_minflt);
    printf("Page faults (Hard/Disco)         : %ld\n", usage.ru_majflt);
    printf("Trocas de contexto voluntarias   : %ld\n", usage.ru_nvcsw);
    printf("Trocas de contexto involuntarias : %ld\n", usage.ru_nivcsw);
    printf("===========================\n");

    return 0;
}