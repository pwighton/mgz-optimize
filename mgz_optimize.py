#!/usr/bin/env python3

import sys
import os
import argparse
import logging
import pathlib
import traceback

import numpy as np
import surfa as sf

from can_convert_mgz_to_int import can_convert_to_int

script_desc = 'Optimizes integer-based mgz files, by:' + \
              ' 1) saving the file as the smallest possible dtype; and' + \
              ' 2) setting the intent code'

# Valid MGZ integer datatypes:
#  - UCHAR
#  - SHORT
#  - INT
# See: https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/MghFormat
# We use the '>' prefix because the MGH format is big-endian
mgz_dtypes = ['>u1', '>i2', '>i4']
mgz_dtype_info = []
for dtype_str in mgz_dtypes:
    dtype = np.dtype(dtype_str)
    info = np.iinfo(dtype)
    mgz_dtype_info.append((dtype_str, info.min, info.max))

# FreeSurfer label files
# todo; finalize

# What about:
#   - wm.seg.mgz
#   - wm.mgz
#   - rh.Yeo_Brainmap*
mgz_label_files = [
  'aparc+aseg.mgz',
  'aparc.DKTatlas+aseg.mgz',
  'aparc.a2005s+aseg.mgz',
  'aparc.a2009s+aseg.mgz',
  'apas+head.mgz',
  'aseg.auto.mgz',
  'aseg.auto_noCCseg.mgz',
  'aseg.mgz',
  'aseg.presurf.hypos.mgz',
  'aseg.presurf.mgz',
  'ctrl_pts.mgz',
  'filled.auto.mgz',
  'filled.mgz',
  'gtmseg.mgz',
  'lh.ribbon.mgz',
  'rh.ribbon.mgz',
  'ribbon.mgz',
  'subcort.mask.1mm.mgz',
  'subcort.mask.mgz',
  'surface.defects.mgz',
  'wm.asegedit.mgz',
  'wmparc.mgz'
]

# Setup logging
logger = logging.getLogger(__name__)
    
def parse_args():
    parser = argparse.ArgumentParser(description=script_desc)
    parser.add_argument('-i', '--inpath', required=True, help='Input path (required)')
    parser.add_argument('-o', '--outpath', required=False, help='Output path')
    parser.add_argument('-f', '--force', action='store_true', help='Force conversion to ints')
    parser.add_argument('--log-level', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='WARNING',
                        help='Set the logging level')

    # Create mutually exclusive group to manage intent code options
    intent_group = parser.add_mutually_exclusive_group()
    intent_group.add_argument('--auto-detect-intent', 
                              action='store_true',
                              default=True,
                              help='Auto-detect intent from filename; if its a label file, set intent to 1 otherwise ignore (default)')
    intent_group.add_argument('--is-imaging-data', 
                              action='store_true',
                              help='Set intent code to 0')
    intent_group.add_argument('--is-label-data', 
                              action='store_true',
                              help='Set intent code to 1')
    intent_group.add_argument('--ignore-intent',
                              action='store_true',
                              help='Dont change intent codes at all')

    args = parser.parse_args()
    return args

def check_args(args):
    infilelist = []
    outfilelist = []
    intent = None

    # Intent:
    #   - 0: Always set intent code to 0 (imaging data)
    #   - 1: Always set intent code to 1 (label data)
    #   - -1: Auto-detect intent code from filename
    #   - None: Never alter intent code
    if args.is_imaging_data:
        intent = 0
    elif args.is_label_data:
        intent = 1
    elif args.auto_detect_intent:
        intent = -1
        
    try:
        inpath = pathlib.Path(args.inpath)
        if args.outpath is not None:
            outpath = pathlib.Path(args.outpath)
        else:
            outpath = None

        if not inpath.exists():
            raise ValueError(f'path does not exist: {args.inpath}')
        if inpath.is_file():
            infilelist.append(inpath.absolute())
            if outpath is None:
                # The file will be overwritten in place
                outfilelist.append(inpath.absolute())
            elif outpath.is_dir():
                outfilelist.append(os.path.join(outpath.absolute, inpath.name))
            elif outpath.is_file():
                outfilelist.append(outpath.absolute())
            else:
                raise ValueError(f'outpath is neither a file nor a directory: {args.outpath}')
        elif inpath.is_dir():
            # If inpath is a dir and outpath is defined, it must also be a dir
            if outpath is None:
                outpath = inpath
            if outpath.is_file():
                raise ValueError(f'outpath has been defined as a file, but inpath is a dir.  inpath: {args.inpath}; outpath: {args.outpath}')
            mgz_files = list(inpath.rglob('*.mgz'))
            for mgz_file in mgz_files:
                infilelist.append(os.path.join(inpath.absolute(), mgz_file.absolute()))
                outfilelist.append(os.path.join(outpath.absolute(), mgz_file.absolute()))
        else:
            raise ValueError(f'inpath is neither a file nor a directory: {args.inpath}')
    except (OSError, ValueError, AssertionError) as e:
        error_msg = str(e)
        logger.error(f'caught an exception: {error_msg}', exc_info=True)
        raise
    return infilelist, outfilelist, intent
            
