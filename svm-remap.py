#!/usr/bin/env python3

"""Remap SVM target of every line from one numeric target to another
based on the name file of every target."""

import sys
import csv
from optparse import OptionParser


FIELD_DELIMITER='\t'
SVM_DELIMITER=' '


def gen_remap_table(from_fp, to_fp):
    """Generate a hash table to remap category names between SVM files."""
    freader = csv.reader(from_fp, delimiter=FIELD_DELIMITER)
    treader = csv.reader(to_fp, delimiter=FIELD_DELIMITER)
    
    ftable = dict((i, field) for i, field in freader)
    ttable = dict((field, i) for i, field in treader)

    return dict((i, ttable[field]) for i, field in ftable.items())

def svm_remap(remap_table, in_fp, out_fp):
    """Remap all category integers according to remap table."""
    def remap(category):
        return remap_table[category]

    reader = csv.reader(in_fp, delimiter=SVM_DELIMITER)
    for line in reader:
        category, *rest = line
        out_fp.write("%s%s%s\n" % (
            remap(category), SVM_DELIMITER, SVM_DELIMITER.join(rest)))

def main():
    parser = OptionParser(
        usage="""Usage: %prog <from-fields> <to-fields> <in-svm> <out-svm>
            <from-fields> := file of fields to map from
            <to-fields> := file of fields to map to
            <in-svm> := input SVM file to remap ( - := /dev/stdin)
            <out-svm> := output SVM file ( - := /dev/stdout)""")
    (_, args) = parser.parse_args()
    if len(args) != 4:
        parser.print_usage(file=sys.stderr)
        return 1
    
    from_fields = args[0]
    to_fields = args[1]
    svm_in = "/dev/stdin" if args[2]=='-' else args[2]
    svm_out = "/dev/stdout" if args[3]=='-' else args[3]

    with open(from_fields, 'r') as from_fp, open(to_fields, 'r') as to_fp:
        remap_table = gen_remap_table(from_fp, to_fp)

    with open(svm_in, 'r') as in_fp, open(svm_out, 'w') as out_fp:
        svm_remap(remap_table, in_fp, out_fp)

    return 0

if __name__=="__main__":
    sys.exit(main())
