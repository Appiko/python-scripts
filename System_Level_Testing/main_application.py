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
    if(txt_format != "END\n" or txt_format != "START\n"):
        txt_format = list(txt_format)
        txt_format = txt_format[(txt_format.index(':')+2):txt_format.index("\n")]
        txt_format = ''.join(txt_format)
        return int(txt_format)
    else:
        return;

##################################################################################
#This function is used to extract test_variable_name from result string###########
##################################################################################
def extractTitles(txt_format):
    if(txt_format != "END\n" or txt_format != "START\n"):
        txt_format = list(txt_format)
        txt_format = txt_format[:txt_format.index(':')-1]
        txt_format = ''.join(txt_format)
        return str(txt_format)
    else:
        return;

##################################################################################
#In this function we establish Python-Mysql connection. And return that ##########
#connection value.################################################################
##################################################################################
def mysql_connect():
    try:
        conn = MySQLdb.connect( host = "localhost", user = "root", passwd = "root", db = "python_mysql")
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
    return


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
#This Function is used to create directory to store all the output files. ########
##################################################################################
def create_op_dir(board_no):
    first_part = ''.join(list(board_no)[:6])
    try:
        subprocess.check_output(["ls", first_part])
    except:
        os.system("mkdir ./"+first_part)
    os.system("cd ./"+first_part)
    fp_op = "./"+first_part+'/'+first_part+"_output.txt"
    os.system("touch "+fp_op)
    txt_file = open(fp_op, "w")
    txt_file.close()
    return first_part

##################################################################################
#This Function is used to write output text file which will be used to generate###
#other files and write into MySQL table###########################################
##################################################################################
def write_op_txt(line_data):
    global first_part
    fp_op = "./"+first_part+'/'+first_part+"_output.txt"
    os.system("touch "+fp_op)
    txt_file = open(fp_op, "a")
    txt_file.write(line_data)
    txt_file.close()
    return;

##################################################################################
#This function is  here to extract product id#####################################
##################################################################################        
def extractBoardNumber(txt_format):
    txt_format = list(txt_format)
    txt_format = txt_format[(txt_format.index(':')+2):txt_format.index("\n")]
    txt_format = ''.join(txt_format)
    return str(txt_format);    

##################################################################################
#This function will get line data and take decisions according to Parameter which#
#is being printed and it's respective value.######################################
##################################################################################
def data_process(line_data,port_ble):
    global first_part
    global board_no
    param = extractTitles(line_data)
    if(param == "Product_ID"):
        board_no = extractBoardNumber(line_data)
        first_part = create_op_dir(board_no)
    else:
        value = extractData(line_data)
        if(param == "BLE_Status" and value == 1):
            port_ble.write("PIR\n")
            port_heat = serial.Serial("/dev/ttyUSB0", baudrate=1000000, bytesize = serial.EIGHTBITS, timeout = 40)
            port_heat.readline()
            port_heat.write("G0 X850.0 F10000\n")
            port_heat.write("G0 X0.0 F10000\n")
            write_op_txt(line_data)
        else:
            write_op_txt(line_data)
    return;

##################################################################################
#This part of code will load test data into table. This data might be useful for #
#checking all the logs. And also might be useful to do some analysis if required##
##################################################################################
def edit_mysql_db():
    global first_part
    global board_no
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
    except :
        pass
    try:
        append_table_for_(txt_input, first_part, mysql_cursor)
    except:
        pass
    txt_input.close()

    txt_input = open(fp_txt_input, "r")
    insert_data_from_(txt_input, first_part, mysql_cursor, board_no)
    conn.commit()
    mysql_cursor.close()
    conn.close()
    print("MySQL database updated successfully\n")
    return;

##################################################################################
#This func will write test data and result into yaml file. YAML is data file, ####
#where test data of all the previous board is written and this is in human #######
#readable format. So it is easier to keep track of all the test results. #########
##################################################################################
#Getting input from output data file 
#Test data which is to be written in yaml file is exctracted from text files######
def create_yaml_db():
    global first_part
    global board_no
    fp_txt_input = "./"+first_part+'/'+first_part+"_output.txt"
    txt_input = open(fp_txt_input, "r")
    title_list = getAllTitles(txt_input)
    txt_input.close()
    txt_input = open(fp_txt_input, "r")
    data_list = getAllData(txt_input)
    txt_input.close()
    #This part will generate a dictinory which is to be loaded into YAML file#########
    fp_yaml_op = "./"+first_part+'/'+first_part+".yaml"
    os.system("touch "+fp_yaml_op)
    outfile = open (fp_yaml_op,"a")
    board_no_dict = dict(zip(title_list,data_list))
    Boards_dict = dict(Board_No = board_no, Results = board_no_dict)
    basic_info = dict(Boards = Boards_dict)
    yaml.dump(basic_info, outfile, indent = 4, default_flow_style = False)
    outfile.close()
    print("YAML data updated successfully\n")

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
    input("Exiting the program..!!\nPress Enter:")
    sys.exit(0)

#Program execution and Writing test data in txt file
##################################################################################
#This part of code actully communicates with controller. In this part code will###
#merge firmware hex file and hex file it generated containing product id. This ###
#part will also erase previous data and upload hex file. Output from UART will be#
#saved in one text file which will be useful for debugging########################
##################################################################################
first_part = "0"
board_no = "NULL"

port = serial.Serial("/dev/ttyBmpTarg", baudrate=1000000, bytesize = serial.EIGHTBITS, timeout = 100)
flag = 0
port.write("SCN\n");
while(flag == 0):
    line_data = port.readline()
    if (line_data == "START\n"):
        flag = 1
while (flag == 1) :
    line_data = (port.readline())
    print(line_data)
    if(line_data == "END\n"):
        write_op_txt(line_data)
        flag =0
    if(flag != 0):
        data_process(line_data, port)
port.close()
create_yaml_db()
edit_mysql_db()

file_exit_flag = "n"
while(not(file_exit_flag == "y" or file_exit_flag == "Y")):
    print("End of Program..!!")
    file_exit_flag = raw_input("Do you want to exit?(y/n): ")

