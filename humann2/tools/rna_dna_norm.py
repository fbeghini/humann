#! /usr/bin/env python

"""
HUMAnN2 utility for normalizing combined meta'omic seq data
Run ./rna_dna_norm.py -h for usage help
"""

from __future__ import print_function # PYTHON 2.7+ REQUIRED
import argparse
import sys
import util

# constants
c_new_dna_extension = "-smoothed_dna.tsv"
c_new_rna_extension = "-smoothed_rna.tsv"
c_norm_rna_extension = "-normalized_rna.tsv"

def get_args ():
    """ Get args from Argparse """
    parser = argparse.ArgumentParser()
    parser.add_argument( 
        "-d", "--input_dna", 
        help="Original DNA output table (.tsv format)",
        )
    parser.add_argument( 
        "-r", "--input_rna", 
        help="Original RNA output table (.tsv format)",
        )
    parser.add_argument( 
        "-o", "--output_basename", 
        help="Path/basename for the three output tables",
        )
    args = parser.parse_args()
    return args

def remove_totals( table ):
    rowheads2, data2 = [], []
    for i, rowhead in enumerate( table.rowheads ):
        if util.c_strat_delim in rowhead:
            rowheads2.append( rowhead )
            data2.append( table.data[i] )
    table.rowheads, table.data = rowheads2, data2

def wbsmooth( table, all_features ):
    # compute per-sample epsilon
    nonzero = [0 for i in table.data[0]]
    colsums = [0 for i in table.data[0]]
    for i, row in enumerate( table.data ):
        # float table here
        table.data[i] = map( float, row )
        for j, value in enumerate( table.data[i] ):
            nonzero[j] += 1 if value > 0 else 0
            colsums[j] += value
    # compute epsilons/norms
    epsilons, norms = [], []
    for j in range( len( nonzero ) ):
        # total events for column j
        N = colsums[j]
        # total first events
        T = nonzero[j]
        # implied unobserved events
        Z = len( all_features ) - T
        norms.append( N / float( N + T ) )
        epsilons.append( ( norms[-1] * T / float( Z ) ) if Z > 0 else 0 )
    # compute quick index for table
    rowmap = {rowhead:i for i, rowhead in enumerate( table.rowheads )}
    # rebuild table data
    rowheads2, data2 = [], []
    for feature in all_features:
        rowheads2.append( feature )
        # feature is in the table; still adjust zero values
        if feature in rowmap:
            i = rowmap[feature]
            for j, value in enumerate( table.data[i] ):
                if value == 0:
                    table.data[i][j] = epsilons[j]
                else:
                    table.data[i][j] = value * norms[j]
            data2.append( table.data[i] )
        # feature is absent from the table; use epsilon for everyone
        else:
            data2.append( epsilons )
    table.rowheads, table.data = rowheads2, data2      

def hsum( table ):
    # look ahead
    groups = {}
    for i, rowhead in enumerate( table.rowheads ):
        groups.setdefault( rowhead.split( util.c_strat_delim )[0], [] ).append( i )
    # rebuild
    rowheads2, data2 = [], []
    for group, poslist in groups.items():
        # attach the sum to the new table
        rowheads2.append( group )
        total = [0 for i in range( len( table.data[0] ) )]
        for i in poslist:
            total = [k1 + k2 for k1, k2 in zip( total, table.data[i] )]
        data2.append( total )
        # attach individual old rows to the new table
        for i in poslist:
            rowheads2.append( table.rowheads[i] )
            data2.append( table.data[i] )
    table.rowheads, table.data = rowheads2, data2

def main ( ):
    # warning
    print( "\nThis script assumes:\n",
           "(1) That DNA and RNA columns have the same order.\n",
           "(2) That units are count-like (including default RPKs).\n",
           file=sys.stderr )
    args = get_args()
    dna = util.Table( args.input_dna )
    rna = util.Table( args.input_rna )
    assert dna.is_stratified == rna.is_stratified, \
        "FAILED: Tables have nonequal stratification status."
    strat_mode = dna.is_stratified
    all_features = sorted( set( dna.rowheads ).__or__( set( rna.rowheads ) ) )
    for t in dna, rna:
        if strat_mode:
            remove_totals( t )
            all_features = [k for k in all_features if util.c_strat_delim in k]
        wbsmooth( t, all_features )
        if strat_mode:
            hsum( t )
    # write out dna/rna
    dna.write( args.output_basename+c_new_dna_extension )
    rna.write( args.output_basename+c_new_rna_extension )
    # normalize rna, then write
    for i in range( len( dna.data ) ):
        rna.data[i] = [r / d for r, d in zip( rna.data[i], dna.data[i] )]
    rna.write( args.output_basename+c_norm_rna_extension )

if __name__ == "__main__":
    main()
