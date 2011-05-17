#!/usr/bin/env python3

"""Distributed grid searching for optimal Radial Basis Function (RBF)
kernel parameters (C, g) for SVM training.
@author Dat Hoang
@date March 2011"""

import os
import sys
import traceback
import operator as op
from itertools import product
from optparse import OptionParser
from subprocess import Popen, PIPE
from multiprocessing import Process, Lock
from multiprocessing import JoinableQueue as Queue
from multiprocessing import cpu_count


#number of local processes 
LOCAL_WORKERS = cpu_count()

#remote passwordless ssh workers
#SSH_WORKERS = ["user@host"]
SSH_WORKERS = []

#number of processes per SSH worker
N_PER_SSH = 3

#location of default utilities/data on each node
SVM_TRAIN = "~/svm-train"
TRAIN_DATA = None

#number of cross validation folds
NFOLDS = 5
#log2(C)
L2C_BEGIN, L2C_END, L2C_DELTA = -10, 10, 1
#log2(G)
L2G_BEGIN, L2G_END, L2G_DELTA = -10, 10, 1
#additional arguments
ADD_ARGS = "-h 0 -q -m 300"

#mutex on printing
PRINT_LOCK = Lock()


def frange(a, b, delta=1.0):
    """Like range(a,b) but for floats."""
    if delta <= 0 or a > b:
        return
    while a <= b:
        yield a
        a += delta

def parse_validation_score(os):
    """Parse validation score from an output stream."""
    for line in os.readlines():
        line = str(line)
        if "Cross" in line:
            return float(line.split()[-1][:-4])


class GridSearchError(Exception):
    pass

class WorkerError(GridSearchError):
    pass


class Worker(Process):
    def __init__(self, name, job_queue, result_queue):
        super(Worker, self).__init__()
        self.name = name
        self.job_queue = job_queue
        self.result_queue = result_queue
    
    def cross_validate(self, c, g):
        pass

    def run(self):
        global PRINT_LOCK
        while not self.job_queue.empty():
            try:
                (log2c, log2g) = self.job_queue.get()
                score = self.cross_validate(2.0**log2c, 2.0**log2g)
                if score is None:
                    raise WorkerError()
            except WorkerError:
                #computation failed, abandon and let others do it
                self.job_queue.put((log2c, log2g))
                self.job_queue.task_done()
            except BaseException:
                #quit if failed for any other reason
                with PRINT_LOCK:
                    traceback.print_exception(
                        sys.exc_info()[0],
                        sys.exc_info()[1],
                        sys.exc_info()[2])
                    print("Worker %s quit!" % self.name, file=sys.stderr)
                self.job_queue.task_done()
                break
            else:
                #successful computation
                self.result_queue.put((self.name, log2c, log2g, score))
                self.job_queue.task_done()


class LocalWorker(Worker):
    """Worker node on the local CPU."""
    def cross_validate(self, c, g):
        """Calculate cross-validation score for given c,g parameters."""
        global PRINT_LOCK
        command = '%s -c %f -g %f -v %d %s %s' % \
            (SVM_TRAIN, c, g, NFOLDS, ADD_ARGS, TRAIN_DATA)
        
        with PRINT_LOCK:
            print("%s doing: %s" % (self.name, command), file=sys.stderr)
        
        result = Popen(command, shell=True, stdout=PIPE).stdout
        return parse_validation_score(result)
    

class SSHWorker(Worker):
    """Worker node over SSH."""
    def __init__(self, name, host, job_queue, result_queue):
        super(SSHWorker, self).__init__(name, job_queue, result_queue)
        self.host = host
        
    def cross_validate(self, c, g):
        """Calculate cross-validation score for given c,g parameters."""
        global PRINT_LOCK
        command = 'ssh -x %s "%s -c %f -g %f -v %d %s %s"' % \
            (self.host, SVM_TRAIN, c, g, NFOLDS, ADD_ARGS, TRAIN_DATA)
        
        with PRINT_LOCK:
            print("%s doing: %s" % (self.name, command), file=sys.stderr)

        result = Popen(command, shell=True, stdout=PIPE).stdout
        return parse_validation_score(result)        


def main():
    global L2C_BEGIN, L2C_END, L2C_DELTA, L2G_BEGIN, L2G_END, L2G_DELTA
    global NFOLDS, ADD_ARGS, SVM_TRAIN, TRAIN_DATA, N_PER_SSH
    
    parser = OptionParser(
        usage="usage: %prog [options] <dataset> <gridscore-file>")
    parser.add_option("--log2c", dest="log2c", metavar="BEGIN END STEP",
        type='float', nargs=3, default=(L2C_BEGIN, L2C_END, L2C_DELTA),
        help="log2 of C SVM contraint [default: %default]")
    parser.add_option("--log2g", dest="log2g", metavar="BEGIN END STEP",
        type='float', nargs=3, default=(L2G_BEGIN, L2G_END, L2G_DELTA),
        help="log2 of G SVM contraint [default: %default]")
    parser.add_option("-v", "--fold", dest="fold", metavar="FOLD",
        type='int', default=NFOLDS,
        help="number of cross validation folds [default: %default]")
    parser.add_option("-a", "--args", dest="args", metavar="ARGS",
        type='string', default=ADD_ARGS,
        help="additional arguments to the SVM trainer [default: %default]")
    parser.add_option("--svm-train", dest="svm_train", metavar="PATHNAME",
        type='string', default=SVM_TRAIN,
        help="path of SVM trainer [default: %default]")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage(file=sys.stderr)
        return 1

    L2C_BEGIN, L2C_END, L2C_DELTA = options.log2c
    L2G_BEGIN, L2G_END, L2G_DELTA = options.log2g
    NFOLDS = options.fold
    ADD_ARGS = options.args
    SVM_TRAIN = options.svm_train
    TRAIN_DATA, outfile = args
    
    job_queue = Queue()
    result_queue = Queue()

    for log2c, log2g in product(
            frange(L2C_BEGIN, L2C_END, L2C_DELTA),
            frange(L2G_BEGIN, L2G_END, L2G_DELTA)):
        job_queue.put((log2c, log2g))

    for i in range(LOCAL_WORKERS):
        LocalWorker('local-%d' % i, job_queue, result_queue).start()
    
    for i, host in enumerate(SSH_WORKERS):
        for j in range(N_PER_SSH):
            SSHWorker('ssh-%d/%d' % (i, j), 
                host, job_queue, result_queue).start()

    #block until all jobs are done
    job_queue.join()
    
    result = []
    while not result_queue.empty():
        result.append(result_queue.get())
    result = sorted(result, key=op.itemgetter(3,1,2), reverse=True)

    _, best_log2c, best_log2g, best_score = max(result, key=op.itemgetter(3,1,2))

    with open(outfile, 'w') as ofp:
        ofp.write("#best result: log2c=%f, log2g=%f, score=%f\n" % \
            (best_log2c, best_log2g, best_score))
        ofp.write("#log2(c)\tlog2(g)\tscore\n")
        for (name, log2c, log2g, score) in result:
            ofp.write("%f\t%f\t%f\n" % (log2c, log2g, score))

    return 0

if __name__=="__main__":
    sys.exit(main())
