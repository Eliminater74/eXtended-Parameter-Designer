# -*- coding: utf-8 -*-
# Infineon-style e-bike controller profile
# Support for EB2xx family
#

import serial
import locale
from xpdm import infineon

# -- # Constants # -- #

# Motor sensor angle
SA_120 = 0
SA_60 = 1
SA_COMPAT = 2

SensorAngleDesc = ["120°", "60°", _("Auto")]

# Three-speed switch modes
SSM_SWITCH = 0
SSM_CYCLE = 1

SpeedSwitchModeDesc = [_("Switch"), _("Cycle")]

# LED indicator mode
IM_COMM_VCC = 0
IM_COMM_GND = 1
# "164 Mode P1-DAT P2-CLK"
IM_164 = 2

IndicatorModeDesc = [_("Common VCC"), _("Common GND"), _("164 Mode P1-DAT P2-CLK")]

# Slip charge mode
SCM_ENABLE = 0
SCM_DISABLE = 1

SlipChargeModeDesc = [_("Enable"), _("Disable")]

# EBS level
EBS_DISABLED = 0
EBS_MODERATE = 1
EBS_STRONG = 2

EBSLevelDesc = [_("Disabled"), _("Moderate"), _("Strong"), _("Unlimited")]
EBSLevel2Raw = [0, 4, 8, 255]

# Guard mode signal polarity (anti-theft)
GP_LOW = 0
GP_HIGH = 1

GuardLevelDesc = [_("Low"), _("High")]

# Throttle blowout protect
TBP_DISABLE = 0
TBP_ENABLE = 1

ThrottleProtectDesc = [_("Disabled"), _("Enabled")]

# Pedal Assisted Sensor mode
PAS_LONG = 0
PAS_SHORT = 1

PASModeDesc = [_("Long (~3s)"), _("Short (~1s)")]

# P3 LED indicator mode
P3M_CRUISE = 0
P3M_CRUISE_FAIL = 1

P3MModeDesc = [_("Cruise"), _("Cruise & Failure code")]


