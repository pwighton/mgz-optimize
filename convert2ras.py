#!/usr/bin/env python3

import sys
import argparse
import nibabel as nb

def parse_args():
    script_desc = 'Converts imaging files to RAS.'
    parser = argparse.ArgumentParser(description=script_desc)

    parser.add_argument('infile', help='Input file')
    parser.add_argument('outfile', help='Output file')

    return parser.parse_args()

def convert_orientation(infile, outfile, target_orientation = 'RAS'):
    input_img = nb.load(infile)
    header = input_img.header.copy()

    orig_affine = input_img.affine.copy()
    orig_orientation = nb.aff2axcodes(orig_affine)
    print(f"Original orientation: {orig_orientation}")
    
    transformation = nb.orientations.ornt_transform(
      nb.orientations.axcodes2ornt(orig_orientation),
      nb.orientations.axcodes2ornt(target_orientation),
    )

    reoriented_img = input_img.as_reoriented(transformation)
    nb.save(reoriented_img, outfile)
    return 0
    
def main():
    args = parse_args()
    return convert_orientation(args.infile, args.outfile)
    
if __name__ == "__main__":
    sys.exit(main())
