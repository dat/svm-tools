#!/usr/bin/env python3

"""Convert ARFF feature vector file to SVM feature vector file."""

import sys
import csv
from optparse import OptionParser


ARFF_DELIMITER = ','
SVM_DELIMITER = ' '


def transform(arff_fp, svm_fp):
    """Transform every training instance of ARFF file to SVM instances
       and return all the field mappings collected."""
    reader = csv.reader(arff_fp, delimiter=ARFF_DELIMITER)
    category_table = {}
    counter = 0
    
    for line in reader:
        if line[0][0]=='@':
            continue #ignore header lines
        
        *rest, category = line
        if category not in category_table:
            numeric_category = category_table[category] = counter = counter + 1
        else:
            numeric_category = category_table[category]
        values = SVM_DELIMITER.join("%s:%s"%(i, s)
            for i, s in enumerate(rest, start=1) if float(s)!=0.0)
        svm_fp.write("%s %s\n" % (numeric_category, values))

    return category_table

def main():
    parser = OptionParser(
        usage="""Usage: %prog <fields> <arff-file> <svm-file>
            <fields> := field-mappings destination file (- := /dev/stderr)
            <arff-file> := arff source file (- := /dev/stdin)
            <svm-file> := svm destination file (- := /dev/stdout)""")
    (_, args) = parser.parse_args()
    if len(args) != 3:
        parser.print_usage(file=sys.stderr)
        return 1
    
    fields_file = "/dev/stderr" if args[0]=='-' else args[0]
    arff_file = "/dev/stdin" if args[1]=='-' else args[1]
    svm_file = "/dev/stdout" if args[2]=='-' else args[2]

    with open(arff_file, 'r') as arff_fp, open(svm_file, 'w') as svm_fp:
        fields_table = transform(arff_fp, svm_fp)

    with open(fields_file, 'w') as fields_fp:
        for k, v in fields_table.items():
            fields_fp.write("%s\t%s\n" % (v, k))

    return 0

if __name__=="__main__":
    sys.exit(main())

