# ----------------------------------------------------------------------
# script functionality
# ----------------------------------------------------------------------
# This script was built to run on an raspberry pi zero
# with DHT22 and 1-wire sensors connected to it.
# It continously reads in the measurable quantities and saves them
# at pre-defined ten minute intervals as a new row in a csv file with
# a UTC timestamp per row.
#
# The script is based on other scripts that highlight
# how DHT22 or 1-wire sensors should be read out and certainly
# needs lots of improvements, USE ONLY AT YOUR OWN RISK.
# ----------------------------------------------------------------------
# setup
# ----------------------------------------------------------------------
# copy to a directory on the raspberry pi zero and adjust the variables
#     pin
#     basepath
#     sensorids
# according to your configuration.

import Adafruit_DHT
import math as math
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
import numpy as np
import os
from pytz import timezone


def readW1Sensor(sensorName):
    f = open(sensorName,'r')
    lines = f.readlines()
    f.close()
    return lines


# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Set basepath to where options and data files are located
basepath = './'

sensor = Adafruit_DHT.DHT22
pin    = 17                       # Adjust to the pin where your DHT22 is connected
floc   = basepath+'/readings.dat'
optloc = basepath+'/options'

# preregistered sensors
# column 1 ... sensor id (in folder /sys/bus/w1/devices)
# column 2 ... column name
# column 3 ... flag whether the sensor was found,
#              initialized as False, later set to
#              true if found in devices folder
#
# In this example there are three wire sensors, two
# for globe temperatures (TG1 and TG2) and an internal
# temperature sensor, measuring the temperature within
# the raspberry zero casing.
#
sensorids = [['28-01205ce5f59c', 'TG1', False], ['28-01205cdf9e85', 'TG2', False], ['28-01205cc2d496', 'Tint', False]]
sensor_n  = 0

# check how many of the preregistered sensors are connected
for ns in range(len(sensorids)):
  sensordir = '/sys/bus/w1/devices/{:s}/w1_slave'.format(sensorids[ns][0])
  print('  checking sensor {:s}'.format(sensorids[ns][0]))
  if os.path.isfile(sensordir):
    sensorids[ns][2] = True
    sensor_n = sensor_n + 1
    print('    >> found')
  else:
    print('    >> not found')

print('  found {:n} preregistered sensors'.format(sensor_n))
print('')

# setup for averaging the dht sensor quantities
T_dht_mean   = 0
RH_dht_mean  = 0
tau_dht_mean = 0

T_dht_min    = 999
T_dht_max    = -999
RH_dht_min   = 999
RH_dht_max   = -999

# -------------------------------------------
# counter - how many values did we measure?
# average that is written to file is later
# calculated as:
# average_value = sum_value / counter_value
# -------------------------------------------
c_T_dht_mean  = 0
c_RH_dht_mean = 0
    
# some setups for averaging the wire-sensor quantities
T_wire_current = np.zeros(len(sensorids))
T_wire_means = np.zeros(len(sensorids))
T_wire_mins  = np.ones(len(sensorids)) * 999
T_wire_maxs  = np.ones(len(sensorids)) * -999
c_wire_means = np.zeros(len(sensorids))


last_save = -1

debug_output = False
debug_data_header = True

