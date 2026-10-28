#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <math.h>
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
            printf("Exemplo: make all-mandelbrot PARS=\"2000 2000 -2.0 1.0 -1.5 1.5 1000\"\n");
            printf("Opcional apos os 7 parametros: <arquivo|-> <num_imagens>\n");
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

    int write_image = (argc >= 9 && strcmp(argv[8], "-") != 0);
    int num_images = (argc >= 10) ? atoi(argv[9]) : 1;
    if (num_images < 1) num_images = 1;

    int tasks_processed = rows / size + (rank < rows % size);

    size_t line_bytes = (size_t)columns * 3;
    size_t total_bytes = (size_t)rows * line_bytes;
    size_t local_bytes = (size_t)tasks_processed * line_bytes;

    if (size > 1 && total_bytes > (size_t)INT_MAX) {
        if (rank == 0)
            fprintf(stderr, "ERRO: imagem de %zu bytes excede INT_MAX; o MPI_Gatherv (contadores int) nao suporta.\n", total_bytes);
        MPI_Finalize();
        return 1;
    }

    /* ---------- Alocacao + pre-touch (fora do cronometro) ---------- */
    unsigned char *local_buffer = (unsigned char *)malloc(local_bytes);
    if (!local_buffer) {
        fprintf(stderr, "[Rank %d] Falha no malloc do local_buffer (%zu bytes)\n", rank, local_bytes);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    memset(local_buffer, 0, local_bytes);

    int *recvcounts = NULL;
    int *displs = NULL;
    unsigned char *gathered_buffer = NULL;
    unsigned char *global_buffer = NULL;   // imagem final (so rank 0)

    if (rank == 0) {
        if (size == 1) {
            global_buffer = local_buffer;  // P=1: o buffer local ja e a imagem
        } else {
            global_buffer = (unsigned char *)malloc(total_bytes);
            gathered_buffer = (unsigned char *)malloc(total_bytes);
            if (!global_buffer || !gathered_buffer) {
                fprintf(stderr, "[Rank 0] Falha no malloc dos buffers globais (%zu bytes)\n", total_bytes);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }
            memset(global_buffer, 0, total_bytes);
            memset(gathered_buffer, 0, total_bytes);

            recvcounts = (int *)malloc((size_t)size * sizeof(int));
            displs = (int *)malloc((size_t)size * sizeof(int));
            if (!recvcounts || !displs) {
                fprintf(stderr, "[Rank 0] Falha ao alocar arrays de coleta\n");
                MPI_Abort(MPI_COMM_WORLD, 1);
            }

            size_t current_displ = 0;
            for (int i = 0; i < size; i++) {
                int lines_this_proc = rows / size + (i < rows % size);
                size_t cnt = (size_t)lines_this_proc * line_bytes;
                recvcounts[i] = (int)cnt;
                displs[i] = (int)current_displ;
                current_displ += cnt;
            }
        }
    }

    double t_comp = 0.0, t_wait = 0.0, t_gather = 0.0, t_reorder = 0.0, t_bar = 0.0;
    double t_total = 0.0, t_io = 0.0;

    MPI_Barrier(MPI_COMM_WORLD);
    double t_section_start = MPI_Wtime();

    for (int img = 0; img < num_images; img++) {
        int local_idx = 0;
        double compute_start = MPI_Wtime();

        for (int i = rank; i < rows; i += size) {
            unsigned char *row_ptr = &local_buffer[(size_t)local_idx * line_bytes];

            for (int e = 0; e < columns; e++) {
                Complex_number c;

                double unidades_largura = maxX - minX;
                double unidades_altura = maxY - minY;

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

                row_ptr[e * 3 + 0] = pixel_value; // R
                row_ptr[e * 3 + 1] = pixel_value; // G
                row_ptr[e * 3 + 2] = pixel_value; // B
            }
            local_idx++;
        }
        t_comp += MPI_Wtime() - compute_start;

        if (size > 1) {
            double w0 = MPI_Wtime();
            MPI_Barrier(MPI_COMM_WORLD);
            t_wait += MPI_Wtime() - w0;

            double g0 = MPI_Wtime();
            MPI_Gatherv(local_buffer, (int)local_bytes, MPI_UNSIGNED_CHAR,
                        gathered_buffer, recvcounts, displs, MPI_UNSIGNED_CHAR,
                        0, MPI_COMM_WORLD);
            t_gather += MPI_Wtime() - g0;

            if (rank == 0) {
                double r0 = MPI_Wtime();
                for (int real_line = 0; real_line < rows; real_line++) {
                    int owner = real_line % size;
                    int line_in_block = real_line / size;

                    size_t src_idx = (size_t)displs[owner] + (size_t)line_in_block * line_bytes;
                    size_t dst_idx = (size_t)real_line * line_bytes;

                    memcpy(&global_buffer[dst_idx], &gathered_buffer[src_idx], line_bytes);
                }
                t_reorder += MPI_Wtime() - r0;
            }
        }
    }

    double b0 = MPI_Wtime();

    MPI_Barrier(MPI_COMM_WORLD);
    
    t_bar += MPI_Wtime() - b0;

    t_total = MPI_Wtime() - t_section_start;
    double t_comm = t_wait + t_gather + t_bar;

    printf("[Rank %d] Finalizado! Processei %d linhas por imagem (%d imagem(ns)).\n", rank, tasks_processed, num_images);

    if (rank == 0) {
        printf("[Rank 0] Imagem montada com sucesso! O array global_buffer tem %zu bytes ordenados.\n", total_bytes);

        if (write_image) {
            char *filename = argv[8];
            double io0 = MPI_Wtime();
            FILE *file_image = fopen(filename, "wb");
            if (file_image) {
                fprintf(file_image, "P6\n%d %d\n255\n", columns, rows);
                fwrite(global_buffer, sizeof(unsigned char), total_bytes, file_image);
                fclose(file_image);
                t_io = MPI_Wtime() - io0;
                printf("[Rank 0] Imagem salva em: %s\n", filename);
            } else {
                perror("[Rank 0] Erro ao abrir arquivo para escrita");
            }
        } else {
            printf("[Rank 0] Imagem nao gravada (sem arquivo ou \"-\").\n");
        }

        free(recvcounts);
        free(displs);
        if (size > 1) {
            free(gathered_buffer);
            free(global_buffer);
        }
    }
    free(local_buffer);

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