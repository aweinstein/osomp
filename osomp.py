import sys

import numpy as np
from numpy.linalg import norm, pinv, lstsq
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib as mpl

try:
    from mlabwrap import mlab
except ImportError:
    Use_Matlab = False
else:
    Use_Matlab = True


params = {'backend': 'Agg',
          'axes.labelsize': 40,
          'text.fontsize': 24,
          'legend.fontsize': 20,
          'xtick.labelsize': 30,
          'ytick.labelsize': 30,
          'savefig.dpi' : 600,
          'ps.usedistiller' : 'xpdf',
          'text.usetex' : True,
          'font.family': 'serif',
          'font.serif' : ['Times'],
          }
mpl.rcParams.update(params)

def save_fig(fig, file_name):
    if isinstance(fig, list):
        pdf = PdfPages(file_name)
        for f in fig:
            pdf.savefig(f)
        pdf.close()
    else:
        fig.savefig(file_name, format='pdf', dpi=300)
    print 'File %s created' % file_name


class DictSet(dict):
    def __init__(self, *args):
        dict.__init__(self, args)

    def to_hashable(self, key):
        return tuple(sorted(key))

    def __getitem__(self, key):
        val = dict.__getitem__(self, self.to_hashable(key))
        return val

    def __setitem__(self, key, val):
        return dict.__setitem__(self, self.to_hashable(key), val)

    def __contains__(self, key):
        return dict.__contains__(self, self.to_hashable(key))


def random_dict(m, n):
    """Create an m-by-n random dictionary.

    The entries are i.i.d. gaussian.

    Parameters
    ----------
    m : number of rows
    n : number of columns

    Return
    ------
    D : The dictionary
    """
    D = np.random.randn(m, n)
    D /= np.sqrt(np.sum((D ** 2), axis=0))

    return D

def get_sparse_x(n, s, dist='normal'):
    """Create an s-sparse vector of length n.

    The support is selected uniformly at random. The amplitudes on the support
    are i.i.d. with uniform random sign and magnitud uniform on the range
    [1,2].

    Parameters
    ----------
    n : length of the vector
    s : number of non-zero entries

    """
    i = np.arange(0,n)
    np.random.shuffle(i)
    support = i[:s]

    x = np.zeros((n, 1))
    if dist == 'normal':
        x[support, 0] = np.random.randn(s)
    elif dist == 'uniform':
        x[support, 0] = np.sign(np.random.randn(s)) * np.random.uniform(1,2,s)
    elif dist == 'binary':
        x[support, 0] = np.sign(np.random.randn(s))

    return x


def single_experiment(n, m, s, method='omp', dist='normal'):
    """Run a single experiment.

    The experiment consist on recovering an s-sparse signal of length n from m
    measurements using OMP. The original signal is generated by get_sparse_x

    Parameters
    ----------
    n : length of the signal
    m : number of measurements
    s : sparsity of the signal
    use_naive : if true, use naive implementation of OMP, use scikit.learn
       implementation otherwise. Default to False

    Return
    ------
    error: The ell_2 norm of the difference between the original and the
       recovered signal
    """
    D = random_dict(m, n)
    x = get_sparse_x(n, s, dist=dist)
    y = np.dot(D, x)
    if method == 'omp':
        x_hat = omp(D, y)
    elif method == 'lrt-omp':
        if dist == 'normal':
            delta = 0.015
        elif dist == 'uniform':
            delta = 0.1
        elif dist == 'binary':
            delta = 0.1
        x_hat = lrt_omp(D, y, s, delta=delta)
    else:
        x_hat = mlab.astar(D, y, s, 100)
    x_hat.resize(n, 1)
    error = norm(x - x_hat)
    return error

def prob_of_recovery(n, m, s, n_trials=100, method='omp', dist='normal'):
    """Probability of recovery of a given method.

    Parameters
    ----------
    n : ambient dimension
    m : number of measuremenst
    s : sparsity level
    n_trials : number of trials. Default to 100

    Returns
    -------
    p_recovery : estimate of the probability of recovery
    """
    # Set seed to assure that all methods experience the same signals
    np.random.seed(1)

    n_success = 0
    for i in range(n_trials):
        if single_experiment(n, m, s, method, dist=dist) < 1e-4:
            n_success += 1

    p_recovery =  float(n_success) / n_trials

    print('n: %d, m: %d, s: %d -> p_%s = %.2f'
          % (n, m, s, method, p_recovery))

    return p_recovery

