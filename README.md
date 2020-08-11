# wiener-crate-pyepics
Python-based EPICS driver for Wiener voltage supply crate

Implimented using python-based EPICS.
/usr/local/epics/modules/pythonIoc/pythonIoc should be installed along with the standard EPICS libraries.

Start the ioc with ./main.py
Most parameters of the IOC can be configured within main.py including the number of channels in each card, ip address, and community names.

Launch the CaQtDM control screen with ./display.

Please install the current WIENER-CRATE-MIB.txt from Wiener:  https://file.wiener-d.com/software/net-snmp/

Paul Nord,
Valparaiso University

Based on earlier work by members of the STAR collaboration.
