#!/usr/bin/env python3

import logging
import sys
import argparse

import numpy as np
import surfa as sf


script_desc = 'Check if an mgz file can safely converted ints'

# Setup logging
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description=script_desc)
    parser.add_argument('-i', '--infile', required=True, help='Input file (required)')
    parser.add_argument('--only-print-true', action='store_true', help='Only print the file if it can be safely converted')
    parser.add_argument('--log-level', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='WARNING',
                        help='Set the logging level')
    args = parser.parse_args()
    return args
    
def can_convert_to_int(numpy_array, tol=1e-10, dtype=np.int32):
    
    if np.issubdtype(numpy_array.dtype, np.integer):
        return False, f"Array is alreay an integer type ({numpy_array.dtype})"

    # Check if conversion is safe
    if np.any(np.isnan(numpy_array)):
        return False, "Array contains NaN values"

    if np.any(np.isinf(numpy_array)):
        return False, "Array contains infinity values"

    rounded_array = np.round(numpy_array)
    if not np.allclose(numpy_array, rounded_array, rtol=0, atol=tol):
        max_dev = np.max(np.abs(numpy_array - rounded_array))
        return False, f"Values deviate from integers by up to {max_dev}"
    
    return True, "Safe to convert to ints"

def main():
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
    )
    logger.debug(f'args: {args}')

    try:
        mgz = sf.load_volume(args.infile)
    except Exception as e:
        logger.warning(f'Caught an exception when trying to load {args.infile}')
        logger.warning(f'{e}')
        logger.warning(f'Skipping this file')
        return 1
    
    safe_to_convert_to_ints, reason = can_convert_to_int(mgz.data)
    
    if not args.only_print_true or (args.only_print_true and safe_to_convert_to_ints):
        print(f'File: {args.infile}')
        print(f'{safe_to_convert_to_ints}\t{reason}')
    
if __name__ == "__main__":
    sys.exit(main())
