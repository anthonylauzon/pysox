#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Python wrapper around the SoX library.
This module requires that SoX is installed.
'''

from __future__ import print_function
import logging


from . import file_info
from . import core
from .core import sox
from .core import SoxError

from .transform import Transformer


logging.basicConfig(level=logging.DEBUG)

COMBINE_VALS = [
    'concatenate', 'merge', 'mix', 'mix-power', 'multiply'
]


class Combiner(Transformer):
    '''Audio file combiner.
    Class which allows multiple files to be combined to create an output
    file, saved to output_filepath.

    Inherits all methods from the Transformer class, thus any effects can be
    applied after combining.
    '''
    def __init__(self):
        super(Combiner, self).__init__()

    def build(self, input_filepath_list, output_filepath, combine_type,
              input_volumes=None):
        '''Builds the output_file by executing the current set of commands.

        Parameters
        ----------
        input_filepath_list : list of str
            List of paths to input audio files.
        output_filepath : str
            Path to desired output file. If a file already exists at the given
            path, the file will be overwritten.
        combine_type : str
            Input file combining method. One of the following values:
                * concatenate : combine input files by concatenating in the
                    order given.
                * merge : combine input files by stacking each input file into
                    a new channel of the output file.
                * mix : combine input files by summing samples in corresponding
                    channels.
                * mix-power : combine input files with volume adjustments such
                    that the output volume is roughly equivlent to one of the
                    input signals.
                * multiply : combine input files by multiplying samples in
                    corresponding samples.
        input_volumes : list of float, default=None
            List of volumes to be applied upon combining input files. Volumes
            are applied to the input files in order.
            If None, input files will be combined at their original volumes.

        '''
        file_info.validate_input_file_list(input_filepath_list)
        file_info.validate_output_file(output_filepath)
        _validate_combine_type(combine_type)
        _validate_volumes(input_volumes)

        input_format_list = _build_input_format_list(
            input_filepath_list, input_volumes
        )

        _validate_file_formats(input_filepath_list, combine_type)

        args = []
        args.extend(self.globals)
        args.extend(['--combine', combine_type])

        input_args = _build_input_args(input_filepath_list, input_format_list)
        args.extend(input_args)

        args.extend(self.output_format)
        args.append(output_filepath)
        args.extend(self.effects)

        status, out, err = sox(args)

        if status != 0:
            raise SoxError(
                "Stdout: {}\nStderr: {}".format(out, err)
            )
        else:
            logging.info(
                "Created %s with combiner %s and  effects: %s",
                output_filepath,
                combine_type,
                " ".join(self.effects_log)
            )
            if out is not None:
                logging.info("[SoX] {}".format(out))
            return True


def _validate_file_formats(input_filepath_list, combine_type):
    '''Validate that combine method can be performed with given files.
    Raises IOError if input file formats are incompatible.
    '''
    _validate_sample_rates(input_filepath_list, combine_type)

    if combine_type == 'concatenate':
        _validate_num_channels(input_filepath_list, combine_type)


def _validate_sample_rates(input_filepath_list, combine_type):
    ''' Check if files in input file list have the same sample rate
    '''
    sample_rates = [
        file_info.sample_rate(f) for f in input_filepath_list
    ]
    if not core.all_equal(sample_rates):
        raise IOError(
            "Input files do not have the same sample rate. The {} combine "
            "type requires that all files have the same sample rate"
            .format(combine_type)
        )


def _validate_num_channels(input_filepath_list, combine_type):
    ''' Check if files in input file list have the same number of channels
    '''
    channels = [
        file_info.channels(f) for f in input_filepath_list
    ]
    if not core.all_equal(channels):
        raise IOError(
            "Input files do not have the same number of channels. The "
            "{} combine type requires that all files have the same "
            "number of channels"
            .format(combine_type)
        )


def _build_input_format_list(input_filepath_list, input_volumes):
    '''Set input formats given input_volumes.

    Parameters
    ----------
    input_volumes : list of float, default=None
        List of volumes to be applied upon combining input files. Volumes
        are applied to the input files in order.
        If None, input files will be combined at their original volumes.

    '''
    n_inputs = len(input_filepath_list)
    input_format_list = []
    if input_volumes is None:
        vols = [1] * n_inputs
    else:
        n_volumes = len(input_volumes)
        if n_volumes < n_inputs:
            logging.warning(
                'Volumes were only specified for %s out of %s files.'
                'The last %s files will remain at their original volumes.',
                n_volumes, n_inputs, n_inputs - n_volumes
            )
            vols = input_volumes + [1] * (n_inputs - n_volumes)
        elif n_volumes > n_inputs:
            logging.warning(
                '%s volumes were specified but only %s input files exist.'
                'The last %s volumes will be ignored.',
                n_volumes, n_inputs, n_volumes - n_inputs
            )
            vols = input_volumes[:n_inputs]
        else:
            vols = [v for v in input_volumes]

    for vol in vols:
        input_format_list.append(['-v', '{}'.format(vol)])

    return input_format_list


def _build_input_args(input_filepath_list, input_format_list):
    ''' Builds input arguments by stitching input filepaths and input
    formats together.
    '''
    if len(input_format_list) != len(input_filepath_list):
        raise ValueError(
            "input_format_list & input_filepath_list are not the same size"
        )

    input_args = []
    zipped = zip(input_filepath_list, input_format_list)
    for input_file, input_fmt in zipped:
        input_args.extend(input_fmt)
        input_args.append(input_file)

    return input_args


def _validate_combine_type(combine_type):
    '''Check that the combine_type is valid.

    Parameters
    ----------
    combine_type : str
        Combine type.

    '''
    if combine_type not in COMBINE_VALS:
        raise ValueError(
            'Invalid value for combine_type. Must be one of {}'.format(
                COMBINE_VALS)
        )


def _validate_volumes(input_volumes):
    '''Check input_volumes contains a valid list of volumes.

    Parameters
    ----------
    input_volumes : list
        list of volume values. Castable to numbers.

    '''
    if not (input_volumes is None or isinstance(input_volumes, list)):
        raise TypeError("input_volumes must be None or a list.")

    if isinstance(input_volumes, list):
        for vol in input_volumes:
            if not core.is_number(vol):
                raise ValueError(
                    "Elements of input_volumes must be numbers: found {}"
                    .format(vol)
                )
