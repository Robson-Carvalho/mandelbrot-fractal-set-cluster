#include <mpi.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
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


    if (argc < 3) {
        printf("Error: You must provide rows and columns.\n");
        return -1;
    }

    int rows = atoi(argv[1]);
    int columns = atoi(argv[2]);

    int tasks = 0;

    for (int i = rank; i < rows; i += size) {
        for(int e = 0; e < columns; e += 1){
            printf("Rank: %d, Task: %d\n", rank, tasks);
        }

        tasks++;
    }

    fflush(stdout);
    MPI_Finalize();

    return 0;
}