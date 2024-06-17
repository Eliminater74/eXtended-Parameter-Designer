# -*- coding: utf-8 -*-
# Basic Infineon-style e-bike controller class
#

import os
import gtk
import ctypes
import math
import serial
from fnmatch import fnmatch
from xpdm import FNENC

# Parameter widget types for editing
PWT_COMBOBOX = 0
PWT_SPINBUTTON = 1
PWT_CHECKBOX = 2

# Capabilities bitflags
CAP_DOWNLOAD = 1

# A list of controller families
Families = []

def log2(x):
    n = 0
    while (1 << n) < x:
        n += 1
    return n

class ControllerFamily:
    def __init__(self, Family, ProfileClass, DetectFormat, Capabilities, ModelDesc):
        def CreateProfile(FileName):
            return ProfileClass(Family, FileName)

        self.Family = Family
        self.CreateProfile = CreateProfile
        self.ModelDesc = ModelDesc
        self.DetectFormat = DetectFormat
        self.Capabilities = Capabilities

def RegisterFamily(Family, ProfileClass, DetectFormat, Capabilities, ModelDesc):
    Families.append(ControllerFamily(Family, ProfileClass, DetectFormat, Capabilities, ModelDesc))

class Profile:
    Family = None
    FileName = None
    Description = None

    # Parameter order when loading from .asv files
    ParamLoadOrder = []

    # The order of parameters in the profile edit dialog
    ParamEditOrder = []

    # The order of parameters in raw binary data sent to controller
    ParamRawOrder = []

    def __init__(self, Family, FileName, ControllerModelDesc, ControllerParameters):
        self.ControllerModelDesc = ControllerModelDesc
        self.ControllerParameters = ControllerParameters
        self.SetFileName(FileName)
        self.Family = Family
        for parm, desc in self.ControllerParameters.items():
            if "Default" in desc:
                setattr(self, parm, desc["Default"])

    def __setattr__(self, attr, val):
        if "ControllerParameters" in self.__dict__:
            if attr in self.ControllerParameters:
                parmdesc = self.ControllerParameters[attr]
                if "BitField" in parmdesc:
                    if parmdesc["BitField"] in self.__dict__:
                        self.__dict__[parmdesc["BitField"]] = \
                            (self.__dict__[parmdesc["BitField"]] & ~parmdesc["BitMask"]) | \
                            ((val << parmdesc["BitShift"]) & parmdesc["BitMask"])
                    else:
                        self.__dict__[parmdesc["BitField"]] = \
                            (val << parmdesc["BitShift"]) & parmdesc["BitMask"]
                    return

        self.__dict__[attr] = val

    def __getattr__(self, attr):
        if "ControllerParameters" in self.__dict__:
            if attr in self.ControllerParameters:
                parmdesc = self.ControllerParameters[attr]
                if "BitField" in parmdesc:
                    return (self.__dict__[parmdesc["BitField"]] & parmdesc["BitMask"]) >> \
                        parmdesc["BitShift"]

        raise AttributeError("%r object has no attribute %r" % (self.__class__, attr))

    def SetFileName(self, fn, rename=True):
        sext = os.path.splitext(os.path.basename(fn))
        if sext[1].lower() != ".asv":
            fn = "%s.asv" % fn
            sext = os.path.splitext(os.path.basename(fn))
        self.Description = sext[0]

        fn = fn.encode(FNENC)

        if rename:
            # If file with old name exists, rename it
            if (self.FileName != None) and os.access(self.FileName, os.R_OK):
                os.rename(self.FileName, fn)

        self.FileName = fn

    def SetDescription(self, desc):
        self.SetFileName(os.path.join(
            os.path.dirname(self.FileName).decode(FNENC), desc + ".asv"))

    def Load(self, fn, lines):
        vi = 0
        for l in lines:
            # Remove extra characters from the string
            l = l.strip()
            try:
                l = l[:l.index(":")]
            except ValueError:
                pass

            if vi >= len(self.ParamLoadOrder):
                if len(l):
                    raise ValueError(_("Extra data at the end of file:\n'%(data)s'") % {"data": l})
            else:
                parm = self.ParamLoadOrder[vi]
                if type(parm) != int:
                    desc = self.ControllerParameters[parm]
                    if 'i' in desc["Type"]:
                        setattr(self, parm, int(l))
                    elif 'f' in desc["Type"]:
                        setattr(self, parm, float(l))

            vi = vi + 1

    def Save(self):
        lines = []
        for parm in self.ParamLoadOrder:
            if type(parm) == int:
                lines.append("%d" % parm)
            else:
                desc = self.ControllerParameters[parm]
                if 'i' in desc["Type"]:
                    # Hack for controller model
                    if '/' in desc["Type"]:
                        model = self.GetModel()
                        if '/' in model:
                            model = model[:model.find('/')]
                        lines.append("%d:%s" % (getattr(self, parm), model))
                    else:
                        lines.append("%d" % getattr(self, parm))
                elif 'f' in desc["Type"]:
                    mask = "%%.%df" % desc.get("Precision", 1)
                    lines.append(mask % getattr(self, parm))

            # Append a CR since the file uses windows line endings
            lines[-1] += '\r'

        with open(self.FileName, "wb") as f:
            f.write(('\n'.join(lines) + '\n').encode('utf-8'))

    def GetController(self):
        if (self.ControllerModel > 0) and (self.ControllerModel <= len(self.ControllerModelDesc)):
            return self.ControllerModelDesc[self.ControllerModel - 1]

        return self.ControllerModelDesc[0]

    def GetModel(self):
        if (self.ControllerModel > 0) and (self.ControllerModel <= len(self.ControllerModelDesc)):
            return self.ControllerModelDesc[self.ControllerModel - 1]["Name"]

        return "???"

    def Remove(self):
        if self.FileName:
            os.remove(self.FileName)

    def FillParameters(self, vbox):
        rowcidx = 0
        rowcolors = [gtk.gdk.Color(1.0, 1.0, 1.0), gtk.gdk.Color(1.0, 0.94, 0.86)]

        self.EditWidgets = {}

        for parm in self.ParamEditOrder:
            if type(parm) == list:
                if len(parm) > 0:
                    expd = gtk.Expander(parm[0])
                    expd.set_expanded(True)
                    expd.set_border_width(1)
                    expd.set_spacing(3)
                    expd_vbox = gtk.VBox(False, 1)
                    expd.add(expd_vbox)
                    vbox.pack_start(expd, False, True, 0)
                else:
                    expd_vbox = gtk.VBox(False, 1)
                    vbox.pack_start(expd_vbox, False, True, 0)
                continue

            desc = self.ControllerParameters[parm]

            # Place the hbox in a event box to be able to change background color
            evbox = gtk.EventBox()
            hbox = gtk.HBox(False, 5)
            hbox.set_border_width(2)
            evbox.add(hbox)
            evbox.set_tooltip_text(desc["Description"])
            expd_vbox.pack_start(evbox, False, True, 0)

            label = gtk.Label(desc["Name"])
            label.set_alignment(0.0, 0.5)

            evbox.modify_bg(gtk.STATE_NORMAL, rowcolors[rowcidx])
            rowcidx ^= 1
            hbox.pack_start(label, True, True, 0)

            if desc["Widget"] == PWT_COMBOBOX:
                minv, maxv = desc["Range"]
                cb = gtk.combo_box_new_text()
                for i in range(minv, maxv + 1):
                    cb.append_text(desc["GetDisplay"](self, i))
                cb.set_active(getattr(self, parm) - minv)
                hbox.pack_start(cb, False, True, 0)
                cb.connect("changed", self.ComboBoxChangeValue, parm, desc)
                self.EditWidgets[parm] = cb

            elif desc["Widget"] == PWT_SPINBUTTON:
                minv, maxv = desc["Range"]
                spin = gtk.SpinButton(climb_rate=1.0)
                try:
                    val = desc["SetDisplay"](self, getattr(self, parm))
                except IndexError:
                    val = desc["Default"]
                spin.get_adjustment().configure(val, minv, maxv, 1, 5, 0)
                spin.set_width_chars(7)
                hbox.pack_start(spin, False, True, 0)
                spin.connect("output", self.SpinButtonOutput, parm, desc)
                spin.connect("input", self.SpinButtonInput, parm, desc)
                spin.connect("value-changed", self.SpinButtonValueChanged, parm, desc)
                self.EditWidgets[parm] = spin

            elif desc["Widget"] == PWT_CHECKBOX:
                cbut = gtk.CheckButton()
                cbut.set_active(getattr(self, parm))
                hbox.pack_start(cbut, False, True, 0)
                cbut.connect("toggled", self.CheckButToggled, parm, desc)
                self.EditWidgets[parm] = cbut

        vbox.show_all()

    def ComboBoxChangeValue(self, cb, parm, desc):
        minv, maxv = desc["Range"]
        setattr(self, parm, minv + cb.get_active())
        # Check if any depending controls needs updating
        for iparm, idesc in self.ControllerParameters.items():
            if "Depends" in idesc:
                if parm in idesc["Depends"]:
                    self.EditWidgets[iparm].update()

    def SpinButtonOutput(self, spin, parm, desc):
        desc = self.ControllerParameters[parm]
        if desc.get("Units") is None:
            mask = "%%.%df" % desc.get("Precision", 1)
        else:
            mask = "%%.%df %s" % (desc.get("Precision", 1), desc.get("Units", "").replace('%', '%%'))
        spin.set_text(mask % desc["GetDisplay"](self, spin.props.adjustment.value))
        return True

    # gptr hack, see http://www.mail-archive.com/pygtk@daa.com.au/msg16384.html
    def SpinButtonInput(self, spin, gptr, parm, desc):
        text = spin.get_text().strip()
        if "Units" in desc:
            try:
                text = text[:text.rindex(desc["Units"])]
            except ValueError:
                pass
        try:
            val = float(desc["SetDisplay"](self, float(text.strip())))
        except ValueError:
            val = spin.props.adjustment.value

        double = ctypes.c_double.from_address(hash(gptr))
        double.value = val
        return True

    # don't allow the displayed value to go below zero
    def SpinButtonValueChanged(self, spin, parm, desc):
        while desc["GetDisplay"](self, spin.props.adjustment.value) < 0:
            spin.props.adjustment.value += 1
        val = desc["GetDisplay"](self, spin.props.adjustment.value)
        prec = desc.get("Precision", 1)
        val = round(val * math.pow(10, prec)) / math.pow(10, prec)
        setattr(self, parm, val)

    def CheckButToggled(self, cbut, parm, desc):
        val = cbut.get_active()
        if val:
            val = 1
        else:
            val = 0
        setattr(self, parm, val)

    def BuildRaw(self):
        data = bytearray()

        for x in self.ParamRawOrder:
            if type(x) == str:
                if "ToRaw" in self.ControllerParameters[x]:
                    x = self.ControllerParameters[x]["ToRaw"](self, getattr(self, x))
                elif self.ControllerParameters[x]["Widget"] == PWT_COMBOBOX:
                    x = round(getattr(self, x))
                elif self.ControllerParameters[x]["Widget"] == PWT_SPINBUTTON:
                    x = self.ControllerParameters[x]["SetDisplay"](self, getattr(self, x))

            data.append(int(x))

        # temporary hack until someone finds out what means the 23rd byte
        if "Byte23" in self.ControllerModelDesc[self.ControllerModel - 1]:
            data[23] = self.ControllerModelDesc[self.ControllerModel - 1]["Byte23"]

        crc = 0
        for x in data:
            crc = crc ^ x
        data.append(crc)

        return data

    def LoadRaw(self, data, name_wildcard):
        data_len = len(self.ParamRawOrder) + 1
        if len(data) > data_len:
            # ignore trailing garbage
            del data[data_len:]

        crc = 0
        for x in data:
            crc = crc ^ x
        if crc != 0:
            raise ValueError(_("Broken data received (wrong family?)"))

        # first of all, determine controller model
        x = data[self.ParamRawOrder.index("ControllerModel")]
        for n in range(len(self.ControllerModelDesc)):
            y = self.ControllerModelDesc[n]
            if (y["ControllerModel"] == x) and \
                ((name_wildcard is None) or (fnmatch(y["Name"], name_wildcard))):
                setattr(self, "ControllerModel", n + 1)
                break

        if getattr(self, "ControllerModel", None) is None:
            return False

        idx = 0
        for x in self.ParamRawOrder:
            if (type(x) == str) and (x != "ControllerModel"):
                p = data[idx]
                if "FromRaw" in self.ControllerParameters[x]:
                        p = self.ControllerParameters[x]["FromRaw"](self, p)
                elif self.ControllerParameters[x]["Widget"] == PWT_SPINBUTTON:
                    p = self.ControllerParameters[x]["GetDisplay"](self, p)
                setattr(self, x, p)

            idx += 1

        return True

    def CopyParameters(self, other):
        for parm in self.ControllerParameters.keys():
            if hasattr(other, parm):
                val = getattr(other, parm)
                rng = self.ControllerParameters[parm].get("Range", (0, 1))
                if val < rng[0]:
                    val = rng[0]
                if val > rng[1]:
                    val = rng[1]
                setattr(self, parm, val)

    def OpenSerial_EB3xx_KH6xx(self, com_port):
        try:
            return serial.Serial(com_port, 38400, serial.EIGHTBITS, serial.PARITY_NONE,
                serial.STOPBITS_TWO, timeout=0.2)
        except serial.SerialException as e:
            raise serial.SerialException(str(e).encode(locale.getpreferredencoding()))

    # Common code for EB3xx and KH6xx
    def Upload_EB3xx_KH6xx(self, com_port, progress_func):
        data = self.BuildRaw()
        ser = self.OpenSerial(com_port)

        progress_func(msg=_("Waiting for controller ready"))
        # Send '8's and wait for the 'U' response
        skip_write = False
        while True:
            if not skip_write:
                # Garbage often comes from the controller upon bootup, just ignore it
                ser.flushInput()
                ser.write(b'8')
            skip_write = False

            c = ser.read()
            if c == b'U':
                break

            if len(c) > 0:
                skip_write = True

            if not progress_func():
                return False

        progress_func(msg=_("Waiting acknowledgement"))

        ser.flushInput()
        ser.write(bytes(data))
        ack = b"QR"
        for i in range(10):
            c = ser.read()
            while len(c) and (c[0] == ack[0]):
                c = c[1:]
                ack = ack[1:]
                if len(ack) == 0:
                    return True

            if len(c) > 0:
                if c[0] == 0xa1:
                    raise Exception(_("Controller says data is short (wrong family?)"))
                elif c[0] == 0xa2:
                    raise Exception(_("Controller says received data is broken"))
                raise Exception(_("Invalid reply byte '%(chr)02x'") % {"chr": ord(c[0])})

            if not progress_func():
                break

        raise Exception(_("Controller does not acknowledge data"))

    def Download_EB3xx_KH6xx(self, com_port, progress_func, name_wildcard):
        data_len = len(self.ParamRawOrder) + 1

        ser = self.OpenSerial(com_port)

        progress_func(msg=_("Waiting for controller ready"))
        # Send 'U' and wait for response
        data = bytearray()
        query = False
        while True:
            if query and len(data) == 0:
                ser.flushInput()
                ser.write(b'U')
                query = False

            c = ser.read()
            if len(c) == 0:
                if len(data) >= data_len:
                    break
                query = True
                del data[:]
                if not progress_func():
                    return False
            else:
                for i in range(len(c)):
                    data.append(ord(c[i]))
                if not progress_func(pos=(float(len(data)) / data_len)):
                    return False
                # just in case
                if len(data) >= 1024:
                    break

        return self.LoadRaw(data, name_wildcard)
