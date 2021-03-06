#!/usr/bin/python
"""
get feed back from grbl and the cnc_pcb_height_probe to map 
the height of the pcb
"""
import serial
import time
import numpy

import commands
import re
import sys
import math

grbl_dev = "/dev/ttyUSB0"
grbl_baud = 9600
grbl_serial = serial.Serial(grbl_dev, grbl_baud)

probe_cmd = " ./probe read | grep continuity"

# everything in mm

z_max = 0.1
z_min = -1.0
z_del = 0.01

# from observation, 0.25 max to min.  0.15 headroom should be plenty 
#   vvvvv-----------NOT ANYMORE!
#   it's also dynamic, so it's going to increase as it scans out
#   the work
z_headroom = 0.15  

cur_z_start = z_max
observed_z_max = z_min
#z_tic = int( round( ((z_max - z_min) / z_del) + 0.5 ) )

x_min = 0.0
#x_max = 80.0
#x_max = 100.0
#x_tic = 20 + 1
x_max = 50.0
x_tic = 10 + 1
#x_max = 55.0
#x_tic = 11 + 1

y_min = 0.0
#y_max = 40.0
y_max = 60.0
y_tic = 12 + 1

verbose = 0

def probe_continuity( ):
  (ret, res) = commands.getstatusoutput( probe_cmd )
  if ( re.search('continuity: yes', res) ):
    return 1
  elif ( re.search('continuity: no', res) ):
    return 0
  sys.exit( probe_cmd + " error (" + str(ret) + ")" )


def send_grbl_command( cmd ) :
  if verbose:
    print "# sending '" + cmd + "'"
  grbl_serial.write(cmd + "\n")
  grbl_out = grbl_serial.readline()
  if verbose:
    print "#  got :", grbl_out.strip()
  while ( not re.search("ok", grbl_out) ):
    if verbose:
      print "#  got :", grbl_out.strip()
    grbl_out = grbl_serial.readline()
  if verbose:
    print "#", grbl_out

def get_grbl_var_position( var_name ):
  var_seen = 0
  var_pos = 0.0
  #grbl_serial.write("$?\n")
  grbl_serial.write("?")
  grbl_out = grbl_serial.readline()

  if verbose:
    print "#  get_grbl_var_position(", var_name, "): got :", grbl_out.strip()

  m = re.search( "^<([^,]*),MPos:([^,]*),([^,]*),([^,]*),", grbl_out)
  if ( m ):
    if verbose:
      print "# matched", m.group(0)
    state = m.group(1)
    x = float(m.group(2))
    y = float(m.group(3))
    z = float(m.group(4))

    if ( var_name == 'x') or ( var_name == 'X'):
      return x
    if ( var_name == 'y') or ( var_name == 'Y'):
      return y
    if ( var_name == 'z') or ( var_name == 'Z'):
      return z

def wait_for_var_position( var_name, var_val ):
  sleepy = 0.05
  var_epsilon = 0.001
  cur_val = get_grbl_var_position( var_name )
  if verbose:
    print "#", str(var_val), " var_epsilon", str(x_epsilon), "cur_x", str(cur_val)
  while (math.fabs(var_val - cur_val) > var_epsilon):
    if verbose:
      print "# cur_val", str(cur_val), ", waiting for ", var_name, str(var_val)
    time.sleep(sleepy)
    cur_val = get_grbl_var_position( var_name )

send_grbl_command( "" )
send_grbl_command( "" )
send_grbl_command( "g90" )
send_grbl_command( "g21" )

send_grbl_command( "g1z" + str(z_max) )
send_grbl_command( "g0 x" + str(x_min) + " y" + str(y_min) )

send_grbl_command( "$" )
send_grbl_command( "$?" )

if verbose:
  print "# grbl setup done\n"
  print "probe continuity: ", str(probe_continuity())
  print "setup done\n"

get_grbl_var_position( "Z" )

height = {}

even_odd = 0

for x in numpy.linspace(x_min, x_max, x_tic):
  y_start = y_min
  y_end = y_max

  if (even_odd == 1):
    y_start = y_max
    y_end = y_min

  even_odd = 1-even_odd

#  for y in numpy.linspace(y_min, y_max, y_tic):
  for y in numpy.linspace(y_start, y_end, y_tic):
    #time.sleep(.1)
    time.sleep(.05)
    if verbose:
      print "# starting probe for x", x, "y", y, "(z", z_max, ")"
    send_grbl_command( "g1z" + str(z_max) )
    send_grbl_command( "g0 x" + str(x) + " y" + str(y) )

    wait_for_var_position("X", x)
    wait_for_var_position("Y", y)
    wait_for_var_position("Z", z_max)

    z_tic = int( round( ((z_max - z_min) / z_del) + 0.5 ) )
    #z_tic = int( round( ((cur_z_start - z_min) / z_del) + 0.5 ) )

    for z in numpy.linspace(z_max, z_min, z_tic):
      if verbose:
        print "#  positioning z", z
      send_grbl_command( "g1z"+str(z) )


      if verbose:
        print "# waiting for z", str(z)
      wait_for_var_position("Z", z)
      c = probe_continuity()
      if verbose:
        print "# got c ", str(c)
      if ( probe_continuity() ):
        if verbose:
          print "# yep!\n"
        break;
      else:
        if verbose:
          print "# nope\n"
        pass

    if (z <= z_min):
      sys.exit("ERROR: z_min (" + str(z_min) + ") reached")

    observed_z_max  = max(z, observed_z_max)
    cur_z_start     = min(z_max, observed_z_max + z_headroom)

    print str(x), str(y), str(z)
    sys.stdout.flush()

    height[ str(x) + "," + str(y) ] = z

#for xy in height:
#  print "xy", xy, ", ", height[xy]

send_grbl_command( "g1z" + str(z_max) )
send_grbl_command( "g0x0y0" )




