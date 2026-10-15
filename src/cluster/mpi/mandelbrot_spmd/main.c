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
        if (rank == 0) {
            printf("Uso: make all-spmd PARS=\"<rows> <cols> <minX> <maxX> <minY> <maxY> <max_iter>\"\n");
            printf("Exemplo: make all-spmd PARS=\"2000 2000 -2.0 1.0 -1.5 1.5 1000\"\n");
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

    int lines_per_rank = rows / size;
    int start_row = rank * lines_per_rank;
    int end_row = (rank == size - 1) ? rows : start_row + lines_per_rank;

    int tasks_processed = end_row - start_row;
    int local_buffer_size = tasks_processed * columns * 3;
    unsigned char *local_buffer = (unsigned char *)malloc(local_buffer_size);

    int buffer_index = 0;

    double t_comp = 0.0;
    double t_comm = 0.0;
    double t_total = 0.0;

    MPI_Barrier(MPI_COMM_WORLD);
    double t_section_start = MPI_Wtime();

    double compute_start = MPI_Wtime();
    for (int i = start_row; i < end_row; i++) 
    {
        for(int e = 0; e < columns; e += 1){
            Complex_number c;
        
            double unidades_largura = maxX - minX;
            double unidades_altura  = maxY - minY;
            
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

            local_buffer[buffer_index++] = pixel_value; // R
            local_buffer[buffer_index++] = pixel_value; // G
            local_buffer[buffer_index++] = pixel_value; // B
        }
    }
    t_comp += MPI_Wtime() - compute_start;

    // Referencias para buffers locais de cada rank e global_buffer (Rank 0)
    int *recvcounts = NULL;
    int *displs = NULL;
    unsigned char *global_buffer = NULL;

    // Rank 0 Reorganizando Imagem calculada via Gather
    if (rank == 0) {
        recvcounts = (int*) malloc(size * sizeof(int));
        displs = (int*) malloc(size * sizeof(int));
        global_buffer = (unsigned char*) malloc(rows * columns * 3);

        int current_displ = 0;
        for (int i = 0; i < size; i++) {
            int r_start = i * lines_per_rank;
            int r_end = (i == size - 1) ? rows : r_start + lines_per_rank;
            
            recvcounts[i] = (r_end - r_start) * columns * 3; 
            displs[i] = current_displ;
            current_displ += recvcounts[i];
        }
    }

    double gatherv_start = MPI_Wtime();
    MPI_Gatherv(local_buffer, local_buffer_size, MPI_UNSIGNED_CHAR,
                global_buffer, recvcounts, displs, MPI_UNSIGNED_CHAR,
                0, MPI_COMM_WORLD);
    t_comm += MPI_Wtime() - gatherv_start;

    printf("[Rank %d] Finalizado! Processei %d linhas.\n", rank, tasks_processed);

    free(local_buffer);

    MPI_Barrier(MPI_COMM_WORLD);
    t_total = MPI_Wtime() - t_section_start;

    if (rank == 0) {
        printf("[Rank 0] Imagem montada com sucesso! O array global_buffer tem %d bytes ordenados.\n", rows * columns * 3);

        if (argc >= 9) {
            char *filename = argv[8];
            FILE *file_image = fopen(filename, "wb");
            if (file_image) {
                fprintf(file_image, "P6\n%d %d\n255\n", columns, rows);
                fwrite(global_buffer, sizeof(unsigned char), rows * columns * 3, file_image);
                fclose(file_image);
                printf("[Rank 0] Imagem salva em: %s\n", filename);
            } else {
                perror("[Rank 0] Erro ao abrir arquivo para escrita");
            }
        } else {
            printf("[Rank 0] Aviso: Nenhum arquivo de imagem foi especificado nos argumentos.\n");
        }

        free(recvcounts);
        free(displs);
        free(global_buffer);
    }

    printf("\nRank %d\n", rank);
    printf("  Tcomp  = %.6f s\n", t_comp);
    printf("  Tcomm  = %.6f s\n", t_comm);
    printf("  Ttotal = %.6f s\n", t_total);

    double comp_sum = 0.0, comp_sum_sq = 0.0;
    double comp_max = 0.0, comp_min = 0.0;
    double comm_sum = 0.0, comm_sum_sq = 0.0;
    double comm_max = 0.0, comm_min = 0.0;
    double total_sum = 0.0, total_sum_sq = 0.0;
    double total_max = 0.0, total_min = 0.0;

    MPI_Reduce(&t_comp, &comp_sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_comp, &comp_max, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_comp, &comp_min, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&(double){ t_comp * t_comp }, &comp_sum_sq, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    MPI_Reduce(&t_comm, &comm_sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_comm, &comm_max, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_comm, &comm_min, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&(double){ t_comm * t_comm }, &comm_sum_sq, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    MPI_Reduce(&t_total, &total_sum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_total, &total_max, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&t_total, &total_min, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);
    MPI_Reduce(&(double){ t_total * t_total }, &total_sum_sq, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        double comp_mean = comp_sum / size;
        double comp_std = sqrt(fmax(0.0, (comp_sum_sq / size) - (comp_mean * comp_mean)));
        double comm_mean = comm_sum / size;
        double comm_std = sqrt(fmax(0.0, (comm_sum_sq / size) - (comm_mean * comm_mean)));
        double total_mean = total_sum / size;
        double total_std = sqrt(fmax(0.0, (total_sum_sq / size) - (total_mean * total_mean)));

        printf("\nResumo estatístico entre os %d ranks\n", size);
        printf("  Tcomp : Tmax=%.6f s | Tmin=%.6f s | Media=%.6f s | Desvio=%.6f s\n", comp_max, comp_min, comp_mean, comp_std);
        printf("  Tcomm : Tmax=%.6f s | Tmin=%.6f s | Media=%.6f s | Desvio=%.6f s\n", comm_max, comm_min, comm_mean, comm_std);
        printf("  Ttotal: Tmax=%.6f s | Tmin=%.6f s | Media=%.6f s | Desvio=%.6f s\n", total_max, total_min, total_mean, total_std);

        double tick = MPI_Wtick();
        printf("\nResolução MPI_Wtick: %.9f s\n", tick);
    }

    fflush(stdout);
    MPI_Finalize();

    return 0;
}