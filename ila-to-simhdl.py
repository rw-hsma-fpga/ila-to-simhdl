import sys
import os
import numpy as np
import re


# extra bit width for std_logic_vector
def get_vector_length(signalname) -> int:
  if re.fullmatch('^.*\[[\d].*:[\d].*\]$', signalname):
    lbuf = re.sub('^.*\[','',buf)
    lbuf = re.sub(':[\d].*\]$','',lbuf)
    lbufint = int(lbuf)
    rbuf = re.sub('\]$','',buf)
    rbuf = re.sub('^.*\[[\d].*:','',rbuf)
    rbufint = int(rbuf)
    return int(abs(rbufint - lbufint) + 1)
  else:
    return 0


# get left std_logic_vector index
def get_left_index(signalname) -> int:
  if re.fullmatch('^.*\[[\d].*:[\d].*\]$', signalname):
    lbuf = re.sub('^.*\[','',buf)
    lbuf = re.sub(':[\d].*\]$','',lbuf)
    return int(lbuf)
  else:
    return 0


# get right std_logic_vector index
def get_right_index(signalname) -> int:
  if re.fullmatch('^.*\[[\d].*:[\d].*\]$', signalname):
    rbuf = re.sub('\]$','',buf)
    rbuf = re.sub('^.*\[[\d].*:','',rbuf)
    return int(rbuf)
  else:
    return 0


# get literal string to assign
def get_assignment_literal(vector_length, hexval) -> str:
  if  int(vector_length)==0:
    return "'" + hexval + "'"  # std_logic
  if  (int(vector_length) % 4)==0:
    return "X\"" + hexval + "\"'"  # std_logic_vector, hex literal
  intval = int(hexval, 16)
  return "\"" + format(intval, '0>'+str(vector_length)+'b') + "\""



## Argument handling

if len(sys.argv) != 3:
  print("ERROR: Wrong number of arguments. Exiting.")
  sys.exit(1) # exit with error code 1

input_file = sys.argv[1]
output = sys.argv[2]

# check if output empty; return with error if so
if output == "":
  print("ERROR: Output name empty. Exiting.")
  sys.exit(1) # exit with error code 1
else:
  # generate output filenames
  output_vhd = output + ".vhd"
  output_vhi = output + ".vhi"

# check if input_file exists
if not os.path.isfile(input_file):
  print("ERROR: Input file not found. Exiting.")
  sys.exit(1) # exit with error code 1


# open CSVfile read-only and import data into CSVdata
CSVfile = open(input_file, 'r')
CSVdata = np.genfromtxt(CSVfile, dtype='str', delimiter=",")


## matrix preprocessing

# remove irrelevant columns # TODO make more configurable
dcolA = 1 # first column
dcolB = 12 # last column
CSVdata = np.delete(CSVdata, slice(dcolA,dcolB+1), 1);

# remove irrelevant row
drowA = 1 # first row
drowB = 1 # last row
CSVdata = np.delete(CSVdata, slice(drowA,drowB+1), 0);

# extract signal indices and widths
namerow = 0
lindices = []
rindices = []
vwidths = []
for col in range(namerow,len(CSVdata[0])):
  buf = CSVdata[namerow][col]
  # extract indices
  lindex = int(get_left_index(buf))
  rindex = int(get_right_index(buf))
  lindices = np.append(lindices, str(int(lindex)))
  rindices = np.append(rindices, str(int(rindex)))
  # calculate vector length
  vwidths = np.append(vwidths, str(int(get_vector_length(buf))))
CSVdata = np.insert(CSVdata, 1, rindices, 0)
CSVdata = np.insert(CSVdata, 1, lindices, 0)
CSVdata = np.insert(CSVdata, 1, vwidths, 0)
vwidthrow = 1
lindexrow = 2
rindexrow = 3

#print(CSVdata[0:5])
#exit(0)


# reduce signal names to relevant part
for col in range(namerow, len(CSVdata[0])):
  buf = CSVdata[namerow][col]
  # cut left side
  buf= re.sub('^.*SLOT_2_','',buf) # TODO make more configurable
  # cut right side
  buf= re.sub('_1$','',buf)
  buf= re.sub('_1\[.*\]$','',buf)
  CSVdata[namerow][col] = buf


# configure output
firstsample = 2
lastsample = 3
#ns_per_cycle = 10 # 1 / 100MHz = 10ns
sample_offset = 4 # Fifth row has first sample set
indent = "\t\t"

# open output_vhd write-only and write to it
output_vhd_file = open(output_vhd, 'w')

# VHDL file header
print("library ieee;", file=output_vhd_file)
print("use ieee.std_logic_1164.all;", file=output_vhd_file)
print("use ieee.numeric_std.all;", file=output_vhd_file)
print("", file=output_vhd_file)
print("entity " + output + " is", file=output_vhd_file)
print("\tgeneric ();" , file=output_vhd_file)
print("\tport (" , file=output_vhd_file)

# generate port list
for signal in range(1,len(CSVdata[namerow])):
  if int(CSVdata[vwidthrow][signal])!=0:
    lindex = int(CSVdata[lindexrow][signal])
    rindex = int(CSVdata[rindexrow][signal])

    vector_suffix = "_vector("
    if rindex > lindex:
      vector_suffix+= str(lindex) + " to " + str(rindex) + ")"
    else:
      vector_suffix+= str(lindex) + " downto " + str(rindex) + ")"
  else:
    vector_suffix = ""

  print("\t\t" + CSVdata[namerow][signal] +" : out std_logic" + vector_suffix + ";", file=output_vhd_file)