# Controller model descriptions
ControllerModelDesc = [
    {
        # User-visible controller model name
        "Name": "EB206",
        # How to translate phase current to a raw value that controller understands (0-255)
        "PhaseCurrent2Raw": lambda I: I * 1.25 - 0.2,
        # The reverse transform: given a raw value, convert to current
        "Raw2PhaseCurrent": lambda R: 0.16 + (0.8 * R),
        # How to translate battery current to a raw value in the range 0-255
        "BattCurrent2Raw": lambda I: I * 1.256 + 1.25,
        # How to translate a raw value to battery current
        "Raw2BattCurrent": lambda R: (0.796 * R) - 0.995,
        # How to translate a voltage to a raw value
        "Voltage2Raw": lambda U: U * 3.281,
        # How to translate a raw value to actual voltage
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        "Name": "EB209",
        "PhaseCurrent2Raw": lambda I: I * 1.25 - 19.2,
        "Raw2PhaseCurrent": lambda R: 15.36 + (0.8 * R),
        "BattCurrent2Raw": lambda I: I * 1.256 - 2.8,
        "Raw2BattCurrent": lambda R: 2.229 + (0.796 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        "Name": "EB212",
        "PhaseCurrent2Raw": lambda I: I * 0.625 - 7,
        "Raw2PhaseCurrent": lambda R: 11.2 + (1.6 * R),
        "BattCurrent2Raw": lambda I: I * 0.624 - 1.5,
        "Raw2BattCurrent": lambda R: 2.404 + (1.603 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        "Name": "EB215",
        "PhaseCurrent2Raw": lambda I: I * 0.416 - 18.9,
        "Raw2PhaseCurrent": lambda R: 45.4327 + (2.4038 * R),
        "BattCurrent2Raw": lambda I: I * 0.425 - 3.3,
        "Raw2BattCurrent": lambda R: 7.765 + (2.353 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        "Name": "EB218",
        "PhaseCurrent2Raw": lambda I: I * 0.187 - 0.1,
        "Raw2PhaseCurrent": lambda R: 0.5348 + (5.3476 * R),
        "BattCurrent2Raw": lambda I: I * 0.213 + 0.1,
        "Raw2BattCurrent": lambda R: (4.695 * R) - 0.469,
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        # According to Lyen, shunt value for EB206 is 4 milliohm
        "Name": "EB206/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 1.25 - 0.2,
        "Raw2PhaseCurrent": lambda R: 0.16 + (0.8 * R),
        "BattCurrent2Raw": lambda I: I * 1.249 - 4.26,
        "Raw2BattCurrent": lambda R: 3.41 + (0.8 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
    },
    {
        "Name": "EB209/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 1.25 - 19.2,
        "Raw2PhaseCurrent": lambda R: 15.36 + (0.8 * R),
        "BattCurrent2Raw": lambda I: I * 1.249 - 2.26,
        "Raw2BattCurrent": lambda R: 1.81 + (0.8 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        # Temporary hack until someone finds out what's this
        # Looks like this is some rudiment of "Speed4" from EB3xx
        "Byte23": 80,
    },
    {
        "Name": "EB212/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 0.625 - 7,
        "Raw2PhaseCurrent": lambda R: 11.2 + (1.6 * R),
        "BattCurrent2Raw": lambda I: I * 0.631 - 1.5,
        "Raw2BattCurrent": lambda R: 2.38 + (1.58 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        "Byte23": 80,
    },
    {
        "Name": "EB215/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 0.834 - 30.1,
        "Raw2PhaseCurrent": lambda R: 36.09 + (1.199 * R),
        "BattCurrent2Raw": lambda I: I * 0.83 - 5.86,
        "Raw2BattCurrent": lambda R: 7.06 + (1.205 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        "Byte23": 80,
    },
    {
        "Name": "EB218/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 0.624 - 16,
        "Raw2PhaseCurrent": lambda R: 25.64 + (1.6 * R),
        "BattCurrent2Raw": lambda I: I * 0.625 - 5,
        "Raw2BattCurrent": lambda R: 8 + (1.6 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        "Byte23": 80,
    },
    {
        "Name": "EB224/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 0.624 - 18,
        "Raw2PhaseCurrent": lambda R: 28.846 + (1.6 * R),
        "BattCurrent2Raw": lambda I: I * 0.627 - 4.12,
        "Raw2BattCurrent": lambda R: 6.57 + (1.594 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        "Byte23": 80,
    },
    {
        "Name": "EB232/Lyen",
        "PhaseCurrent2Raw": lambda I: I * 0.5 - 20.2,
        "Raw2PhaseCurrent": lambda R: 40.4 + (2 * R),
        "BattCurrent2Raw": lambda I: I * 0.5 - 4,
        "Raw2BattCurrent": lambda R: 8 + (2 * R),
        "Voltage2Raw": lambda U: U * 3.281,
        "Raw2Voltage": lambda R: R / 3.281,
        "Byte23": 80,
    },
    {
        # According to methods, shunt value is 0.23 mOhm,
        # and is twice smaller than the stock shunt in EB218
        "Name": "EB218/Crystalyte",
        "PhaseCurrent2Raw": lambda I: (I * 0.0935) - 0.05,
        "Raw2PhaseCurrent": lambda R: 0.5348 + (10.6952 * R),
        "BattCurrent2Raw": lambda I: (I * 0.1065) + 0.05,
        "Raw2BattCurrent": lambda R: (9.3897 * R) - 0.469,
        "Voltage2Raw": lambda U: (U * 3.281) / 1.2,
        "Raw2Voltage": lambda R: (R / 3.281) * 1.2,
    },
]


# This array describes all the controller parameters
ControllerParameters = {
    # The name of the variable to hold this parameter
    "ControllerModel": {
        # Parameter type (the '/' is a special hack flag for ControllerModel)
        "Type": "i/",
        # A short user-friendly parameter description
        "Name": _("Controller model"),
        # Long parameter description
        "Description": _("""\
The type of your controller. This influences the coefficients assumed for \
various parts of the controller, e.g. shunts, resistive dividers.\
"""),
        # Default parameter value (when creating a new profile)
        "Default": 1,
        # The widget type used to edit this parameter
        "Widget": infineon.PWT_COMBOBOX,
        # This field contains the (min, max) values tuple for current parameter
        "Range": (1, len(ControllerModelDesc)),
        # This function translates the numeric param value to a user-friendly string
        "GetDisplay": lambda prof, v: ControllerModelDesc[v - 1]["Name"],
    },
    "PhaseCurrent": {
        "Type": "f",
        "Name": _("Phase current limit"),
        "Description": _("""\
The current limit in motor phase wires. Since the e-bike controller is, \
in a sense, a step-down DC-DC converter, the motor current can actually be \
much higher than the battery current. When setting this parameter, make \
sure you don't exceed the capabilities of the MOSFETs in your controller. \
This parameter mostly affects the acceleration on low speeds.\
"""),
        "Default": 30,
        # A list of parameters this one depends on
        "Depends": ["ControllerModel"],
        # The measurement units for this parameter
        "Units": _("A"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (1, 255),
        # This function converts the raw value to displayed value (in amps)
        "GetDisplay": lambda prof, v: prof.GetController()["Raw2PhaseCurrent"](v),
        # This function converts the displayed value to raw (when user enters the value directly)
        "SetDisplay": lambda prof, v: round(prof.GetController()["PhaseCurrent2Raw"](v)),
    },
    "BatteryCurrent": {
        "Type": "f",
        "Name": _("Battery current limit"),
        "Description": _("""\
The limit for the current drawn out of the battery. Make sure this does \
not exceed the specs for your battery, otherwise you will lose a lot of \
energy heating up the battery (and may blow it, too).\
"""),
        "Default": 14,
        "Depends": ["ControllerModel"],
        "Units": _("A"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (1, 255),
        "GetDisplay": lambda prof, v: prof.GetController()["Raw2BattCurrent"](v),
        "SetDisplay": lambda prof, v: round(prof.GetController()["BattCurrent2Raw"](v)),
    },
    "LowVoltage": {
        "Type": "f",
        "Name": _("Battery low voltage"),
        "Description": _("""\
The voltage at which controller cuts off the power. Make sure this is \
at least equal to lowest_cell_voltage x cell_count (e.g. for a \
12S LiFePO4 battery this would be 2.6 * 12 = 31.2V). This does not \
matter much if you use a BMS, since it will cut the power as soon \
as *any* cell reaches the lowest voltage, which is much better for \
the health of your battery.\
"""),
        "Default": 32.5,
        "Depends": ["ControllerModel"],
        "Units": _("V"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (1, 255),
        "GetDisplay": lambda prof, v: prof.GetController()["Raw2Voltage"](v),
        "SetDisplay": lambda prof, v: round(prof.GetController()["Voltage2Raw"](v)),
    },
    "LowVoltageTolerance": {
        "Type": "f",
        "Name": _("Battery low voltage threshold"),
        "Description": _("""\
The amount of volts for the battery voltage to rise after a cutoff \
due to low voltage for the controller to restore power back. This is \
most useful for plumbum batteries, as they tend to restore voltage \
after a bit of rest.\
"""),
        "Default": 1.0,
        "Depends": ["ControllerModel"],
        "Units": _("V"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (1, 255),
        "GetDisplay": lambda prof, v: prof.GetController()["Raw2Voltage"](v),
        "SetDisplay": lambda prof, v: round(prof.GetController()["Voltage2Raw"](v)),
    },
    "SpeedSwitchMode": {
        "Type": "i",
        "Name": _("Speed switch mode"),
        "Description": _("""\
The way how the speed switch functions. When in 'Switch' mode you may \
use a three-position switch which connects X1 (speed 1) or X2 (speed 3) \
to GND, or leaves both unconnected (speed 2). In 'Cycle' mode connecting \
X1 to ground with a momentary switch will toggle between speeds 1, 2 and 3 \
(speed 1 is default after power-on).\
"""),
        "Default": SSM_SWITCH,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: SpeedSwitchModeDesc[v],
    },
    "Speed1": {
        "Type": "i",
        "Name": _("Speed limit 1"),
        "Description": _("""\
The first speed limit.(see comment to 'speed switch mode').\
"""),
        "Default": 100,
        "Units": "%",
        "Widget": infineon.PWT_SPINBUTTON,
        "Precision": 0,
        "Range": (1, 95),
        "GetDisplay": lambda prof, v: v * 1.26,
        "SetDisplay": lambda prof, v: round(v / 1.26),
    },
    "Speed2": {
        "Type": "i",
        "Name": _("Speed limit 2"),
        "Description": _("""\
The second speed limit.(see comment to 'speed switch mode').\
"""),
        "Default": 100,
        "Units": "%",
        "Widget": infineon.PWT_SPINBUTTON,
        "Precision": 0,
        "Range": (1, 95),
        "GetDisplay": lambda prof, v: v * 1.26,
        "SetDisplay": lambda prof, v: round(v / 1.26),
    },
    "Speed3": {
        "Type": "i",
        "Name": _("Speed limit 3"),
        "Description": _("""\
The third speed limit.(see comment to 'speed switch mode').\
"""),
        "Default": 100,
        "Units": "%",
        "Widget": infineon.PWT_SPINBUTTON,
        "Precision": 0,
        "Range": (1, 95),
        "GetDisplay": lambda prof, v: v * 1.26,
        "SetDisplay": lambda prof, v: round(v / 1.26),
    },
    "LimitedSpeed": {
        "Type": "i",
        "Name": _("Limited speed"),
        "Description": _("""\
The speed corresponding to 100% throttle when the 'speed limit' \
switch/wires are enabled (when the 'SL' board contact is connected \
to ground).\
"""),
        "Default": 100,
        "Units": "%",
        "Widget": infineon.PWT_SPINBUTTON,
        "Precision": 0,
        "Range": (1, 128),
        "GetDisplay": lambda prof, v: v / 1.28,
        "SetDisplay": lambda prof, v: round(v * 1.28),
    },
    "ReverseSpeed": {
        "Type": "i",
        "Name": _("Reverse speed"),
        "Description": _("""\
The speed at which motor runs in reverse direction when the DX3 \
board contact is connected to ground.\
"""),
        "Default": 35,
        "Units": "%",
        "Widget": infineon.PWT_SPINBUTTON,
        "Precision": 0,
        "Range": (1, 128),
        "GetDisplay": lambda prof, v: v / 1.28,
        "SetDisplay": lambda prof, v: round(v * 1.28),
    },
    "BlockTime": {
        "Type": "f",
        "Name": _("Overcurrent detection delay"),
        "Description": _("""\
The amount of time before the phase current limit takes effect  \
Rising this parameter will help you start quicker from a dead stop, \
but don't set this too high as you risk blowing out your motor - \
at high currents it will quickly heat up. Set it to 0 to disable overcurrent. \
"""),
        "Default": 1.0,
        "Units": _("s"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (0, 100),
        "GetDisplay": lambda prof, v: v / 10.0,
        "SetDisplay": lambda prof, v: round(v * 10),
    },
    "AutoCruisingTime": {
        "Type": "f",
        "Name": _("Auto cruising time"),
        "Description": _("""\
The amount of seconds to hold the throttle position unchanged \
before the 'cruising' mode will be enabled. For this to work \
you need to connect the CR contact on the board to ground.\
"""),
        "Default": 5.0,
        "Units": _("s"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (10, 150),
        "GetDisplay": lambda prof, v: v / 10.0,
        "SetDisplay": lambda prof, v: round(v * 10),
    },
    "SlipChargeMode": {
        "Type": "i",
        "Name": _("Slip charge mode"),
        "Description": _("""\
This parameter controls regen from the throttle. If you enable it, \
throttling back will enable regen (and thus will brake) until the \
electronic braking becomes ineffective (at about 15% of full speed).\
"""),
        "Default": SCM_DISABLE,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: SlipChargeModeDesc[v],
    },
    "IndicatorMode": {
        "Type": "i",
        "Name": _("LED indicator mode"),
        "Description": _("""\
This sets the mode of the P1, P2 and P3 contacts on the board. \
The connected LEDs may use either a common GND or common VCC. \
P1 lights when Speed1 is selected, P2 lights when Speed3 is selected. \
In "164 mode" P1-DAT, P2-CLK."""),
        "Default": IM_COMM_GND,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 2),
        "GetDisplay": lambda prof, v: IndicatorModeDesc[v],
    },
    "EBSLevel": {
        "Type": "i",
        "Name": _("EBS level"),
        "Description": _("""\
Electronic braking level. Choose 'Moderate' for smaller wheel diameters, \
and 'Strong' for 26" and up. In 'Unlimited' mode controller does not impose \
any limits on braking strength; this is a undocumented feature and is \
not guaranteed to work with your controller. The larger is the level, \
the more effective is braking.\
"""),
        "Default": EBS_DISABLED,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 3),
        "GetDisplay": lambda prof, v: EBSLevelDesc[v],
        # This member, if defined, tells how to translate setting to raw value
        "ToRaw": lambda prof, v: EBSLevel2Raw[v],
    },
    "EBSLimVoltage": {
        "Type": "f",
        "Name": _("EBS limit voltage"),
        "Description": _("""\
When regen is enabled (also known as electronic braking system) \
the controller effectively acts as a step-up DC-DC converter, \
transferring energy from the motor into the battery. This sets \
the upper voltage limit for this DC-DC converter, which is needed \
to prevent blowing out the controller MOSFETs.\
"""),
        "Default": 75,
        "Depends": ["ControllerModel"],
        "Units": _("V"),
        "Widget": infineon.PWT_SPINBUTTON,
        "Range": (1, 255),
        "GetDisplay": lambda prof, v: prof.GetController()["Raw2Voltage"](v),
        "SetDisplay": lambda prof, v: round(prof.GetController()["Voltage2Raw"](v)),
    },
    "GuardLevel": {
        "Type": "i",
        "Name": _("Guard signal polarity"),
        "Description": _("""\
The polarity of the Guard signal, which should be connected to the \
TB pin on the board  When Guard is active, controller will prevent \
rotating the wheel in any direction. This is useful if used together \
with a motorcycle alarm or something like that.\
"""),
        "Default": GP_LOW,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: GuardLevelDesc[v],
    },
    "ThrottleProtect": {
        "Type": "i",
        "Name": _("Throttle blowout protect"),
        "Description": _("""\
Enable this parameter to let the controller check if your \
throttle output is sane (e.g. if the Hall sensor in the throttle \
is not blown out). If it is broken, you might get a constant \
full-throttle condition, which might be not very pleasant.\
"""),
        "Default": TBP_ENABLE,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: ThrottleProtectDesc[v],
    },
    "PASMode": {
        "Type": "i",
        "Name": _("PAS mode"),
        "Description": _("""\
The time motor is running after last PAS impulse.\
"""),
        "Default": PAS_LONG,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: PASModeDesc[v],
    },
    "P3Mode": {
        "Type": "i",
        "Name": _("P3 mode"),
        "Description": _("""\
An additional setting for the P3 LED output. You may select \
between displaying only the "Cruise" mode on this LED, or both \
"Cruise" and fault conditions.\
"""),
        "Default": P3M_CRUISE,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 1),
        "GetDisplay": lambda prof, v: P3MModeDesc[v],
    },
    "SensorAngle": {
        "Type": "i",
        "Name": _("Hall sensors angle"),
        "Description": _("""\
The (electric) angle between Hall sensors in your motor. Most \
motors use sensors at 120 degrees, but sometimes this may differ. \
Choose "Auto" if you want the controller to detect this \
automatically.\
"""),
        "Default": SA_COMPAT,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (0, 2),
        "GetDisplay": lambda prof, v: SensorAngleDesc[v],
    },
}

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

class Profile(infineon.Profile):

    # Parameter order when loading from .asv files
    ParamLoadOrder = [
        "ControllerModel", "PhaseCurrent", "BatteryCurrent", "LowVoltage",
        "LowVoltageTolerance", "LimitedSpeed", "SpeedSwitchMode", "Speed1", "Speed2",
        "Speed3", "BlockTime", "AutoCruisingTime", "SlipChargeMode",
        "IndicatorMode", "EBSLevel", "ReverseSpeed", "EBSLimVoltage",
        "GuardLevel", "ThrottleProtect", "PASMode", "P3Mode", "SensorAngle"
    ]

    # The order of parameters in the profile edit dialog
    ParamEditOrder = [
        [],
        "ControllerModel",
        [_("Current/Voltage design")],
        "BatteryCurrent",
        "PhaseCurrent",
        "BlockTime",
        "LowVoltage",
        "LowVoltageTolerance",
        [_("Speed modes")],
        "SpeedSwitchMode",
        "Speed1",
        "Speed2",
        "Speed3",
        "LimitedSpeed",
        "ReverseSpeed",
        [_("Regeneration")],
        "EBSLevel",
        "EBSLimVoltage",
        "SlipChargeMode",
        [_("External devices")],
        "SensorAngle",
        "AutoCruisingTime",
        "GuardLevel",
        "ThrottleProtect",
        "PASMode",
        "IndicatorMode",
        "P3Mode",
    ]

    # The order of parameters in raw binary data sent to controller
    ParamRawOrder = [
        2,
        15,
        "PhaseCurrent",
        "BatteryCurrent",
        "LowVoltage",
        "LowVoltageTolerance",
        "LimitedSpeed",
        "SpeedSwitchMode",
        "Speed1",
        "Speed2",
        "Speed3",
        "BlockTime",
        "AutoCruisingTime",
        "SlipChargeMode",
        "IndicatorMode",
        "EBSLevel",
        "ReverseSpeed",
        "EBSLimVoltage",
        "GuardLevel",
        "ThrottleProtect",
        "PASMode",
        "P3Mode",
        "SensorAngle",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]

    def __init__(self, Family, FileName):
        infineon.Profile.__init__(self, Family, FileName,
                                  ControllerModelDesc, ControllerParameters)
        self.Download = self.Download_EB3xx_KH6xx

    def OpenSerial(self, com_port):
        try:
            return serial.Serial(com_port, 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                                 serial.STOPBITS_ONE, timeout=0.2)
        except serial.SerialException as e:
            raise serial.SerialException(str(e).decode(locale.getpreferredencoding()))

    def Upload(self, com_port, progress_func):
        data = self.BuildRaw()
        ser = self.OpenSerial(com_port)

        progress_func(msg=_("Waiting for controller ready"))
        # Send '8's and wait for the 'U' response
        skip_write = False
        while True:
            if not skip_write:
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
        ser.write(data)
        for i in range(10):
            c = ser.read()
            if c == b'U':
                return True

            if len(c) > 0:
                raise Exception(_("Invalid reply byte '%(chr)02x'") % {"chr": ord(c)})

            if not progress_func():
                break

        return False

def DetectFormat2(l):
    if len(l) < 22:
        return False

    i = l[0].find(':')
    if i >= 0:
        ct = l[0][i + 1:]
        if ct[:3] == "EB2":
            return True

    return False

infineon.RegisterFamily(_("EB2xx (Infineon 2)"), Profile, DetectFormat2, 0,
                        ControllerModelDesc)
