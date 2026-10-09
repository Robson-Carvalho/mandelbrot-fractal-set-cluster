#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "lib/complex.h"
#include "lib/mandelbrot.h"

int main(int argc, char **argv) {
    int rank, size;
    char hostname[256];

    int rc = MPI_Init(&argc, &argv);

    if (rc != MPI_SUCCESS)
    {
        printf("Error starting MPI program.\n");
        MPI_Abort(MPI_COMM_WORLD, rc);
        return -1;
    }

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 8) {
        printf("Uso: make all-spmd PARS=\"<rows> <cols> <minX> <maxX> <minY> <maxY> <max_iter>\"\n");
        printf("Exemplo: make all-spmd PARS=\"2000 2000 -2.0 1.0 -1.5 1.5 1000\"\n");
        return -1;
    }

    int rows = atoi(argv[1]);
    int columns = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);

    int lines_per_rank = rows / size;
    int start_row = rank * lines_per_rank;
    int end_row = (rank == size - 1) ? rows : start_row + lines_per_rank;

    int tasks_processed = end_row - start_row;
    int local_buffer_size = tasks_processed * columns;
    unsigned char *local_buffer = (unsigned char *)malloc(local_buffer_size);

    int buffer_index = 0;

    for (int i = start_row; i < end_row; i++) 
    {
        for(int e = 0; e < columns; e += 1){
            Complex_number c;
            c.real = minX + (e * (maxX - minX)) / columns;
            c.imag = minY + (i * (maxY - minY)) / rows;

            Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

            unsigned char pixel_value;

            if (result.check == 1) { 
                pixel_value = 0;
            } else {
                int iter = result.iterations_to_scape;
                pixel_value = (unsigned char)(sin(0.1 * iter) * 127.5 + 127.5);
            }

            local_buffer[buffer_index++] = pixel_value;
        }
    }

    // Referencias para buffers locais de cada rank e global_buffer (Rank 0)
    int *recvcounts = NULL;
    int *displs = NULL;
    unsigned char *global_buffer = NULL;

    // Rank 0 Reorganizando Imagem calculada via Gather
    if (rank == 0) {
        recvcounts = (int*) malloc(size * sizeof(int));
        displs = (int*) malloc(size * sizeof(int));
        global_buffer = (unsigned char*) malloc(rows * columns);

        int current_displ = 0;
        for (int i = 0; i < size; i++) {
            int r_start = i * lines_per_rank;
            int r_end = (i == size - 1) ? rows : r_start + lines_per_rank;
            
            recvcounts[i] = (r_end - r_start) * columns; 
            displs[i] = current_displ;
            current_displ += recvcounts[i];
        }
    }

    // Gather de pedaços da imagem calculados pelos processos independentes
    MPI_Gatherv(local_buffer, local_buffer_size, MPI_UNSIGNED_CHAR,
                global_buffer, recvcounts, displs, MPI_UNSIGNED_CHAR,
                0, MPI_COMM_WORLD);

    printf("[Rank %d] Finalizado! Processei %d linhas.\n", rank, tasks_processed);

    if (rank == 0) {
        printf("[Rank 0] Imagem montada com sucesso! O array global_buffer tem %d bytes ordenados.\n", rows * columns);

        free(recvcounts);
        free(displs);
        free(global_buffer);
    }

    free(local_buffer);

    fflush(stdout);
    MPI_Finalize();

    return 0;
}