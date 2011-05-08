#!/usr/bin/env python3

"""Generate an accuracy report with confusion matrix for
a given SVM model on a test data set."""

import csv
import sys
from collections import defaultdict
from subprocess import Popen, PIPE
from optparse import OptionParser
from itertools import chain


SVM_PREDICT = "~/shared/svm-predict"
DELIMITER = '\t'


def parse_name_table(name_fd):
    """Parse a hash table for name fields."""
    reader = csv.reader(name_fd, delimiter=DELIMITER)
    return dict((int(i),name) for i, name in reader)

def gen_report(name_table, pairs, out_fp):
    """Generate report based on (actual, estimated) pairs."""
    matrix = defaultdict(int)
    actual_table = defaultdict(int)
    estimated_table = defaultdict(int)

    for (actual, estimated) in pairs:
        matrix[(actual,estimated)] += 1
        actual_table[actual] += 1
        estimated_table[estimated] += 1
    
    categories = set(chain(actual_table.keys(), estimated_table.keys()))
    all_correct = sum(matrix[(c,c)] for c in categories)
    all_total = sum(actual_table.values())

    #overall accuracy
    all_total = float(all_total) if all_total > 0 else 1.0
    out_fp.write("\nOverall accuracy: %f\n" % (all_correct / all_total))

    #confusion matrix
    out_fp.write("\nX=SystemAnswer, Y=CorrectAnswer\n\n")
    for c in categories:
        out_fp.write("%-5s\t" % name_table.get(c, c))
        out_fp.write("\t".join("%-4s" % matrix[(c, p)] for p in categories))
        out_fp.write("\n")

    #category results
    out_fp.write("\nLabel\tCorrect\tTotal\tPrec\tRecall\tFmeas\n")
    for c in categories:
        correct = matrix[(c,c)]
        total = actual_table[c]
        precision = correct / float(estimated_table[c]) \
            if estimated_table[c] != 0 else 0.0
        recall = correct / float(total) \
            if total != 0 else 0.0
        fmeas = 2 * precision * recall / (precision + recall) \
            if (precision + recall) != 0.0 else 0.0

        out_fp.write("%-5s" % name_table.get(c, c))
        out_fp.write("%6d\t%6d\t%6.3f\t%6.3f\t%6.3f\n" % \
            (correct, total, precision, recall, fmeas))

def main():
    global SVM_PREDICT
    
    parser = OptionParser(
        usage="""Usage: %prog [options] <model> <svm-file>
            <model> := trained SVM model file
            <svm-file> := SVM file to test""")
    parser.add_option("--svm-predict", dest="svm_predict", metavar="PATHNAME",
        type='string', default=SVM_PREDICT,
        help="path of SVM predictor [default: %default]")
    parser.add_option("-f", "--fields", dest="fields",
        metavar="PATHNAME", type='string', default=None,
        help="file of field mappings from integer to names")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage(file=sys.stderr)
        return 1
    
    SVM_PREDICT = options.svm_predict
    fields_file = options.fields
    model_file = args[0]
    svm_file = args[1]

    if fields_file:
        with open(fields_file, 'r') as field_fp:
            table = parse_name_table(field_fp)
    else:
        table = {}
    
    with open(svm_file, 'r') as ifp:
        actual = [int(line.split()[0]) for line in ifp]

    estimated = map(int, 
        Popen("%s %s %s /dev/stdout | head -n -1" % 
            (SVM_PREDICT, svm_file, model_file), 
            shell=True, stdout=PIPE).stdout.readlines())

    gen_report(table, zip(actual, estimated), sys.stdout)

    return 0

if __name__=="__main__":
    sys.exit(main())