print("\t\t--" , file=output_vhd_file)
print("\t\tsample_enable : in std_logic;" , file=output_vhd_file)
print("\t\tsample_clock : in std_logic" , file=output_vhd_file)

print("\t);" , file=output_vhd_file)
print("end " + output + ";", file=output_vhd_file)
print("", file=output_vhd_file)
print("architecture stimuli of " + output + " is", file=output_vhd_file)
print("", file=output_vhd_file)
print("begin", file=output_vhd_file)

print("\tprocess", file=output_vhd_file)
print("\tbegin", file=output_vhd_file)

# generate sequential signal assignments
for sample in range(firstsample+sample_offset,lastsample+sample_offset+1):
  # print to output_vhd file
  print("\t\t-- Sample #",CSVdata[sample][0], file=output_vhd_file)
  print("\t\twait until (rising_edge(sample_clock) and sample_enable='1');", file=output_vhd_file)

  for signal in range(1,len(CSVdata[sample])):
    literal = get_assignment_literal(
                                      CSVdata[vwidthrow][signal],
                                      CSVdata[sample][signal])
    print("\t\t\t" + CSVdata[0][signal], " <= ", literal, ";", file=output_vhd_file)
    #print(indent, "wait for ", ns_per_cycle, "ns;", file=output_vhd_file)
  print("", file=output_vhd_file)

# Finish VHDL file
print("\t\twait;", file=output_vhd_file)
print("\tend process;", file=output_vhd_file)
print("", file=output_vhd_file)
print("end stimuli;", file=output_vhd_file)

#close VHDL file
output_vhd_file.close()


# open output_vhi (VHDL instatiation templates) write-only
output_vhi_file = open(output_vhi, 'w')

print("\t----------------------------------------------------------" , file=output_vhi_file)
print("\t-- component declaration for testbench architecture header" , file=output_vhi_file)
print("\t----------------------------------------------------------" , file=output_vhi_file)

print("\tcomponent " + output + " is", file=output_vhi_file)
print("\t\tgeneric ();" , file=output_vhi_file)
print("\t\tport (" , file=output_vhi_file)

# generate port list
for signal in range(1,len(CSVdata[namerow])):
  if int(CSVdata[vwidthrow][signal])!=0:
    lindex = int(CSVdata[lindexrow][signal])
    rindex = int(CSVdata[rindexrow][signal])

    vector_suffix = "_vector("
    if rindex > lindex:
      vector_suffix+= str(lindex) + " to " + str(rindex) + ")"
    else:
      vector_suffix+= str(lindex) + " downto " + str(rindex) + ")"
  else:
    vector_suffix = ""

  print("\t\t\t" + CSVdata[namerow][signal] +" : out std_logic" + vector_suffix + ";", file=output_vhi_file)
print("\t\t\t--" , file=output_vhi_file)
print("\t\t\tsample_enable : in std_logic;" , file=output_vhi_file)
print("\t\t\tsample_clock : in std_logic" , file=output_vhi_file)

print("\t\t);" , file=output_vhi_file)
print("\tend component " + output + ";", file=output_vhi_file)

print("", file=output_vhi_file)
print("\t------------------------------------------------" , file=output_vhi_file)
print("\t-- signal list for testbench architecture header" , file=output_vhi_file)
print("\t------------------------------------------------" , file=output_vhi_file)

# generate signal list
for signal in range(1,len(CSVdata[namerow])):
  if int(CSVdata[vwidthrow][signal])!=0:
    lindex = int(CSVdata[lindexrow][signal])
    rindex = int(CSVdata[rindexrow][signal])

    vector_suffix = "_vector("
    if rindex > lindex:
      vector_suffix+= str(lindex) + " to " + str(rindex) + ")"
    else:
      vector_suffix+= str(lindex) + " downto " + str(rindex) + ")"
  else:
    vector_suffix = ""
  print("\tsignal " + CSVdata[namerow][signal] +" : std_logic" + vector_suffix + ";", file=output_vhi_file)

print("\t--" , file=output_vhi_file)
print("\tsignal sample_enable : std_logic;" , file=output_vhi_file)
print("\tsignal sample_clock : std_logic;" , file=output_vhi_file)

print("", file=output_vhi_file)
print("\t------------------------------------------------" , file=output_vhi_file)
print("\t-- instantiation for testbench architecture body" , file=output_vhi_file)
print("\t------------------------------------------------" , file=output_vhi_file)

# generate instantiation
print("\t" + output + "_inst : " + output, file=output_vhi_file)
print("\t\tport map (", file=output_vhi_file)

for signal in range(1,len(CSVdata[namerow])):
  print("\t\t\t" + CSVdata[namerow][signal] +" => " + CSVdata[namerow][signal] + ",", file=output_vhi_file)
print("\t\t\t--" , file=output_vhi_file)
print("\t\t\tsample_enable => sample_enable," , file=output_vhi_file)
print("\t\t\tsample_clock => sample_clock" , file=output_vhi_file)

print("\t\t);" , file=output_vhi_file)

# close VHI file
output_vhi_file.close()
