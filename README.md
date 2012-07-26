Code to reproduce the results of the paper

A.J. Weinstein and M.B. Wakin. [Online Search Orthogonal Matching Pursuit][1]. In
IEEE Statistical Signal Processing Workshop.

[1]: http://www.ocam.cl/static/pdfs/os_omp_spp12.pdf

Dependencies
============

* Python >=2.6
* NumPy >= 1.3
* SciPy >= 0.7
* Matplotlib >= 1.2

Optional (to reproduce the A*OMP results)

* Matlab
* [mlabwrap v1.1-pre][2]
* [A*OMP][3]

[2]: https://github.com/aweinstein/mlabwrap
[3]: http://students.sabanciuniv.edu/~karahanoglu/AStar/AStarOMPv_01.00.zip

Note
====

If you want to run A*star, make sure to add the `matlab` directory to Matlab
(e.g., by adding a 'addpath path/to/osomp/matlab` line in `startup.m`.

Usage
=====

Create residue comparison plot (Fig. 2 of the paper)

    $ python osomp.py --residue

Create rate of recovery plot (Fig. 3(a-c))

    $ python osomp.py --rate

To also run A*OMP:

    $ python osomp.py --rate --astar

Create relative error for noisy observations (Fig. 3(d))

    $ python osomp.py --noisy