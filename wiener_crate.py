import time
import pandas as pd
import threading
from datetime import datetime

from Channel import Channel
from softioc import builder, softioc, alarm
import subprocess

class wiener_crate():
    def __init__(self, ip, config_file, channels=[8,8,8,8,8], community=["public","private","admin"]):
        # Control Buttons
        self.board_channels = channels
        self.disableSNMPset = True  # If operating EPICS as monitor only, this will prevent setting voltages,  Power On/Off will work
        self.readData = builder.boolOut('LV:readData', on_update=self.place_voltages, HIGH=0.1)
        self.mainOn = builder.aOut('LV:mainOn', on_update=self.turnMainOn, HIGH=0.1)
        self.mainOff = builder.aOut('LV:mainOff', on_update=self.turnMainOff, HIGH=0.1)
        self.on = builder.aOut('LV:on', on_update=self.turnOn, HIGH=0.1)
        self.off = builder.aOut('LV:off', on_update=self.turnOff, HIGH=0.1)
        self.setV = builder.aOut("LV:setVals", on_update=self.setVals)
        #self.write_voltages_pv = builder.boolOut("LV:write_voltages", on_update=self.write_voltages, HIGH=0.1)
        self.marker = builder.longIn('LV:marker')

        self.config_file = config_file
        self.reset = builder.boolOut("LV:reset", on_update=self.Reset, HIGH=0.1)
        self.adj_current_pv = builder.boolOut("LV:adj_current", on_update=self.adj_current, HIGH=0.1)
        self.adj_msg = "Last done: "
        self.adj_stat_pv = builder.stringIn("LV:adj_stat", initial_value=self.adj_msg+"none")

        self.chlist = []
        self.ip = ip
        self.dictWiener, self.dictCrate = {}, {}

        #snmp 5.8 for user defined precision in current readings, compiled according to
        # http://file.wiener-d.com/software/net-snmp/net-snmp-CompileForExtendedPrecision-2015-03-06.txt
        #self.snmpwalk = "/usr/local/Net-SNMP_5-8/code/apps/snmpwalk"
        #self.snmpwalk = "/usr/bin/snmpwalk"
        self.snmpwalk ="/home/stgc/pnord/net-snmp-5.8/apps/snmpwalk -v 2c -c "+ community[0] + " " + self.ip + " WIENER-CRATE-MIB::"
        self.snmpset = "/home/stgc/pnord/net-snmp-5.8/apps/snmpset  -v 2c -c "+ community[1] + " " + self.ip + " WIENER-CRATE-MIB::"

        #create PV's for all channels, add them to channel list and dictionary
        board = 0
        for self.i in self.board_channels: # board
            for self.j in xrange(self.i): # channel
                name = "u"+str(100*board+self.j)
                self.chlist.append(Channel(name, board, self.j, self.snmpset, self.disableSNMPset))
                self.dictWiener[(board,self.j)] = self.chlist[-1]
                self.dictCrate[(name)] = self.chlist[-1]
            board += 1
        print "Before start, you have to Load Voltage from file through Load Voltage button "
        print "Voltages settings will load from " + self.config_file
        if self.disableSNMPset:
            print "EPICS task setup in monitor-only mode.  No voltage or current set commands will run."

    def getValue(self, cm):
            #print("Get value: ", cm)
            p = subprocess.Popen(cm.split(), stdout=subprocess.PIPE)
            out = p.communicate()
            a = out[0].split("\n")
            #print(a)
            l1, l2, l3 = [], [], []
            for i in range(0,len(a)-1):
                b = a[i].split('.u')
                c = b[1].split()
                if( len( c[0] ) == 1):
                    iboard=0
                    ich = int(c[0])
                elif( len( c[0] ) == 2):
                    iboard=0
                    ich=int(c[0])
                else:
                    iboard = int(c[0][0])
                    ich = int(c[0][1:])
                #if iboard >2: continue # we use only boards 0, 1, 2
                if ich >=8: continue # we use only 8 channel boards
                l1.append(iboard)
                l2.append(ich)
                l3.append(float(c[4]))
            return l1,l2,l3

    def do_runreading(self):
        while True:
            time.sleep(5) # default was 2 sec
            cmd_base = self.snmpwalk 
            cmdV = cmd_base + "outputMeasurementSenseVoltage"
            cmdI = cmd_base + "outputMeasurementCurrent -Op .9"
            cmdS = cmd_base + "outputStatus"
            cmdT = cmd_base + "outputMeasurementTemperature"
            try: 
                eV, fV, gV = self.getValue(cmdV)
                eI, fI, gI = self.getValue(cmdI)
            except IndexError:
                print "Wiener crate not responding"
                self.set_invalid()
                continue

            if len(eV) == 0:
                print "Empty response from Wiener crate"
                self.set_invalid()
                continue

            p = subprocess.Popen(cmdS.split(), stdout=subprocess.PIPE)
            out = p.communicate()
            a = out[0].split('\n')

            pT = subprocess.Popen(cmdT.split(), stdout=subprocess.PIPE)
            outT = pT.communicate()
            aT = outT[0].split('\n') 

            sumV, sumT = 0, 0
            sumVi, sumVo = 0, 0
            Ni, No = 0, 0
            for j in range(len(eV)):
                ll = 99
                try:
                    self.dictWiener[ (eV[j], fV[j]) ].readVol.set( gV[j]*(-1) )
                    self.dictWiener[ (eI[j], fI[j]) ].put_measured_current( gI[j]*1e6 )
                    self.dictWiener[ (eI[j], fI[j]) ].readTem.set(int( aT[j].split()[-2] ))
                except:
                    print "Invalid value from Wiener response"
                    print(j,eV[j],fV[j],eI[j],fI[j])
                    print(gV[j],gI[j],int( aT[j].split()[-2] ))
                    self.set_invalid()
                    continue

                sumV = sumV + self.dictWiener[(eV[j], fV[j])].readVol.get()
                sumT = sumT + self.dictWiener[(eV[j], fV[j])].readTem.get()
                if('00 01' in a[j]):
                    ll=0 # OFF
                #if('80 11 80' in a[j] or '80 01' in a[j] or '80 11' in a[j] or '80 21' in a[j]):
                if('80 11 80' in a[j] or '80 21' in a[j] or '80 01 outputOn(0)' in a[j]):
                #if('80 11 80' in a[j]):
                    ll=2 # RAMP UP
                    if( self.dictWiener[ (eV[j], fV[j]) ].readVol.get() > self.dictWiener[ (eV[j], fV[j]) ].volt.get() ):
                        ll=3
                if('80 09 80' in a[j]):
                    ll=3 # RAMP DOWN
                if('80 01 80' in a[j]):
                    ll=1 # ON
                if('04 01' in a[j]):
                    ll=4 # TRIP
                self.dictWiener[ (eI[j], fI[j]) ].status.set(ll)
                myStatus = a[j].split("BITS: ")
                self.dictWiener[ (eI[j], fI[j]) ].channelStatus.set(str(myStatus[1][:20]))

                #report unrecognized status to ioc shell
                if ll > 10:
                    print "Unrecognized channel status:", ll, j, a[j]


    def do_startthread(self):
        t = threading.Thread(target=self.do_runreading)
        t.daemon = True
        t.start()

    def set_invalid(self):
        for ch in self.chlist:
            ch.readVol.set_alarm(alarm.INVALID_ALARM, alarm=alarm.UDF_ALARM)
            ch.readTem.set_alarm(alarm.INVALID_ALARM, alarm=alarm.UDF_ALARM)
            ch.readCurr.set_alarm(alarm.INVALID_ALARM, alarm=alarm.UDF_ALARM)
            ch.status.set_alarm(alarm.INVALID_ALARM, alarm=alarm.UDF_ALARM)

        self.marker.set_alarm(alarm.INVALID_ALARM, alarm=alarm.UDF_ALARM)

    # place_voltages() will read the csv configuration file, send voltages and current limits on crate
    def place_voltages(self, val):
        if val == 0: return
        f = pd.read_csv(self.config_file)
        for line in range(len(f)):
            channel_name = f['name'][line]
            voltage = f['voltage'][line]
            current = f['current'][line]
            group = f['group'][line]
            self.dictCrate[(channel_name)].volt.set(voltage)  # These two commands will set voltages on snmp device
            self.dictCrate[(channel_name)].curt.set(current)  # -- question from PMN, do we want this to happen on initialization?
            self.dictCrate[(channel_name)].group.set(group)

    #def write_voltages(self, val):
    #    if val == 0: return
    #    f = pd.read_csv(self.config_file)
    #    for i in xrange(len(f)):
    #        ch = f['name'][i]
    #        volt = self.dictCrate[(sec, ch)].volt.get()
    #        curr = self.dictCrate[(sec, ch)].curr.get()
    #        f['voltage'][i] = volt
    #        f['current'][i] = curr
    #    f.to_csv(self.config_file, index=False)

    def turnMainOn(self, val):
        #print("turnMainOn called",val)
        if val < 0: return
        cmd = self.snmpset + ' sysMainSwitch.0 i 1'
        if self.disableSNMPset:
            print "Power On Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()

        self.mainOn.set(-1)

    def turnMainOff(self, val):
        #print("turnMainOff called",val)
        if val < 0: return
        cmd = self.snmpset + ' sysMainSwitch.0 i 0'
        if self.disableSNMPset:
            print "Power Off Disabled  :  " + cmd
            return
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        out = p.communicate()

        self.mainOff.set(-1)

    def turnOn(self, val):
        #print("turnOn called",val)
        self.marker.set(1)
        if val < 0: return
        for obj in self.chlist:
            if(val == obj.group.get()):
                obj.setOn.set(1)
        self.on.set(-1)

    def turnOff(self, val):
        #print("turnOff called",val)
        self.marker.set(2)
        if val < 0: return
        for obj in self.chlist:
            if(val == obj.group.get()):
                obj.setOff.set(1)
        self.off.set(-1)

    def setVals(self, val):
        #print("setVolt called",val)
        if val <= 0: return
        try:
            for ch in self.chlist:
                current = ch.curt.get()
                ch.setCurrent(current)
                voltage = ch.volt.get()
                ch.setVoltage(voltage)
        except:
            print("hmmm")

        self.setV.set(0)

    def Reset(self, val):
        print("reset called",val)
        if(val==0):return
        for obj in self.chlist:
            if(obj.status.get()==4):
                print "RESET: sector {0}, channel{1}".format(obj.sect_num, obj.chann_num)
                obj.setReset.set(1)

    def adj_current(self, val):
        if val == 0: return
        self.adj_stat_pv.set("Wait calib in progress")
        for ch in self.chlist:
            ch.adjust_measured_current()

        self.adj_stat_pv.set(self.adj_msg + datetime.now().strftime("%Y-%m-%d %H:%M"))




