#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <sys/resource.h>
#include "complex.h"
#include "mandelbrot.h"

int mandelbrot(int px, int py, int width, int height, double minX, double maxX, double minY, double maxY, int max_iter) {
    Complex_number c;

    double unidades_largura = maxX - minX; 
    double unidades_altura = maxY - minY; 

    double proporcao_x = (px / (double)width); 
    double proporcao_y = (py / (double)height); 

    double deslocamento_x = unidades_largura * proporcao_x; 
    double deslocamento_y = unidades_altura * proporcao_y;

    double enquadramento_eixo_x = minX + deslocamento_x;
    double enquadramento_eixo_y = maxY - deslocamento_y;

    c = (Complex_number){enquadramento_eixo_x, enquadramento_eixo_y};

    Mandelbrot_check_return result = check_mandelbrot(c, max_iter);
    
    return result.iterations_to_scape;
}

int main(int argc, char *argv[]) {
    // Voltamos a exigir 8 argumentos (o último é o nome do arquivo da imagem)
    if (argc < 9) {
        printf("Uso: %s <width> <height> <minX> <maxX> <minY> <maxY> <max_iter> <output_filename>\n", argv[0]);
        return 1;
    }

    int width = atoi(argv[1]);
    int height = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);
    char *filename = argv[8];

    printf("Iniciando cálculos e geração da imagem...\n");
    printf("Resolucao: %dx%d | Iteracoes: %d\n", width, height, max_iter);
    printf("Salvando em: %s\n", filename);

    FILE *file_image = fopen(filename, "wb");
    if (!file_image) {
        perror("Erro ao abrir arquivo para escrita");
        return 1;
    }

    // Cabeçalho do formato PPM
    fprintf(file_image, "P6\n%d %d\n255\n", width, height);

    // --- Início da medição de tempo ---
    struct timespec t_start, t_end;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    for (int py = 0; py < height; py++) {
         for (int px = 0; px < width; px++) {
            int iter = mandelbrot(px, py, width, height, minX, maxX, minY, maxY, max_iter);
            
            unsigned char r, g, b;

            // Dentro do limite (pertence ao conjunto - Preto)
            if (iter == max_iter) { 
                r = g = b = 0;
            } 
            // Fora do limite (Divergiu - Colorido)
            else {
                // Cálculo de cor suave baseado nas iterações
                unsigned char tom = (unsigned char)(sin(0.1 * iter) * 127.5 + 127.5);
                r = g = b = tom;
            }       

            // Escreve os pixels no arquivo
            fputc(r, file_image);
            fputc(g, file_image);
            fputc(b, file_image);
         }
    }

    // --- Fim da medição de tempo ---
    clock_gettime(CLOCK_MONOTONIC, &t_end);
    double elapsed = (t_end.tv_sec - t_start.tv_sec) +
                     (t_end.tv_nsec - t_start.tv_nsec) / 1e9;
    
    fclose(file_image);

    // -------------------------------------------------
    // Relatórios de Execução e Recursos
    printf("\n=== RESULTADOS ===\n");
    printf("Tempo de processamento (CPU + I/O) : %.6f segundos\n", elapsed);

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
