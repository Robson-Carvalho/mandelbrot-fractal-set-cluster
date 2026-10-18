#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "lib/complex.h"
#include "lib/mandelbrot.h"

static void reduce_stats(const char *nome, double v, int rank, int size) {
    double sum = 0.0, sumsq = 0.0, mx = 0.0, mn = 0.0, sq = v * v;
    MPI_Reduce(&v, &sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&v, &mx, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&v, &mn, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&sq, &sumsq, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    if (rank == 0) {
        double mean = sum / size;
        double std = sqrt(fmax(0.0, (sumsq / size) - (mean * mean)));  // desvio populacional entre ranks
        printf("  %-7s: Tmax=%.6f s | Tmin=%.6f s | Media=%.6f s | Desvio=%.6f s\n",
               nome, mx, mn, mean, std);
    }
}

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
            printf("Uso: make all-mandelbrot PARS=\"<largura> <altura> <minX> <maxX> <minY> <maxY> <max_iter>\"\n");
        }
        MPI_Finalize();
        return -1;
    }

    int columns = atoi(argv[1]);
    int rows = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);

    // Opcional: <arquivo|-> <num_imagens>. "-" nao grava a imagem.
    int write_image = !(argc > 8 && strcmp(argv[8], "-") == 0);
    int num_images = (argc >= 10) ? atoi(argv[9]) : 1;
    if (num_images < 1) num_images = 1;

    int my_rows = rows / size + (rank < rows % size);

    // tamanho da linha
    size_t line_bytes = (size_t)columns * 3;
    size_t total_image_bytes = (size_t)rows * line_bytes;

    // tamanho parcial da imagem - apenas o tamanho calculado das linhas por esse processo
    unsigned char *my_lines = (unsigned char *)malloc(my_rows * line_bytes * sizeof(unsigned char));
    if (my_lines == NULL) {
        fprintf(stderr, "Rank %d: falha ao alocar my_lines\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    double t_comp = 0.0, t_wait = 0.0, t_gather = 0.0, t_bar = 0.0;
    double t_total = 0.0, t_io = 0.0;
    double t_reorder = 0.0; // medido apenas no rank 0 (memcpy de reordenação), fica dentro do Ttotal

    // Buffers de coleta alocados fora do cronometro (reutilizados entre imagens)
    unsigned char *full_image = NULL;
    unsigned char *gathered_buffer = NULL;
    int *chunk_sizes_in_bytes = NULL;
    int *byte_offsets_in_buffer = NULL;

    if (rank == 0) {
        if (size == 1) {
            full_image = my_lines; // P=1: o buffer local ja contem todas as linhas ordenadas
        } else {
            full_image = (unsigned char *)malloc(total_image_bytes);
            gathered_buffer = (unsigned char *)malloc(total_image_bytes);

            if (full_image == NULL || gathered_buffer == NULL) {
                fprintf(stderr, "Rank %d: falha ao alocar buffers de imagem\n", rank);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }

            // Arrays para o MPI_Gatherv saber o tamanho do bloco de cada processo
            chunk_sizes_in_bytes = (int *)malloc(size * sizeof(int));
            byte_offsets_in_buffer = (int *)malloc(size * sizeof(int));

            if (chunk_sizes_in_bytes == NULL || byte_offsets_in_buffer == NULL) {
                fprintf(stderr, "Rank %d: falha ao alocar arrays de coleta\n", rank);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }

            int accumulated_bytes = 0;
            for (int process_id = 0; process_id < size; process_id++) {
                int lines_this_process = rows / size + (process_id < rows % size);
                int bytes_this_process = lines_this_process * (int)line_bytes;
                chunk_sizes_in_bytes[process_id] = bytes_this_process;
                byte_offsets_in_buffer[process_id] = accumulated_bytes;
                accumulated_bytes += bytes_this_process;
            }
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_section_start = MPI_Wtime();

    for (int img = 0; img < num_images; img++) {
        int local_idx = 0;
        double compute_start = MPI_Wtime();
        for (int i = rank; i < rows; i += size) {
            int offset = local_idx * line_bytes;
            unsigned char *row_ptr = &my_lines[offset];

            for (int e = 0; e < columns; e++) {
                Complex_number c;
                c.real = minX + ((double)e / columns) * (maxX - minX);
                c.imag = maxY - ((double)i / rows) * (maxY - minY);

                Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

                unsigned char color_intensity;

                if (result.check == 1 || result.iterations_to_scape == max_iter) {
                    color_intensity = 0;
                } else {
                    color_intensity = (unsigned char)(sin(0.1 * result.iterations_to_scape) * 127.5 + 127.5);
                }
                row_ptr[e * 3 + 0] = color_intensity;
                row_ptr[e * 3 + 1] = color_intensity;
                row_ptr[e * 3 + 2] = color_intensity;
            }
            local_idx++;
        }
        t_comp += MPI_Wtime() - compute_start;

        if (size > 1) {
            double w0 = MPI_Wtime();
            MPI_Barrier(MPI_COMM_WORLD);
            t_wait += MPI_Wtime() - w0;

            double g0 = MPI_Wtime();
            MPI_Gatherv(
                my_lines,
                my_rows * (int)line_bytes,
                MPI_UNSIGNED_CHAR,
                gathered_buffer,
                chunk_sizes_in_bytes,
                byte_offsets_in_buffer,
                MPI_UNSIGNED_CHAR,
                0,
                MPI_COMM_WORLD
            );
            t_gather += MPI_Wtime() - g0;

            if (rank == 0) {
                double reorder_start = MPI_Wtime();
                for (int real_line = 0; real_line < rows; real_line++) {
                    int owner = real_line % size;
                    int line_in_block = real_line / size;

                    size_t source_index = byte_offsets_in_buffer[owner] + line_in_block * line_bytes;
                    size_t destination_index = real_line * line_bytes;

                    unsigned char *source = &gathered_buffer[source_index];
                    unsigned char *destination = &full_image[destination_index];

                    memcpy(destination, source, line_bytes);
                }
                t_reorder += MPI_Wtime() - reorder_start;
            }
        }
    }

    double b0 = MPI_Wtime();
    MPI_Barrier(MPI_COMM_WORLD);
    t_bar += MPI_Wtime() - b0;

    t_total = MPI_Wtime() - t_section_start;
    double t_comm = t_wait + t_gather + t_bar;

    if (rank == 0) {
        if (write_image) {
            char *filename = (argc > 8) ? argv[8] : "mandelbrot_mpi.ppm";
            double io0 = MPI_Wtime();
            FILE *file_image = fopen(filename, "wb");
            if (file_image) {
                fprintf(file_image, "P6\n%d %d\n255\n", columns, rows);
                fwrite(full_image, sizeof(unsigned char), total_image_bytes, file_image);
                fclose(file_image);
                t_io = MPI_Wtime() - io0;
                printf("Imagem salva com sucesso em '%s'\n", filename);
            }
        }
        if (size > 1) {
            free(full_image);
            free(gathered_buffer);
            free(chunk_sizes_in_bytes);
            free(byte_offsets_in_buffer);
        }
    }
    free(my_lines);

    printf("\nRank %d\n", rank);
    printf("  Tcomp  = %.6f s\n", t_comp);
    printf("  Tcomm  = %.6f s\n", t_comm);
    printf("  Twait  = %.6f s\n", t_wait);
    printf("  Tgather= %.6f s\n", t_gather);
    printf("  Tbar   = %.6f s\n", t_bar);
    printf("  Ttotal = %.6f s\n", t_total);
    if (rank == 0) {
        if (size > 1) {
            printf("  Treorder (so rank 0, dentro do Ttotal) = %.6f s\n", t_reorder);
        }
        printf("  Tio    = %.6f s\n", t_io);
    }

    if (rank == 0) printf("\nResumo estatístico entre os %d ranks (imagens=%d)\n", size, num_images);
    reduce_stats("Tcomp", t_comp, rank, size);
    reduce_stats("Tcomm", t_comm, rank, size);
    reduce_stats("Twait", t_wait, rank, size);
    reduce_stats("Tgather", t_gather, rank, size);
    reduce_stats("Tbar", t_bar, rank, size);
    reduce_stats("Ttotal", t_total, rank, size);

    if (rank == 0) {
        printf("  Tio (rank 0, fora do Ttotal): %.6f s\n", t_io);
        printf("\nResolução MPI_Wtick: %.9f s\n", MPI_Wtick());
    }

    fflush(stdout);
    MPI_Finalize();
    return 0;
}