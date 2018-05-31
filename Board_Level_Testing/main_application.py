#!/usr/bin/python

##################################################################################
#Every test in testing firmware should be designed in such a way that output over#
#UART will be in format-> test_variable : int_value. This will ensure proper######
#working of this python application. Also every output should start with "\n"(new#
# line character) followed by "START\n" string;then test results, and should end #
#with "END\n" string.############################################################# 
##################################################################################

import yaml
import io
import os
from datetime import date
import mysql
import mysql.connector
import MySQLdb
import requests
import binascii
import serial
import subprocess
import sys
from pygdbmi.gdbcontroller import GdbController

#important funtion:

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
#This function is used to extract test_variable_name from result string###########
##################################################################################
def extractTitles(txt_format):
    if(txt_format != "END\n"):
        txt_format = list(txt_format)
        txt_format = txt_format[:txt_format.index(':')-1]
        txt_format = ''.join(txt_format)
        return str(txt_format)
    else:
        return

##################################################################################
#In this function we establish Python-Mysql connection. And return that ##########
#connection value.################################################################
##################################################################################
def mysql_connect():
    try:
        conn = MySQLdb.connect( host = "localhost", user = "root", passwd = "root", db = "python_mysql")
        if (conn):
            print ("MySQL databse connected:" + str(conn))
    except Error as e:
            print (e)
    return conn;

##################################################################################
#As every board will have different number of tests. Every MySQL table may and ###
#will contain different number of columns This function will add those extra #####
#columns to the respective table.#################################################
##################################################################################
def append_table_for_(txt_file, first_part, mysql_cursor):
    txt_ip = txt_file.readline();
    while (txt_ip != "END\n"):
        field_name = extractTitles(txt_ip)
        txt_ip = txt_file.readline()
        alter_query = ("alter table " + first_part + " add " + field_name + " varchar(20)")
        mysql_cursor.execute(alter_query)
    return;

##################################################################################
#This function will insert int_value (test results) into it's respective column###
##################################################################################
def insert_data_from_(txt_file, first_part, mysql_cursor, board_no):
    txt_ip = txt_file.readline();
    while (txt_ip != "END\n"):
        field_name = extractTitles(txt_ip)
        data_value = extractData(txt_ip)
        data_value = str(data_value)
        insert_data = {
            'first_part' : str(first_part),
            'field_name' : str(field_name),
            'data_value' : str(data_value),
            'board_no' : str(board_no)
        }
        update_query = ("update "+first_part+ " set " + field_name+"="+data_value+ " where Product_ID=%(board_no)s")
        mysql_cursor.execute(update_query, insert_data)
        txt_ip = txt_file.readline()
    return;


##################################################################################
#This function will generate a list containing all the test_variable_names. ######
##################################################################################
def getAllTitles(txt_file):
    temp_list = []
    flag = 1
    while (flag == 1):
        temp_data = txt_file.readline()
        if(temp_data == "END\n"):
            flag = 0
        if(flag == 1):
            temp_list.append(extractTitles(temp_data))
    return temp_list

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


##################################################################################
#######################MAIN FUNCTION STARTS FROM HERE#############################
##################################################################################


#Checking for Hardware and Toolchain
##################################################################################
#This part of program will check presence of BMP debugger and ARM cross compiler##
#toolchain. if either of them are not present then program will be terminated.####
##################################################################################

debugger_flag = 1
arm_toolchain_flag = 1
board_detect_flag = 1
try:
    subprocess.check_output(["ls", "/dev/ttyBmpTarg"])

except:
    debugger_flag = 0
try:
    subprocess.check_output(["ls", "/usr/local/gcc-arm-none-eabi-6-2017-q2-update/bin/arm-none-eabi-gdb"])
except:	
    arm_toolchain_flag = 0
 
#This part will check is board is connected properly or not by creating and ######
#reading a log file for GDB.######################################################

os.system("touch gdb_log.txt")
GDB = "/usr/local/gcc-arm-none-eabi-6-2017-q2-update/bin/arm-none-eabi-gdb"
os.system(GDB + " -ex 'set loggin file ./gdb_log.txt' -ex 'set logging overwrite on' -ex 'set logging redirect on' -ex 'set logging on' -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor tpwr enable' -ex 'monitor swdp_scan' -ex 'set logging off' -ex 'quit' ")
log_file = open("./gdb_log.txt","r")
file_contents = log_file.readlines()
log_file.close()
err_msg = (file_contents[len(file_contents) -1])
print(err_msg)
if((err_msg == "SW-DP scan failed!\n")):
    board_detect_flag = 0

os.system("rm gdb_log.txt")
os.system("clear")
if(debugger_flag == 0):
    print("Debugger not present..!!")
if(arm_toolchain_flag == 0):
    print("ARM toolchain not present..!!")
if(board_detect_flag == 0):
    print("Board not detected..!!")
if(not(debugger_flag & arm_toolchain_flag & board_detect_flag)):
    raw_input("Press Enter to exit..!!")
    sys.exit(0)




#Generation of first part