def omp(D, y, epsilon=1e-6, save_data=False):
    """ Recover x using naive implementation of OMP.

    Parameter
    ---------
    D: Dictionary
    y: Measurement

    Return
    ------
    x_hat : Estimate of x
    """

    if save_data:
        residues = [1]
        scores = []

    n = D.shape[1]
    r = y.copy()
    k = 0
    Delta = []
    while norm(r) > epsilon:
        h = np.abs(np.dot(D.T, r))
        Delta.append(np.argmax(h))
        alpha, _, _, _ = lstsq(D[:,Delta], y)
        r = y - np.dot(D[:, Delta], alpha)
        k += 1
        if save_data:
            residues.append(norm(r) / norm(y))
            scores.append(h)

    x_hat = np.zeros(n)
    x_hat[Delta] = alpha

    if save_data:
        return x_hat, residues, scores, Delta
    else:
        return x_hat

residues = DictSet() # Cache with the computed residues
def residue(A, y, Gamma):
    if Gamma in residues:
        return residues[Gamma]
    else:
        A_Gamma = A[:, list(Gamma)]
        alpha, _, _, _ = lstsq(A_Gamma, y)
        residue =  y - np.dot(A_Gamma, alpha)
        residues[Gamma] = residue
        return residue

predecessors = DictSet()
# Do we cache the succesosrs?
def succesors(A, y, Gamma, P=2):
    m = len(y)
    succs = []     # May be return a generator to save memory?
    if len(Gamma) < m:
        r = residue(A, y, Gamma)
        scores = np.abs(np.dot(A.T, r))
        idxs = np.argsort(scores, axis=0)[:-P-1:-1].flatten()
        succs.extend([set((idx,)).union(Gamma) for idx in idxs])
    if Gamma in predecessors:
        succs.append(predecessors[Gamma])

    return succs

def ell1_norm(A, y, Gamma):
    A_Gamma = A[:, list(Gamma)]
    alpha, _, _, _ = lstsq(A_Gamma, y)
    return norm(alpha, 1)

def h(A, y, Gamma):
    return norm(residue(A, y, Gamma))

def lrt_omp(A, y, k, epsilon=1e-6, **options):
    delta = options.pop('delta', 0.1)
    verbose = options.pop('verbose', False)
    save_data = options.pop('save_data', False)
    max_iters = options.pop('max_iters', 200)

    u = DictSet()
    visited = []
    residues.clear()
    predecessors.clear()
    residues[()] = y
    Gamma = set()
    last_Gamma = set()
    n_iters = 0
    Gammas = []
    delta_res = []
    last_res = norm(y)
    residue_list = [1.0]
    first_time = True
    while True:
        if norm(residue(A, y, Gamma)) < epsilon and len(Gamma)<2*k:
            break
        if Gamma not in u:
            u[Gamma] = h(A, y, Gamma)
        m = float('inf')
        for Gamma_succ in succesors(A, y, Gamma):
            if Gamma_succ not in u:
                u[Gamma_succ] = h(A, y, Gamma_succ)
            if u[Gamma_succ] < m:
                m = u[Gamma_succ]
                Gamma_min = Gamma_succ

        succs = succesors(A, y, Gamma)
        res = [u[g] for g in succs]
        Gamma_min = succs[res.index(min(res))]

        delta_res.append((max(res) - min(res)) / norm(y))
        if verbose: print '%.2e' % ((max(res) - min(res)) / norm(y)),
        if (max(res) - min(res)) / norm(y) > delta:
            Gamma_min = succs[res.index(min(res))]
        else:
            cards = [len(g) for g in succs]
            Gamma_min = succs[cards.index(min(cards))]

        if Gamma_min not in predecessors:
            predecessors[Gamma_min] = Gamma
        Gamma = Gamma_min

        residue_list.append(h(A,y,Gamma) / norm(y))
        dr = abs(last_res - h(A,y,Gamma))

        d0 = residue_list[0] - residue_list[1]
        d =  residue_list[-2] - residue_list[-1]

        n_iters += 1

        if verbose: print n_iters-1,

        if len(Gamma) > len(last_Gamma):
            if verbose: print ' Added', Gamma.difference(last_Gamma),
        else:
            if verbose: print ' Removed', last_Gamma.difference(Gamma),
            u[last_Gamma] = 100
        if verbose: print 'with card', len(Gamma),
        if verbose: print u[last_Gamma]
        Gammas.append(Gamma)

        last_Gamma = Gamma.copy()

        if n_iters > max_iters:
            if verbose: print 'Too many iterations :('
            break

    alpha, _, _, _ = lstsq(A[:,list(Gamma)], y)
    x_hat = np.zeros(A.shape[1])
    x_hat[list(Gamma)] = alpha

    do_plot = False
    if do_plot:
        plt.plot(residue_list, 'o:')
        plt.grid()
        plt.show()
    if save_data:
        return x_hat, Gammas, residue_list
    else:
        return x_hat

