#!/bin/bash

#SBATCH --cpus-per-task   8
#SBATCH --mem		20G
#SBATCH --time 		10:05:00
#SBATCH --profile	all
#SBATCH --acctg-freq	1


# example of submitting to cluster.

module load MATLAB/2023a

. ~/.bashrc # Only callum has to do this.

matlab -batch "runmddPlot"