##################################################################################
#First part of product key is generated using product_id_config.yaml. This file###
#contains Board ID, Revision number, and factory number###########################
##################################################################################
fp_config = "./product_id_config.yaml"
configfile = open(fp_config, "r")
config_load = yaml.load(configfile)
product = config_load['Product']
revision = config_load['Revision']
factory = config_load['Factory']
first_part = product + revision + factory

#creating directry with name = first_part
try:
    os.system("mkdir "+first_part)
except OSError: 
    pass

#Generation of second part

##################################################################################
#Second part of product key is a date stamp in yymmdd format. this part is #######
#generated over here. If yy and/or mm and/or dd is less than 10 then code will ###
#add "0" before it to keep format intact. ########################################
##################################################################################
today = date.today()
if ((today.year%100) < 10):
    year = str("0" + str(today.year%100))
else:
    year = str(today.year%100)
if ((today.month) < 10):
    month = str("0" + str(today.month))
else:
    month = str(today.month)
if ((today.day) < 10):
    day = str("0" + str(today.day))
else:
    day = str(today.day)
second_part = year + month + day





#Product_ID generation

##################################################################################
#This part will count the number of board and generate entire product id which is#
#to be written in the memory of board for further assesment#######################
##################################################################################
fp = str("./"+first_part+"/"+first_part+".yaml")
os.system("touch "+fp)
infile = open(fp, "r+")
data = yaml.load(infile)    
empty_doc = None
if (data == empty_doc):
#If this is the first board which is being tested ever. Assign default board_no###
    board_no =(first_part + second_part + "0001")
else :
    product_list = data['Boards']['Board_No']
    product_stamp = (product_list)
#first 6 characters of product id represents product stamp of particular board####
    product_stamp = (product_stamp[0:6])
    product_stamp = ''.join(product_stamp)
    date_stamp = list(product_list)
#Characters 7-12 of product_id represents date stamp of particular board##########
    date_stamp = (date_stamp[6:12])
    date_stamp = ''.join(date_stamp)
    if(product_stamp == first_part):
        if (date_stamp == second_part):
#if product stamp and date stamp matches then increment the count of board_no#####
            product_id = list(product_list)
#Charater 13-16 of product_id represents count of boards associated with that ####
#particular board specifications##################################################
            product_id = (product_id[12:16])
            product_id = ''.join(product_id)
            board_no_temp = int(product_id)
            board_no_temp = board_no_temp+ 1
            if (board_no_temp < 10):
                board_no_str = "000" + str(board_no_temp)
            elif(board_no_temp >=10 and board_no_temp < 100):
                board_no_str = "00" + str(board_no_temp)
            elif (board_no_temp >=100 and board_no_temp < 1000):
                board_no_str = "0" + str(board_no_temp)
            else :
                board_no_str = str(board_no_temp)
            board_no = ( first_part + second_part + board_no_str)
        else :
            board_no = ( first_part + second_part + "0001" )
    else :
        board_no = (first_part + second_part + "0001")
infile.close()

#Generation of .hex file
##################################################################################
#This part of code will generate hex file which is to be merged with main testing#
#firmware. This hex file will contain instrction to write product_id into UICR ###
#registers. ######################################################################
##################################################################################

#Data which is to be written in UICR via hex file has to written backwards for ###
#every register separately. So this part reverses whole string and assign proper##
#output to respective variable. ##################################################

board_list = list(board_no)
board_list.reverse()
board_list = ''.join(board_list)
board_no_reverse = board_list
reg_UICR_0 = (binascii.hexlify(board_list[12:16]))
reg_UICR_1 = (binascii.hexlify(board_list[8:12]))
reg_UICR_2 = (binascii.hexlify(board_list[4:8]))
reg_UICR_3 = (binascii.hexlify(board_list[0:4]))

#At the end of end of every line of hex file there is checksum byte. Which is ####
#LSB of 2's complement of sum of all bytes presents in that line. This is useful##
#to check is right data is being written in controller's memory###################
board_no_list = list(board_no_reverse)
byte_list = []
for i in board_no_list:
    byte_list.append(binascii.hexlify(i))
#0x0A is a calculated sum for initital address of UICR0 and other information#####
#ONE SHOULD NEVER CHANGE THIS VALUE UNTIL ONE WHISHES TO CHANGE THE UICR REGISTERS
#WHERE PRODUCT_ID IS TO BE STORED#################################################
xor_chk_sum = "0xA0"
for i in byte_list:
    xor_chk_sum = int(str(xor_chk_sum),16) + (int(i,16))
    xor_chk_sum = hex(xor_chk_sum)
print(xor_chk_sum)
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

product_id_reg = reg_UICR_0 + reg_UICR_1 + reg_UICR_2 + reg_UICR_3 + chk_sum

#Generation of hex file###########################################################
hexfp = "./"+first_part+'/'+"product_id.hex"
os.system("touch "+hexfp)
product_id_hex = open(hexfp, "w")
hex_file_contents = """:020000041000EA
:10108000"""+product_id_reg+"""
:00000001FF
"""
product_id_hex.write(hex_file_contents)
product_id_hex.close()




