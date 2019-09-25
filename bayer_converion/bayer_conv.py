#!/usr/bin/python

import os
import getopt
import sys
import glob
import subprocess
from datetime import datetime


def extract_filename(filename):
    dt = str(datetime.timestamp(datetime.now())).split('.')[0]
    name = filename.split('/')[-1].split(".")[0]
    filename = dst_dir + dt + "_" + name + ".ppm"
    return filename


def parse_src_dir():
    for filename in glob.glob(os.path.join(src_dir, '*.rgb*')):
        op_file = extract_filename(filename)
        running = f"./a.out {filename} {op_file}"
        print(f"\n\nRunning: {running}\r")

        subprocess.call(["./a.out",
                         filename,
                         op_file,
                         ])


def print_help():
    print("""
    Application to convert Appiko RGB RAW files to PPM files
    Usage: ./bayer_conv.py [options]
        -h --help           Help
        -s --src_dir        Source Directory
        -d --dst_dir        Destination Directory
        -z --size           Size `10x20` (widthxheight)

    Example: 
        python bayer_conv.py -s /mnt  -d ./new/ -z 1280x960

    Make sure you compile the a.c file and/or a.out is executable.
    if it's not executable `chmod +x ./a.out`
    """)


def opt_handle(arglist):
    global src_dir
    global dst_dir
    global size

    try:
        opts, args = getopt.getopt(
            arglist,
            "hs:d:z:", [
                "help",
                "src_dir ",
                "dst_dir ",
                "size",
            ])
    except getopt.GetoptError:
        print("Error")
    for opt, arg in opts:
        if opt in["-h", "--help"]:
            print_help()
        if opt in["-s", "--src_dir"]:
            src_dir = arg
            if(src_dir == '\0'):
                print_help()
                sys.exit()
        if opt in["-d", "--dst_dir"]:
            dst_dir = arg
            if(dst_dir == '\0'):
                print_help()
                sys.exit()
        if opt in["-z", "--size"]:
            size = arg


src_dir = " "
dst_dir = " "
size = ""


opt_handle(sys.argv[1:])

subprocess.call(["gcc",
                 f"-DPIX_W={size.split('x')[0]}",
                 f"-DPIX_H={size.split('x')[1]}",
                 "./bayer_conv.c"])

parse_src_dir()
