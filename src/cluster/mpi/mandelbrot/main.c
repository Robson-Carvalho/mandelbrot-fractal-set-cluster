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
        printf("Uso: make all-mandelbrot PARS=\"<rows> <cols> <minX> <maxX> <minY> <maxY> <max_iter>\"\n");
        printf("Exemplo: make all-mandelbrot PARS=\"2000 2000 -2.0 1.0 -1.5 1.5 1000\"\n");
        return -1;
    }

    int rows = atoi(argv[1]);
    int columns = atoi(argv[2]);
    double minX = atof(argv[3]);
    double maxX = atof(argv[4]);
    double minY = atof(argv[5]);
    double maxY = atof(argv[6]);
    int max_iter = atoi(argv[7]);

    long long total_iter = 0; 

    for (int i = rank; i < rows; i += size) 
    {
        for(int e = 0; e < columns; e += 1){
            Complex_number c;
            c.real = minX + (e * (maxX - minX)) / columns;
            c.imag = minY + (i * (maxY - minY)) / rows;

            Mandelbrot_check_return result = check_mandelbrot(c, max_iter);

            unsigned char r, g, b;

            if (result.check == 1) { 
                r = g = b = 0;
                total_iter += max_iter;
            } else {
                int iter = result.iterations_to_scape;
                unsigned char tom = (unsigned char)(sin(0.1 * iter) * 127.5 + 127.5);
                r = g = b = tom;
                total_iter += iter;
            }
        }
    }


    if(size > 1){
        if(rank == 0)
        {
            int receive = 0;
            printf("oi, eu sou o mestre de rank %d e vou receber valores dos trabalhos!\n", rank);
            

            for(int i = 1; i < size; i++){
                // int MPI_Recv(void *message, int count, MPI_Datatype datatype, int source, int tag, MPI_Comm comm, MPI_Status *status)
                MPI_Recv(&receive, 1, MPI_INT, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD, NULL);
                printf("Recebi: %d\n", receive);
            }
        }
        else
        {
            int tag = 0;
            int dest = 0;

            printf("oi, eu sou o trabalhador de rank %d e vou enviar %d para o mestre!\n", rank, total_iter);
            //int MPI_Send(void *message, int count, MPI_Datatype datatype, int dest, int tag, MPI_Comm comm)
            MPI_Send(&total_iter, 1, MPI_INT, dest, tag, MPI_COMM_WORLD);
        }
    }

    fflush(stdout);
    MPI_Finalize();

    return 0;
}