#Program execution and Writing test data in txt file

##################################################################################
#This part of code actully communicates with controller. In this part code will###
#merge firmware hex file and hex file it generated containing product id. This ###
#part will also erase previous data and upload hex file. Output from UART will be#
#saved in one text file which will be useful for debugging########################
##################################################################################
fp_txt_input = "./"+first_part+'/'+first_part+"_output.txt"
os.system("touch "+fp_txt_input)
data_file = open(fp_txt_input, "w")
port = serial.Serial("/dev/ttyBmpTarg", baudrate=1000000, bytesize = serial.EIGHTBITS, timeout = 40)
flag = 0

mrg_hex = str("srec_cat "+"./"+first_part+"/product_id.hex -Intel "+"./source_hex/"+first_part+"_v_*.hex -Intel"+" -O "+"./"+first_part+"/"+first_part+".hex -Intel --line-length=44")
os.system(mrg_hex)

GDB = "/usr/local/gcc-arm-none-eabi-6-2017-q2-update/bin/arm-none-eabi-gdb"
eraseall = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'mon erase_mass' -ex 'detach' -ex 'quit';")
os.system(eraseall)

upload = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'load ./"+first_part+"/"+first_part+".hex'" " -ex 'compare-sections' -ex 'detach' -ex kill -ex 'quit';" )
os.system(upload)


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
os.system("rm ./"+first_part+"/product_id.hex")
os.system("rm ./"+first_part+"/"+first_part+".hex")


#Checking Final Status of board level testing

##################################################################################
#This part will check the final status of hardware testing. If status is 1 then###
#upload the sense_pi firmware to board############################################
##################################################################################
fp_txt_input = "./"+first_part+'/'+first_part+"_output.txt"
data_file = open(fp_txt_input, "r")
status_flag = 0
file_data = "START\n"
while(file_data != "END\n"):
    file_data = data_file.readline()
    temp_title = extractTitles(file_data)
    if(temp_title == "Status"):
        temp_data = extractData(file_data)
        if(temp_data == 1):
            status_flag = 1
if(status_flag == 1):
    upload = str(GDB+" -ex 'target extended-remote /dev/ttyBmpGdb' -ex 'monitor swdp_scan' -ex 'attach 1' -ex 'load ./source_hex/SensePi_v_0_1_0.hex' -ex 'compare-sections' -ex 'detach' -ex kill -ex 'quit';" )
    print(upload)
    os.system(upload)

        



#Writing into yaml file:

##################################################################################
#This part will write test data and result into yaml file. YAML is data file, ####
#where test data of all the previous board is written and this is in human #######
#readable format. So it is easier to keep track of all the test results. #########
##################################################################################
#Getting input from output data file 
#Test data which is to be written in yaml file is exctracted from text files######
fp_txt_input = "./"+first_part+'/'+first_part+"_output.txt"
txt_input = open(fp_txt_input, "r")
title_list = getAllTitles(txt_input)
txt_input.close()
txt_input = open(fp_txt_input, "r")
data_list = getAllData(txt_input)
txt_input.close()
#This part will generate a dictinory which is to be loaded into YAML file#########
outfile = open (fp,"a")
board_no_dict = dict(zip(title_list,data_list))
Boards_dict = dict(Board_No = board_no, Results = board_no_dict)
basic_info = dict(Boards = Boards_dict)
yaml.dump(basic_info, outfile, indent = 4, default_flow_style = False)
outfile.close()


#MySQL DATABASE:

##################################################################################
#This part of code will load test data into table. This data might be useful for #
#checking all the logs. And also might be useful to do some analysis if required##
##################################################################################
fp_txt_input = "./"+first_part+'/'+first_part+"_output.txt"
txt_input = open(fp_txt_input, "r")
conn = mysql_connect()
mysql_cursor = conn.cursor()

#Every table will have these 3 fields. Therefore while creating table these 3 ####
#fields will always be there. Once table is created we will append that table and#
#add whatever fields are required. ###############################################
create_table_query = ("create table " + first_part + "(id int(10) auto_increment primary key, Product_ID varchar(17), date_stamp timestamp not null)")
try:
    mysql_cursor.execute(create_table_query)
    append_table_for_(txt_input, first_part, mysql_cursor)
except :
    pass

txt_input.close()

txt_input = open(fp_txt_input, "r")
insert_basic_data = {
    'first_part' : first_part,
    'board_no' : board_no
}

basic_insert_query = ("insert into " +first_part+ " (Product_ID) values  (%(board_no)s) ")
mysql_cursor.execute(basic_insert_query, insert_basic_data)
insert_data_from_(txt_input, first_part, mysql_cursor, board_no)
conn.commit()
mysql_cursor.close()
conn.close()


print("Board Number = "+board_no)
file_exit_flag = 'n'
while(not(file_exit_flag == 'y' or file_exit_flag == 'Y')):
    print("Write the board number on board..!!")
    file_exit_flag = raw_input("Done?(y/n):")

