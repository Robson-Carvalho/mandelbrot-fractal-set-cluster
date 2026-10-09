#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "lib/complex.h"
#include "lib/mandelbrot.h"

int main(int argc, char **argv) {
    int rank, size;
    int rc = MPI_Init(&argc, &argv);
    if (rc != MPI_SUCCESS) {
        printf("Error starting MPI program.\n");
        MPI_Abort(MPI_COMM_WORLD, rc);
        return -1;
    }

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 8) {
        if (rank == 0) {
            printf("Uso: make all-mandelbrot PARS=\"<rows> <cols> <minX> <maxX> <minY> <maxY> <max_iter>\"\n");
        }
        MPI_Finalize();
        return -1;
    }

    int rows = atoi(argv[1]);
    int columns = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);

    int my_rows = 0;
    for (int i = rank; i < rows; i += size) {
        my_rows++;
    }

    size_t line_bytes = (size_t)columns * 3;
    unsigned char *my_lines = (unsigned char *)malloc(my_rows * line_bytes * sizeof(unsigned char));

    int local_idx = 0;
    for (int i = rank; i < rows; i += size) {
        unsigned char *row_ptr = &my_lines[local_idx * line_bytes];
        for (int e = 0; e < columns; e++) {
            Complex_number c;
            c.real = minX + ((double)e / columns) * (maxX - minX);
            c.imag = maxY - ((double)i / rows) * (maxY - minY);

            Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

            unsigned char tom;
            if (result.check == 1) {
                tom = 0;
            } else {
                tom = (unsigned char)(sin(0.1 * result.iterations_to_scape) * 127.5 + 127.5);
            }
            row_ptr[e * 3 + 0] = tom;
            row_ptr[e * 3 + 1] = tom;
            row_ptr[e * 3 + 2] = tom;
        }
        local_idx++;
    }

    unsigned char *full_image = NULL;
    unsigned char *gathered_buffer = NULL;
    int *recvcounts = NULL;
    int *displs = NULL;

    if (rank == 0) {
        full_image = (unsigned char *)malloc((size_t)rows * line_bytes);
        gathered_buffer = (unsigned char *)malloc((size_t)rows * line_bytes);
        recvcounts = (int *)malloc(size * sizeof(int));
        displs = (int *)malloc(size * sizeof(int));

        int offset = 0;
        for (int p = 0; p < size; p++) {
            int p_rows = 0;
            for (int i = p; i < rows; i += size) p_rows++;
            recvcounts[p] = p_rows * (int)line_bytes;
            displs[p] = offset;
            offset += recvcounts[p];
        }
    }

    MPI_Gatherv(my_lines, my_rows * (int)line_bytes, MPI_UNSIGNED_CHAR,
                gathered_buffer, recvcounts, displs, MPI_UNSIGNED_CHAR,
                0, MPI_COMM_WORLD);

    if (rank == 0) {
        for (int p = 0; p < size; p++) {
            unsigned char *src = &gathered_buffer[displs[p]];
            int row_counter = 0;
            for (int r = p; r < rows; r += size) {
                unsigned char *dst = &full_image[(size_t)r * line_bytes];
                for (size_t b = 0; b < line_bytes; b++) {
                    dst[b] = src[row_counter * line_bytes + b];
                }
                row_counter++;
            }
        }
    }

    if (rank == 0) {
        char *filename = (argc > 8) ? argv[8] : "mandelbrot_mpi.ppm";
        FILE *file_image = fopen(filename, "wb");
        if (file_image) {
            fprintf(file_image, "P6\n%d %d\n255\n", columns, rows);
            fwrite(full_image, sizeof(unsigned char), (size_t)rows * line_bytes, file_image);
            fclose(file_image);
            printf("Imagem salva com sucesso em '%s'\n", filename);
        }
        free(full_image);
        free(gathered_buffer);
        free(recvcounts);
        free(displs);
    }

    free(my_lines);
    MPI_Finalize();
    return 0;
}