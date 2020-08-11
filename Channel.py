from softioc import builder, softioc
import subprocess
from epics import PV

class Channel():
    def __init__(self, chan_name,  wboard, wch, snmpset, monitor_only):
        self.disableSNMPset = monitor_only #Channel on, off, and reset will work.  V and C set commands disabled
        self.chan_name = chan_name
        self.wboard = wboard
        self.wch = wch
        self.cmdtemplate = snmpset
        base_PV = "LV:"+self.chan_name+":"

        # Features of the channels
        self.volt = builder.aOut(base_PV+'SetVoltage', initial_value=0, on_update=self.setVoltage)
        self.curt = builder.aOut(base_PV+'SetCurrent', initial_value=0, on_update=self.setCurrent)
        self.group = builder.aOut(base_PV+'group', initial_value=0) # used to power on/off sets of channels
        self.wboardpv = builder.longIn(base_PV+'wboardpv', initial_value=self.wboard)
        self.wchpv = builder.longIn(base_PV+'wchpv', initial_value=self.wch)
        self.setOn = builder.boolOut(base_PV+'setOn', on_update=self.setOn, HIGH=0.1)
        self.setOff = builder.boolOut(base_PV+'setOff', on_update=self.setOff, HIGH=0.1)
        self.readVol = builder.aIn(base_PV+'SenseVoltage', PREC=1)
        self.readVol.LOPR = 100
        self.readVol.HOPR = 130
        self.readVol.HIHI = 125
        self.readVol.HIGH = 120
        self.readVol.LOW  = 110
        self.readVol.LOLO = 105
        self.readVol.LSV = "MINOR"
        self.readVol.LLSV = "MAJOR"
        self.readVol.HSV = "MINOR"
        self.readVol.HHSV = "MAJOR"
        self.readTem = builder.longIn(base_PV+'Temperature')
        self.imon_read = 0. # measured current from ISEG
        self.imon_adj = 0. # adjustment to the measured current
        self.readCurr = builder.aIn(base_PV+'Current', PREC=3)
        self.status = builder.longIn(base_PV+'status')
        self.setReset = builder.boolOut(base_PV+'setReset', on_update=self.setReset, HIGH=0.1)
        self.channelStatus = builder.stringOut(base_PV+'ChannelStatus',initial_value="")

        if(self.wboard==0):
            self.a = str(self.wch)
        else:
            if(self.wboard !=0 and self.wch > 9):
                self.a = str(self.wboard)+str(self.wch)
            else:
                self.a = str(self.wboard)+'0'+str(self.wch)

    def adjust_measured_current(self):
        self.imon_adj = -1.*self.imon_read

    def put_measured_current(self, imon):
        self.imon_read = imon
        self.readCurr.set( self.imon_read + self.imon_adj )

    def setVoltage(self, val):
        cmd = '{0}outputVoltage.u{1} F {2:.1f}'.format(self.cmdtemplate, self.a, val)
        if self.disableSNMPset: 
            print "setVoltage Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()


    def setCurrent(self, val):
        cmd = '{0}outputCurrent.u{1} F {2:.6f}'.format(self.cmdtemplate, self.a, val*1e-6)
        if self.disableSNMPset: 
            print "setCurrent Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()

    def setOn(self, val):
        if(val==0):return
        cmd = '{0}outputSwitch.u{1} i 1'.format(self.cmdtemplate, self.a)
        if self.disableSNMPset: 
            print "Power On Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()

    def setOff(self, val):
        if(val==0):return
        cmd = '{0}outputSwitch.u{1} i 0'.format(self.cmdtemplate, self.a)
        if self.disableSNMPset: 
            print "Power Off Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()

    def setReset(self, val):
        if(val==0):return
        cmd = '{0}outputSwitch.u{1} i 10'.format(self.cmdtemplate, self.a)
        if self.disableSNMPset: 
            print "Reset Command Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()


