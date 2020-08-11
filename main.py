#!/usr/local/epics/modules/pythonIoc/pythonIoc

#import basic softioc framework
from softioc import softioc, builder

#import the the application
devicename = 'CRATE'
builder.SetDeviceName(devicename)

from wiener_crate import wiener_crate

#load the voltage control systems
ip_address = '192.168.1.200'          #configure to match local network settings
voltage_config = "voltage_supply.csv"
#    name,board,channel,voltage,current,rampup,rampdown,group
#    u0,0,0,5,1,20,20,0
#    ...
chan = [8,8,8,8,8]                  #number of channels in each slot
comm = ["public","private","admin"]  #community names, default values work with factory configuration

power_crate = wiener_crate(ip_address,voltage_config,channels=chan, community=comm)

#run the ioc
builder.LoadDatabase()
softioc.iocInit()

power_crate.do_startthread()


#start the ioc shell
softioc.interactive_ioc(globals())
