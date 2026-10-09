#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
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

    // tamanho da linha
    size_t line_bytes = (size_t)columns * 3;

    // tamanho parcial da imagem - apenas o tamanho calculado das linhas por esse processo
    unsigned char *my_lines = (unsigned char *)malloc(my_rows * line_bytes * sizeof(unsigned char));

    int local_idx = 0;
    for (int i = rank; i < rows; i += size) {
        int offset = local_idx * line_bytes;
        unsigned char *row_ptr = &my_lines[offset];

        for (int e = 0; e < columns; e++) {
            Complex_number c;
            c.real = minX + ((double)e / columns) * (maxX - minX);
            c.imag = maxY - ((double)i / rows) * (maxY - minY);

            Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

            unsigned char color_intensity;
            if (result.check == 1) {
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

    unsigned char *full_image = NULL;
    unsigned char *gathered_buffer = NULL;
    int *chunk_sizes_in_bytes = NULL;
    int *byte_offsets_in_buffer = NULL;

    if (rank == 0) {
        size_t total_image_bytes = (size_t)rows * line_bytes;
        full_image = (unsigned char *)malloc(total_image_bytes);
        gathered_buffer = (unsigned char *)malloc(total_image_bytes);
        
        // Arrays para o MPI_Gatherv saber o tamanho do bloco de cada processo
        chunk_sizes_in_bytes = (int *)malloc(size * sizeof(int));
        byte_offsets_in_buffer = (int *)malloc(size * sizeof(int));

        int accumulated_bytes = 0;
        for (int process_id = 0; process_id < size; process_id++) {
            // Conta quantas linhas o 'process_id' processou
            int lines_this_process = 0;
            for (int line = process_id; line < rows; line += size) {
                lines_this_process++;
            }
            
            int bytes_this_process = lines_this_process * (int)line_bytes;
            // A quantidade de bytes de cada processo armazenado no index de sua referência 
            chunk_sizes_in_bytes[process_id] = bytes_this_process; 
            // Em cada posição desse array, há um offset para que o MPI_Gatherv saiba onde colocar os dados de cada processo
            byte_offsets_in_buffer[process_id] = accumulated_bytes;
            
            accumulated_bytes += bytes_this_process;
        }
    }

    
    MPI_Gatherv(
        my_lines, 
        my_rows * (int)line_bytes, 
        MPI_UNSIGNED_CHAR,gathered_buffer,
        chunk_sizes_in_bytes, 
        byte_offsets_in_buffer, 
        MPI_UNSIGNED_CHAR, 
        0,
        MPI_COMM_WORLD 
    );


    if (rank == 0) {
        for (int real_line = 0; real_line < rows; real_line++) {
            int owner = real_line % size;
            int line_in_block = real_line / size;
            
            size_t source_index  = byte_offsets_in_buffer[owner] + line_in_block * line_bytes;
            size_t destination_index = real_line * line_bytes;

            unsigned char *source      = &gathered_buffer[source_index];
            unsigned char *destination = &full_image[destination_index];

            memcpy(destination, source, line_bytes);
        }
    }

    // Gerar a imagem.
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
        free(chunk_sizes_in_bytes);
        free(byte_offsets_in_buffer);
    }

    free(my_lines);
    MPI_Finalize();
    return 0;
}