#!/usr/bin/python

import os
import serial
import binascii
import getopt
import sys

GDB = "/usr/local/gcc-arm-none-eabi-6-2017-q2-update/bin/arm-none-eabi-gdb"

def intToHexStr (var):
    var = list(str(hex(var)))
    var = ''.join(var[2:])
    return var


def charToASCII(lst):
    temp_lst= []
    lst = list(lst)
    for i in range(len(lst)):
        temp_lst.append((ord(lst[i])))
        temp_lst[i] = intToHexStr (temp_lst[i])
    temp_lst = ''.join(temp_lst)
    return temp_lst

def split_len(seq, length):
    return [seq[i:i+length] for i in range(0, len(seq), length)]

##################################################################################
#This function is used to exctact int_value from test result string. #############
##################################################################################
def extractData(txt_format):
    if(txt_format != "END\n"):
        txt_format = list(txt_format)
        txt_format = txt_format[(txt_format.index(':')+1):txt_format.index("\n")]
        txt_format = ''.join(txt_format)
        return int(txt_format)
    else:
        return

##################################################################################
#This function will generate a list containing all the result_int_value. #########
##################################################################################
def getAllData(txt_file):
    temp_list = []
    flag = 1
    while (flag == 1):
        temp_data = txt_file.readline()
        if(temp_data == "END\n"):
            flag = 0
        if(flag == 1):
            temp_list.append(extractData(temp_data))
    return temp_list



    #Upload program which will extract Board no.
def extractBoardNo():
    fp_txt_input = "./board_no.txt"
    os.system("touch "+fp_txt_input)
    data_file = open(fp_txt_input, "w")
    port = serial.Serial("/dev/ttyBmpTarg", baudrate=1000000, bytesize = serial.EIGHTBITS, timeout = 40)

    upload = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'load' -ex 'compare-sections' -ex 'detach' -ex 'kill' -ex 'quit' ./board_no_extract.hex;" )
    os.system(upload)
    flag = 0
    line_data = ""
    prev_data = ""
    while(flag == 0):
        line_data = port.readline()
        if (line_data == "START\n"):
            flag = 1
    while (flag == 1) :
        line_data = (port.readline())
        if(line_data != prev_data):
            print(line_data)
            data_file.write(line_data)
            if(line_data == "END\n"):
               flag =0
        prev_data = line_data
    data_file.close()
    port.close()

    #Save that board no locally.
    fp_txt_input = "./board_no.txt"
    data_file = open(fp_txt_input, "r")
    board_no_seg = getAllData(data_file)
    board_no = ""
    board_no_str_arr = []
    for i in board_no_seg:
        board_no = board_no + str(i)
        board_no_str_arr.append(str(i)) 
    #board_no = list(board_no)
    print(board_no)
    board_no = split_len(board_no,2)
    data_file.close()
    return board_no

#def createBoardNo (board_no_arg):


def prductIdHexGen ():
    print("Product Id Generation : ")
    global board_no
    xor_chk_sum = "0xA0"
    for i in board_no:
        xor_chk_sum = int(str(xor_chk_sum),16) + int(i,16)
        xor_chk_sum = hex(xor_chk_sum)
    #This is one of the methods to calculate 1's complement, subtracting value from###
    #largest value possible. #########################################################
    #We need only LSB therefore anding sum value with 0xFF############################
    xor_chk_sum = int("0xffff",16) - int(xor_chk_sum,16)
    chk_sum = xor_chk_sum + 0x01
    chk_sum = (chk_sum  &  int("0xff",16))
    #Converting calculated checksum value in standard format to write in hex file#####
    if(chk_sum<16):
        chk_sum = list(str(hex(chk_sum)))
        chk_sum = "0"+''.join(chk_sum[2:3])
    else:
        chk_sum = list(str(hex(chk_sum)))
        chk_sum = ''.join(chk_sum[2:4])

    #Production ID with check sum#####################################################

    board_no = ''.join(board_no)

    product_id_reg = board_no + str(chk_sum)

    print("\t"+product_id_reg)
    #Make board_no.hex
    hexfp = "./product_id.hex"
    os.system("touch "+hexfp)
    product_id_hex = open(hexfp, "w")
    hex_file_contents = """:020000041000EA
:10108000"""+product_id_reg+"""
:00000001FF
"""
    product_id_hex.write(hex_file_contents)
    product_id_hex.close()


#Merge board_no.hex with output.hex as firmware.hex
def mergeUpload ():
    global fw_addr
    print("Merge and Upload: ")

    mrg_hex = str("srec_cat ./product_id.hex -Intel "+fw_addr+" -Intel -O ./output.hex -Intel --line-length=44")
    os.system(mrg_hex)

    #Upload Firmware.hex

    GDB = "/usr/local/gcc-arm-none-eabi-6-2017-q2-update/bin/arm-none-eabi-gdb"
    eraseall = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'mon erase_mass' -ex 'detach' -ex 'quit';")
    os.system(eraseall)

    upload = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'load ./output.hex'" " -ex 'compare-sections' -ex 'detach' -ex kill -ex 'quit';" )
    os.system(upload)

def opt_handle (arglist):
    global fw_addr
    global board_no
    try:
        opts, args = getopt.getopt(
                        arglist,
                        "hp:f:", [
                        "help",
                        "product-id=",
                        "firmware="
                        ])
    except getopt.GetoptError:
        print("Error")
    for opt, arg in opts:
        if opt in["-h", "--help"]:
            print("""
Firmwre update script developed and used by Appiko
Usage: ./firmware_update [options]
    -h --help               Help Menu
    -p --product-id         Product ID which is to be written in nRF52810
    -f --firmware           Location of firmware which is to written
""")
            sys.exit ()
        if opt in["-p", "--product-id"]:
            board_no = arg
            if(len(board_no) != 16):
                print("Invalid ID")
                sys.exit ()
            else:
                board_no = charToASCII(board_no)
                board_no = split_len(board_no,2)

                print("Product Id : "+arg)
        if opt in["-f", "--firmware"]:
            fw_addr = arg
            print("Firmware Addr : "+fw_addr)



global board_no
board_no = ""
fw_addr = ""
opt_handle(sys.argv[1:])
if(board_no == ""):
    print ("Extract Product ID")
    board_no=extractBoardNo()
if(fw_addr == ""):
    fw_addr = "./firmware.hex"
    print("Default : "+fw_addr)

prductIdHexGen()

mergeUpload()

