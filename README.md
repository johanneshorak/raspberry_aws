----------------------------------------------------------------------
script functionality
----------------------------------------------------------------------
This script was built to run on an raspberry pi zero
with DHT22 and 1-wire sensors connected to it.
It continously reads in the measurable quantities and saves them
at pre-defined ten minute intervals as a new row in a csv file with
a UTC timestamp per row.

The script is based on other scripts that highlight
how DHT22 or 1-wire sensors should be read out and certainly
needs lots of improvements, USE ONLY AT YOUR OWN RISK.

----------------------------------------------------------------------
setup
----------------------------------------------------------------------
copy to a directory on the raspberry pi zero and adjust the variables
    pin
    basepath
    sensorids
according to your configuration.