def experiment_2(plot=False, **options):
    """Recover one signal using OMP."""
    n = options.pop('n', 128)
    k = options.pop('k', 5)
    m = options.pop('m', 20)
    dist = options.pop('dist', 'uniform')
    seed = options.pop('seed', None)
    return_locals = options.pop('return_locals', True)

    print ('Recovering signal wiht n=%(n)i, k=%(k)i and m=%(m)i using OMP' %
           locals())

    if seed:
        np.random.seed(seed)
    x = get_sparse_x(n, k, dist=dist)
    if seed:
        np.random.seed(seed + 198)
    A = random_dict(m, n)
    y = np.dot(A, x)

    x_hat, residues, scores, Delta = omp(A, y, save_data=True)

    if plot:
        plt.figure()
        plt.stem(range(n), x, 'r-', 'ro', 'k:')
        plt.stem(range(n), x_hat, 'b:', 'bx', 'k:')
        plt.show()

    print 'error', norm(x - x_hat.reshape(n, 1))

    if return_locals:
        return locals()

def experiment_3(**options):
    """Recover one signal using LRT-OMP."""
    n = options.pop('n', 128)
    k = options.pop('k', 5)
    m = options.pop('m', 20)
    dist = options.pop('dist', 'uniform')
    seed = options.pop('seed', None)
    return_locals = options.pop('return_locals', True)
    verbose = options.pop('verbose', True)

    print ('Recovering signal wiht n=%(n)i, k=%(k)i and m=%(m)i using '
           'LRT-OMP' % locals())

    if seed:
        np.random.seed(seed)
    x = get_sparse_x(n, k, dist=dist)
    if seed:
        np.random.seed(seed + 198)
    A = random_dict(m, n)
    y = np.dot(A, x)
    x_hat, Gammas, residues = lrt_omp(A, y, k, verbose=verbose, save_data=True,
                                     **options)
    print 'error', norm(x - x_hat.reshape(n, 1))

    if return_locals:
        return locals()

def experiment_7(mode='thesis'):
    """Compare OMP and LRT-OMP.

    The format of the plots depends on mode. Available options are 'thesis',
    'paper', 'poster'.

    """
    n = 128
    m = 19
    k = 5
    seed = 3
    delta = 0.18
    d_omp = experiment_2(n=n, m=m, k=k, seed=seed)
    d_lrt = experiment_3(n=n, m=m, k=k, seed=seed, delta=delta)

    if mode in ['thesis', 'poster']:
        params = {'axes.labelsize': 30,
                  'axes.titlesize': 30,
                  'text.fontsize': 24,
                  'legend.fontsize': 20,
                  'xtick.labelsize': 20,
                  'ytick.labelsize': 20}
    elif mode == 'paper':
        params = {'axes.labelsize': 40,
                  'text.fontsize': 24,
                  'legend.fontsize': 20,
                  'xtick.labelsize': 30,
                  'ytick.labelsize': 30}
    else:
        print 'Unknon mode', mode
        return
    mpl.rcParams.update(params)

    figs = []
    figs.append(plt.figure())
    ms = 9
    res_lrt = d_lrt['residues']
    res_omp = d_omp['residues']
    plt.plot(range(len(res_lrt)), res_lrt, 'o-b', label='OS-OMP',
             markersize=ms)
    plt.plot(range(len(res_omp)), res_omp, 's-g', label='OMP',
             markersize=ms)
    plt.legend()
    plt.xlim(-0.4, len(res_lrt) + 0.4)
    plt.ylim(-0.0, 1.1)
    plt.xlabel('iteration')
    plt.ylabel('residue norm')
    plt.grid(color=(0.7, 0.7, 0.7))
    plt.tight_layout()
    save_fig(figs, 'residue_comparison.pdf')
    return locals()

if __name__ == '__main__':
    experiment_7()