def find_best_dtype(np_array, possible_dtypes=mgz_dtype_info):
    min_val = np.min(np_array)
    max_val = np.max(np_array)
    # Find the smallest dtype that can accommodate the range
    for dtype_str, dtype_min, dtype_max in possible_dtypes:
        if dtype_min <= min_val and max_val <= dtype_max:
            return dtype_str
    return None

def guess_intent_code_from_filename(filename):
    # Strip the directory info
    file = os.path.basename(filename)
    if file in mgz_label_files:
        return 1
    else:
        return None

def optimize_mgz(infile, outfile, intent=-1, force_convert_to_ints=False):
    logger.debug(f'infile:  {infile}')
    logger.debug(f'outfile: {outfile}')
    logger.debug(f'intent:  {intent}')
    logger.debug(f'force_convert_to_ints: {force_convert_to_ints}')

    logger.info(f'loading mgz file: {infile}')
    try:
        mgz = sf.load_volume(infile)
    except Exception as e:
        logger.warning(f'Caught an exception when trying to load {infile}')
        logger.warning(f'{e}', exc_info=True)
        logger.warning(f'Skipping this file')
        return
    logger.debug(f'metadata for {infile}: {mgz.metadata}')

    if not np.issubdtype(mgz.dtype, np.integer) and not force_convert_to_ints:
        logger.info(f'mgz file is not integer based and --force is not enabled; skipping')
    else:
        new_dtype = find_best_dtype(mgz.data)
        logger.debug(f'Best dtype for this file is {new_dtype}')
        if new_dtype is None:
            logger.warning(f'Cant find a suitable dtype for {infile}; just copying the file as-is')
            mgz_new = mgz.copy()
        else:
            mgz_new = mgz.astype(new_dtype)
        # PW: Shouldn't this be done by mgz.copy() and mgz.astype()?
        mgz_new.metadata = mgz.metadata.copy()
        # if intent code is already set, and force is not set; skip
        if intent is None:
            pass
        elif intent == -1:
            # try to guess the intent code from the filename
            intent = guess_intent_code_from_filename(infile)
            logger.info(f'intent was None, so I guessed from the filename that it should be {intent}')
        if intent is not None:
            logger.debug(f"setting metadata['intent'] to {intent}")
            mgz_new.metadata['intent'] = intent
        else:
            logger.debug(f'--ignore-intent was set, not setting or changing intent code')
        logger.info(f'Writing to file: {outfile}')
        logger.debug(f'metadata for {outfile}: {mgz_new.metadata}')
        mgz_new.save(outfile)

def main():
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )
    logger.debug(f'args: {args}')
    logger.debug(f'mgz_dtype_info: {mgz_dtype_info}')
    logger.debug(f'mgz_label_files: {mgz_label_files}')

    infilelist, outfilelist, intent = check_args(args)

    logger.debug(f'infilelist: {infilelist}')
    logger.debug(f'outfilelist: {outfilelist}')
    logger.debug(f'intent: {intent}')
    assert(len(infilelist) == len(outfilelist))

    for i in range(len(infilelist)):
        logger.debug('------------------------------')
        optimize_mgz(infilelist[i], outfilelist[i], intent=intent, force_convert_to_ints=args.force)
    return 0

if __name__ == "__main__":
    sys.exit(main())