while True:

  try:
    opt_fh = open(optloc)
    debug_output_line = opt_fh.readline()
    opt_fh.close()

    debug_output_new = bool(debug_output_line.split('=')[1])

    if debug_output_new != debug_output:
      debug_data_header = True
    else:
      debug_data_header = False
    debug_output = debug_output_new 
  except:
    debug_output = False
    debug_data_header = True

  date_time_obj = datetime.now(tz=timezone('UTC'))
  date_time     = date_time_obj.strftime("%Y-%m-%d %H:%M:%S")

  humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

  for ns in range(len(sensorids)):
    if sensorids[ns][2]:
      sensordir = '/sys/bus/w1/devices/{:s}/w1_slave'.format(sensorids[ns][0])
      if os.path.isfile(sensordir):
        try:
          T = float(str(readW1Sensor(sensordir)).split('t=')[1].replace('\\n\']',''))/1000.
          T_wire_current[ns] = T
          T_wire_means[ns] = T_wire_means[ns] + T
          c_wire_means[ns] = c_wire_means[ns] + 1
          T_wire_mins[ns]  = np.nanmin([T_wire_mins[ns],T])
          T_wire_maxs[ns]  = np.nanmax([T_wire_maxs[ns],T])
        except:
          pass


  if humidity is None:
      humidity = 999
  elif humidity > 150:
      humidity = 999
  if temperature is None:
      temperature = 999
  elif temperature > 100:
      temperature = 999

  if not(humidity == 999):
      K1 = 6.112
      K2 = 17.62
      K3 = 243.12
      tau = K3*((K2*temperature)/(K3+temperature)+math.log(humidity/100.))/((K2*K3)/(K3+temperature)-math.log(humidity/100.))
  else:
      tau = 999

  if not(temperature == 999):  
    T_dht_mean = T_dht_mean + temperature
    T_dht_min  = np.nanmin([temperature,T_dht_min])
    T_dht_max  = np.nanmax([temperature,T_dht_max])
    c_T_dht_mean = c_T_dht_mean + 1
  if not(humidity == 999):
    RH_dht_mean = RH_dht_mean + humidity
    RH_dht_min  = np.nanmin([humidity,RH_dht_min])
    RH_dht_max  = np.nanmax([humidity,RH_dht_max])
    tau_dht_mean = tau_dht_mean + tau
    c_RH_dht_mean = c_RH_dht_mean + 1

  if debug_output:
    varlist = [temperature, humidity, tau]
    varlist = varlist + list(T_wire_current)
    
    if debug_data_header:
      print(' {:19s}   {:5s}{:5s}{:5s}{:5s}{:5s}{:5s}'.format('datetime','T','RH','tau','TG1','TG2','Tint'))
      debug_data_header = False

    debug_str = ' {:s}  '.format(date_time)
    for var in varlist:
      debug_str = debug_str + ' {:2.1f}'.format(var)
    print(debug_str)

  datetime_minutes = date_time_obj.minute
  #datetime_minutes = 10

  if ( (datetime_minutes in [0,10,20,30,40,50]) and (datetime_minutes != last_save) and (np.abs(datetime_minutes - last_save) > 9) ):
    print('  averaging threshold reached at min = {:n}'.format(datetime_minutes))

    line = ''
    # open file and - if it doesn exist, write header line  
    if os.path.isfile(floc):
      fhandle = open(floc,'a+')
    else:
      fhandle = open(floc,'a+')
      line = 'date,T_dht,Tmin_dht,Tmax_dht,RH_dht,RHmin_dht,RHmax_dht,Tau_dht,'
      for ns in range(len(sensorids)):
        line=line+'{:s},{:s},{:s},'.format(sensorids[ns][1],sensorids[ns][1]+'min',sensorids[ns][1]+'max') 
      print('  '+line)
      line=line+'\n'  
      fhandle.write(line)
      

    if c_T_dht_mean == 0:
      T_dht_mean = 999
    else:
      T_dht_mean = T_dht_mean / c_T_dht_mean

    if c_RH_dht_mean == 0:
      RH_dht_mean = 999
      tau_dht_mean = 999
    else:
      RH_dht_mean = RH_dht_mean / c_RH_dht_mean
      tau_dht_mean = tau_dht_mean / c_RH_dht_mean
     
    line = ''
    line = '{:s},{:2.1f},{:2.1f},{:2.1f},{:2.1f},{:2.1f},{:2.1f},{:2.1f}'.format(date_time,T_dht_mean,T_dht_min,T_dht_max,RH_dht_mean,RH_dht_min,RH_dht_max,tau_dht_mean)
    for ns in range(len(sensorids)):
      if c_wire_means[ns] == 0:
        T_wire_means[ns] = 999
      else:
        T_wire_means[ns] = T_wire_means[ns] / c_wire_means[ns]

      line=line+'{:2.1f},{:2.1f},{:2.1f},'.format(T_wire_means[ns],T_wire_mins[ns],T_wire_maxs[ns]) 
    print('  '+line)
    line=line+'\n'
    fhandle.write(line)

    fhandle.flush()
    fhandle.close()

    last_save = datetime_minutes
    #last_save = date_time_obj.minute

    # reset all averages and counts
    c_T_dht_mean = 0
    c_RH_dht_mean = 0
    c_wire_means = c_wire_means*0
    T_dht_mean = 0
    RH_dht_mean = 0
    T_wire_means = T_wire_means * 0
