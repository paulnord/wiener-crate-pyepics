import pandas as pd
import xml.etree.ElementTree as ET


def main():

    PV_LIST = []

    for board in range(0,5):
        for chan in range (0,8):
            for i in range(0,16):
                PV_LIST.append("u"+str(100*board+chan))

    #print(PV_LIST)
    
    #open template file which is in xml format
    tree = ET.parse("voltage_display_template.ui")
    root = tree.getroot()

    #scan through the file taking an entry from the PV list and replacing it in the matching text of the template file
    i = 0
    items = tree.findall(".//string")
    label_count = files_count = args_count = 0
    for item in items:
              print(item,i)
              try:
                if "XYZZY" in item.text:
                  item.text = item.text.replace("XYZZY",PV_LIST[i])
                  print(item.text)
                  i += 1
              except:
                print("strange error")

    #write out the new file
    new_file = open("VoltageControls.ui","w")
    data = ET.tostring(root)
    new_file.write(data)
    new_file.close()

main()
