#include <mpi.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {
    int rank, size;
    char hostname[256];

    rc = MPI_Init(&argc, &argv);

    if (rc != MPI_SUCCESS)
    {
        printf("Error starting MPI program.\n");
        MPI_Abort(MPI_COMM_WORLD, rc);
        return -1;
    }

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    /******* do some work *******/
    
    fflush(stdout);
    MPI_Finalize();

    return 0;
}