# -*- coding: utf-8 -*-
# Infineon-style e-bike controller profile
# Support for KH6xx family
#

import serial
import time
import locale
from xpdm import infineon

# -- # Constants # -- #

# Bit flags
BF_120 = 1
BF_EBS = 2
BF_SOFTSTART = 4
BF_LVHALT = 8

def BitFlagsToRaw (prof, v):
    f = 0
    if v & BF_120:
        f |= 0x80
    if v & BF_EBS:
        f |= 0x40
    if v & BF_SOFTSTART:
        f |= 0x20
    if v & BF_LVHALT:
        f |= 0x10
    return f

def BitFlagsFromRaw (prof, v):
    f = 0
    if v & 0x80:
        f |= BF_120
    if v & 0x40:
        f |= BF_EBS
    if v & 0x20:
        f |= BF_SOFTSTART
    if v & 0x10:
        f |= BF_LVHALT
    return f

SensorAngleDesc = [ "60°", "120°" ]

# Three-speed switch modes
SSM_SWITCH = 0
SSM_CYCLE3 = 1
SSM_HISWITCH = 2
SSM_CYCLE4 = 3

SpeedSwitchModeDesc = [ _("Switch"), _("Cycle 3"), _("High Switch"), _("Cycle 4") ]

# LED indicator mode
IM_COMM_VCC = 0
IM_COMM_GND = 1

IndicatorModeDesc = [ _("Common VCC"), _("Common GND") ]

# Slip charge mode
SCM_ENABLE = 0
SCM_DISABLE = 1

SlipChargeModeDesc = [ _("Enable"), _("Disable") ]

# EBS level
EBS_DISABLED = 0
EBS_MODERATE = 1
EBS_STRONG = 2

EBSLevelDesc = [ _("Disabled"), _("Moderate"), _("Strong"), _("Unlimited") ]
EBSLevel2Raw = [ 0, 4, 8, 255 ]

# Guard mode signal polarity (anti-theft)
GP_LOW = 0
GP_HIGH = 1

GuardLevelDesc = [ _("Low"), _("High") ]

# Throttle blowout protect
TBP_DISABLE = 0
TBP_ENABLE = 1

ThrottleProtectDesc = [ _("Disabled"), _("Enabled") ]

# Cruise limit
CruiseLimitDesc = [ _("No"), _("Yes") ]

# Default speed
DefaultSpeedDesc = [ _("Speed 1"), _("Speed 2"), _("Speed 3"), _("Speed 4") ]

# Controller model descriptions
ControllerModelDesc = \
[
    {
        "Name"             : "KH606",
        "PhaseCurrent2Raw" : lambda I: I * 2.85,
        "Raw2PhaseCurrent" : lambda R: R / 2.85,
        "BattCurrent2Raw"  : lambda I: I * 5.10,
        "Raw2BattCurrent"  : lambda R: R / 5.10,
        "Voltage2Raw"      : lambda U: U * 3.285,
        "Raw2Voltage"      : lambda R: R / 3.285,
        "ControllerModel"  : 1,
    },
    {
        "Name"             : "KH609",
        "PhaseCurrent2Raw" : lambda I: I * 2.46,
        "Raw2PhaseCurrent" : lambda R: R / 2.46,
        "BattCurrent2Raw"  : lambda I: I * 5.10,
        "Raw2BattCurrent"  : lambda R: R / 5.10,
        "Voltage2Raw"      : lambda U: U * 3.285,
        "Raw2Voltage"      : lambda R: R / 3.285,
        "ControllerModel"  : 2,
    },
    {
        "Name"             : "KH612",
        "PhaseCurrent2Raw" : lambda I: I * 1.20,
        "Raw2PhaseCurrent" : lambda R: R / 1.20,
        "BattCurrent2Raw"  : lambda I: I * 2.73,
        "Raw2BattCurrent"  : lambda R: R / 2.73,
        "Voltage2Raw"      : lambda U: U * 3.285,
        "Raw2Voltage"      : lambda R: R / 3.285,
        "ControllerModel"  : 3,
    },
    {
        "Name"             : "KH615",
        "PhaseCurrent2Raw" : lambda I: I * 0.79,
        "Raw2PhaseCurrent" : lambda R: R / 0.79,
        "BattCurrent2Raw"  : lambda I: I * 2.55,
        "Raw2BattCurrent"  : lambda R: R / 2.55,
        "Voltage2Raw"      : lambda U: U * 3.285,
        "Raw2Voltage"      : lambda R: R / 3.285,
        "ControllerModel"  : 4,
    },
    {
        "Name"             : "KH618",
        "PhaseCurrent2Raw" : lambda I: I * 0.53,
        "Raw2PhaseCurrent" : lambda R: R / 0.53,
        "BattCurrent2Raw"  : lambda I: I * 1.70,
        "Raw2BattCurrent"  : lambda R: R / 1.70,
        "Voltage2Raw"      : lambda U: U * 3.285,
        "Raw2Voltage"      : lambda R: R / 3.285,
        "ControllerModel"  : 5,
    },
];


# This array describes all the controller parameters
ControllerParameters = \
{
    "ControllerModel" :
    {
        "Type"        : "i/",
        "Name"        : _("Controller model"),
        "Description" : _("""\
The type of your controller. This influences the coefficients assumed for \
various parts of the controller, e.g. shunts, resistive dividers.\
"""),
        "Default"     : 1,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (1, len (ControllerModelDesc)),
        "GetDisplay"  : lambda prof, v: ControllerModelDesc [v - 1]["Name"],
        "ToRaw"       : lambda prof, v: ControllerModelDesc [v - 1]["ControllerModel"],
    },

    "PhaseCurrent" :
    {
        "Type"        : "f",
        "Name"        : _("Phase current limit"),
        "Description" : _("""\
The current limit in motor phase wires. Since the e-bike controller is, \
in a sense, a step-down DC-DC converter, the motor current can actually be \
much higher than the battery current. When setting this parameter, make \
sure you don't exceed the capabilities of the MOSFETs in your controller. \
This parameter mostly affects the acceleration on low speeds.\
"""),
        "Default"     : 30,
        "Depends"     : [ "ControllerModel" ],
        "Units"       : _("A"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: prof.GetController () ["Raw2PhaseCurrent"] (v),
        "SetDisplay"  : lambda prof, v: round (prof.GetController () ["PhaseCurrent2Raw"] (v)),
    },

    "BatteryCurrent" :
    {
        "Type"        : "f",
        "Name"        : _("Battery current limit"),
        "Description" : _("""\
The limit for the current drawn out of the battery. Make sure this does \
not exceed the specs for your battery, otherwise you will lose a lot of \
energy heating up the battery (and may blow it, too).\
"""),
        "Default"     : 14,
        "Depends"     : [ "ControllerModel" ],
        "Units"       : _("A"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: prof.GetController () ["Raw2BattCurrent"] (v),
        "SetDisplay"  : lambda prof, v: round (prof.GetController () ["BattCurrent2Raw"] (v)),
    },

    "CurrentCompensation" :
    {
        "Type"        : "i",
        "Name"        : _("Current compensation"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 85,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (0, 100),
        "Precision"   : 0,
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "LowVoltage" :
    {
        "Type"        : "f",
        "Name"        : _("Battery low voltage"),
        "Description" : _("""\
The voltage which is considered 'low'. The actual behavior depends \
on the 'Halt on low voltage' checkbox. If it is enabled, controller \
will instantly stop when voltage drops below this level. If it is \
not enabled, a new set of speed and current limits will be used instead \
of the default.\
"""),
        "Default"     : 32.5,
        "Depends"     : [ "ControllerModel" ],
        "Units"       : _("V"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: prof.GetController () ["Raw2Voltage"] (v),
        "SetDisplay"  : lambda prof, v: round (prof.GetController () ["Voltage2Raw"] (v)),
    },

    "LowVoltageTolerance" :
    {
        "Type"        : "f",
        "Name"        : _("Battery low voltage threshold"),
        "Description" : _("""\
The amount of volts for the battery voltage to rise after the 'low voltage' \
condition has been triggered to quit the 'low voltage' condition. This is \
most useful for plumbum batteries, as they tend to restore voltage \
after a bit of rest.\
"""),
        "Default"     : 1.0,
        "Depends"     : [ "ControllerModel" ],
        "Units"       : _("V"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: prof.GetController () ["Raw2Voltage"] (v),
        "SetDisplay"  : lambda prof, v: round (prof.GetController () ["Voltage2Raw"] (v)),
    },

    "LowVoltageHalt" :
    {
        "Type"        : "i",
        "Name"        : _("Halt on low voltage"),
        "Description" : _("""\
Select this option if you want controller to instantly halt if battery voltage \
drops below defined voltage threshold. If you leave this unchecked, a different \
set of limits for speeds and currents will be applied if the voltage is low.
If you select this option, make sure battery low threshold is \
at least equal to lowest_cell_voltage x cell_count (e.g. for a \
12S LiFePO4 battery this would be 2.6 * 12 = 31.2V).\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_CHECKBOX,
        "BitField"    : "BitFlags",
        "BitShift"    : infineon.log2 (BF_LVHALT),
        "BitMask"     : BF_LVHALT,
    },

    "LowVoltageCurrent" :
    {
        "Type"        : "f",
        "Name"        : _("Low voltage current limit"),
        "Description" : _("""\
If battery voltage drops below \"Battery low voltage\", battery current \
can be limited to a relatively safe low value. This is especially useful if \
you set the low voltage threshold somewhat higher than the voltage at which \
your BMS will cut the power off.\
"""),
        "Default"     : 10,
        "Units"       : _("A"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: v / 13.18,
        "SetDisplay"  : lambda prof, v: round (v * 13.18),
    },

    "SpeedSwitchMode" :
    {
        "Type"        : "i",
        "Name"        : _("Speed switch mode"),
        "Description" : _("""\
The way how the speed switch functions. When in 'Switch' mode you may \
use a three-position switch which connects X1 (speed 1) or X2 (speed 3) \
to GND, or leaves both unconnected (speed 2). In 'Cycle 3' mode connecting \
X1 to ground with a momentary switch will cycle speeds 1-2-3. \
The 'High Switch' mode is similar to 'Switch', but X1/X2 should \
connect to high voltage (+5V or +BAT). The 'Cycle 4' mode is like \
'Cycle 3', but cycles between speeds 1-2-3-4.\
"""),
        "Default"     : SSM_SWITCH,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 3),
        "GetDisplay"  : lambda prof, v: SpeedSwitchModeDesc [v],
    },

    "DefaultSpeed" :
    {
        "Type"        : "i",
        "Name"        : _("Default speed"),
        "Description" : _("""\
This determines which of the four programmed speed limits will be default \
after power on, if the speed selector switch is missing.\
"""),
        "Default"     : 1,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 3),
        "GetDisplay"  : lambda prof, v: DefaultSpeedDesc [v],
    },

    "Speed1" :
    {
        "Type"        : "i",
        "Name"        : _("Speed limit 1"),
        "Description" : _("""\
The first speed limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Current1":
    {
        "Type"        : "i",
        "Name"        : _("Current limit 1"),
        "Description" : _("""\
First current limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (0, 141),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "LowVoltageSpeed1":
    {
        "Type"        : "i",
        "Name"        : _("Low-voltage speed 1"),
        "Description" : _("""\
The first speed limit if battery voltage is lower than defined threshold.\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Speed2" :
    {
        "Type"        : "i",
        "Name"        : _("Speed limit 2"),
        "Description" : _("""\
The second speed limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Current2":
    {
        "Type"        : "i",
        "Name"        : _("Current limit 2"),
        "Description" : _("""\
Second current limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (0, 141),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "LowVoltageSpeed2":
    {
        "Type"        : "i",
        "Name"        : _("Low-voltage speed 2"),
        "Description" : _("""\
The second speed limit if battery voltage is lower than defined threshold.\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Speed3" :
    {
        "Type"        : "i",
        "Name"        : _("Speed limit 3"),
        "Description" : _("""\
The third speed limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Current3":
    {
        "Type"        : "i",
        "Name"        : _("Current limit 3"),
        "Description" : _("""\
Third current limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (0, 141),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "LowVoltageSpeed3":
    {
        "Type"        : "i",
        "Name"        : _("Low-voltage speed 3"),
        "Description" : _("""\
Third speed limit if battery voltage is lower than defined threshold.\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Speed4" :
    {
        "Type"        : "i",
        "Name"        : _("Speed limit 4"),
        "Description" : _("""\
The fourth speed limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "Current4":
    {
        "Type"        : "i",
        "Name"        : _("Current limit 4"),
        "Description" : _("""\
Fourth current limit (see comment to 'speed switch mode').\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (0, 141),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "LowVoltageSpeed4":
    {
        "Type"        : "i",
        "Name"        : _("Low-voltage speed 4"),
        "Description" : _("""\
Fourth speed limit if battery voltage is lower than defined threshold.\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 104),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "LimitedSpeed" :
    {
        "Type"        : "i",
        "Name"        : _("Limited speed"),
        "Description" : _("""\
The speed corresponding to 100% throttle when the 'speed limit' \
switch/wires are enabled (when the 'SL' board contact is connected \
to ground).\
"""),
        "Default"     : 100,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (1, 96),
        "GetDisplay"  : lambda prof, v: v / 0.96,
        "SetDisplay"  : lambda prof, v: round (v * 0.96),
    },

    "ReverseSpeed" :
    {
        "Type"        : "i",
        "Name"        : _("Reverse speed"),
        "Description" : _("""\
The speed at which motor runs in reverse direction when the DX3 \
board contact is connected to ground.\
"""),
        "Default"     : 35,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (1, 128),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "SlowSpeed" :
    {
        "Type"        : "i",
        "Name"        : _("Slow speed"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 35,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 80),
        "GetDisplay"  : lambda prof, v: v / 0.8,
        "SetDisplay"  : lambda prof, v: round (v * 0.8),
    },

    "RecoverySpeed" :
    {
        "Type"        : "i",
        "Name"        : _("Recovery speed"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 35,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (0, 128),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "SoftStartEnable" :
    {
        "Type"        : "i",
        "Name"        : _("Enable soft start"),
        "Description" : _("""\
Check this if you want the motor to start at lower currents. \
This both improves efficiency and lowers energy consumption.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_CHECKBOX,
        "BitField"    : "BitFlags",
        "BitShift"    : infineon.log2 (BF_SOFTSTART),
        "BitMask"     : BF_SOFTSTART,
    },

    "SoftStartTime" :
    {
        "Type"        : "i",
        "Name"        : _("Soft start time"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 10),
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "BlockTime" :
    {
        "Type"        : "f",
        "Name"        : _("Overcurrent detection delay"),
        "Description" : _("""\
The amount of time before the phase current limit takes effect  \
Rising this parameter will help you start quicker from a dead stop, \
but don't set this too high as you risk blowing out your motor - \
at high currents it will quickly heat up. Set it to 0 to disable overcurrent. \
"""),
        "Default"     : 1.0,
        "Units"       : _("s"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (0, 100),
        "GetDisplay"  : lambda prof, v: v / 10.0,
        "SetDisplay"  : lambda prof, v: round (v * 10),
    },

    "AutoCruisingTime" :
    {
        "Type"        : "f",
        "Name"        : _("Auto cruising time"),
        "Description" : _("""\
The amount of seconds to hold the throttle position unchanged \
before the 'cruising' mode will be enabled. For this to work \
you need to connect the CR contact on the board to ground.\
"""),
        "Default"     : 5.0,
        "Units"       : _("s"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (10, 150),
        "GetDisplay"  : lambda prof, v: v / 10.0,
        "SetDisplay"  : lambda prof, v: round (v * 10),
    },

    "SlipChargeMode" :
    {
        "Type"        : "i",
        "Name"        : _("Slip charge mode"),
        "Description" : _("""\
This parameter controls regen from the throttle. If you enable it, \
throttling back will enable regen (and thus will brake) until the \
electronic braking becomes ineffective (at about 15% of full speed).\
"""),
        "Default"     : SCM_DISABLE,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: SlipChargeModeDesc [v],
    },

    "LimitCruise" :
    {
        "Type"        : "i",
        "Name"        : _("Limit cruise"),
        "Description" : _("""\
So far it is unknown how this parameter affects controller function.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: CruiseLimitDesc [v],
    },

    "IndicatorMode" :
    {
        "Type"        : "i",
        "Name"        : _("LED indicator mode"),
        "Description" : _("""\
This sets the mode of the P1, P2 and P3 contacts on the board. \
The connected LEDs may use either a common GND or common VCC. \
P1 lights when Speed1 is selected, P2 lights when Speed3 is selected.\
"""),
        "Default"     : IM_COMM_GND,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: IndicatorModeDesc [v],
    },

    "EBSEnable" :
    {
        "Type"        : "i",
        "Name"        : _("Enable EBS"),
        "Description" : _("""\
Enable Electronic Brake System. This will transform your kinetic energy back \
into electric energy when you activate your brakes (slightly press the brake levers). \
This has the side effect of smoothly braking your electric transport without the \
risk of locking your wheels (similar to ABS on cars).\
"""),
        "Default"     : 1,
        "Widget"      : infineon.PWT_CHECKBOX,
        "BitField"    : "BitFlags",
        "BitShift"    : infineon.log2 (BF_EBS),
        "BitMask"     : BF_EBS,
    },

    "EBSForce" :
    {
        "Type"        : "i",
        "Name"        : _("EBS force"),
        "Description" : _("""\
Electronic braking force level. Choose smaller values for smaller wheel diameters. \
The larger is the level, the more effective is braking but make sure your battery \
can charge with higher currents.\
"""),
        "Default"     : 40,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (0, 200),
        "Precision"   : 0,
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "EBSLimVoltage" :
    {
        "Type"        : "f",
        "Name"        : _("EBS limit voltage"),
        "Description" : _("""\
When regen is enabled (also known as electronic braking system) \
the controller effectively acts as a step-up DC-DC converter, \
transferring energy from the motor into the battery. This sets \
the upper voltage limit for this DC-DC converter, which is needed \
to prevent blowing out the controller MOSFETs.\
"""),
        "Default"     : 60,
        "Depends"     : [ "ControllerModel" ],
        "Units"       : _("V"),
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 255),
        "GetDisplay"  : lambda prof, v: prof.GetController () ["Raw2Voltage"] (v),
        "SetDisplay"  : lambda prof, v: round (prof.GetController () ["Voltage2Raw"] (v)),
    },

    "GuardLevel" :
    {
        "Type"        : "i",
        "Name"        : _("Guard signal polarity"),
        "Description" : _("""\
The polarity of the Guard signal, which should be connected to the \
TB pin on the board  When Guard is active, controller will prevent \
rotating the wheel in any direction. This is useful if used together \
with a motorcycle alarm or something like that.\
"""),
        "Default"     : GP_LOW,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: GuardLevelDesc [v],
    },

    "ThrottleProtect" :
    {
        "Type"        : "i",
        "Name"        : _("Throttle blowout protect"),
        "Description" : _("""\
Enable this parameter to let the controller check if your \
throttle output is sane (e.g. if the Hall sensor in the throttle \
is not blown out). If it is broken, you might get a constant \
full-throttle condition, which might be not very pleasant.\
"""),
        "Default"     : TBP_ENABLE,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: ThrottleProtectDesc [v],
    },

    "PASLevel" :
    {
        "Type"        : "i",
        "Name"        : _("PAS level"),
        "Description" : _("""\
Pedal Assisted Sensor help level.\
"""),
        "Default"     : 21,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (1, 21),
        "Precision"   : 0,
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "PASStartPulse" :
    {
        "Type"        : "i",
        "Name"        : _("PAS start pulse"),
        "Description" : _("""\
The amount of pulses from the PAS sensor to skip before starting assisting \
to pedalling.\
"""),
        "Default"     : 5,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Range"       : (3, 255),
        "Precision"   : 0,
        "SetDisplay"  : lambda prof, v: v,
        "GetDisplay"  : lambda prof, v: v,
    },

    "PASMaxSpeed" :
    {
        "Type"        : "i",
        "Name"        : _("PAS max speed"),
        "Description" : _("""\
This sets the speed limit when using the pedal assistant.\
"""),
        "Default"     : 35,
        "Units"       : "%",
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 1,
        "Range"       : (1, 128),
        "GetDisplay"  : lambda prof, v: v / 1.28,
        "SetDisplay"  : lambda prof, v: round (v * 1.28),
    },

    "Angle120" :
    {
        "Type"        : "i",
        "Name"        : _("Hall sensors angle"),
        "Description" : _("""\
Select the (electric) angle between Hall sensors in your motor. \
Most motors use sensors at 120 degrees, but sometimes you may encounter 60 degree motors.\
"""),
        "Default"     : 1,
        "Widget"      : infineon.PWT_COMBOBOX,
        "Range"       : (0, 1),
        "GetDisplay"  : lambda prof, v: SensorAngleDesc [v],
        "BitField"    : "BitFlags",
        "BitShift"    : infineon.log2 (BF_120),
        "BitMask"     : BF_120,
    },

    "FluxWeaken" :
    {
        "Type"        : "i",
        "Name"        : _("Flux weakening level"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 191),
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "FluxFineTune" :
    {
        "Type"        : "i",
        "Name"        : _("Flux weakening finetune"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 255),
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "FluxWeakPosition" :
    {
        "Type"        : "i",
        "Name"        : _("Flux weakening position"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 40),
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    "FluxWeakTurnPoint" :
    {
        "Type"        : "i",
        "Name"        : _("Flux weakening turnpoint"),
        "Description" : _("""\
So far the exact meaning of this parameter is unknown.\
"""),
        "Default"     : 0,
        "Widget"      : infineon.PWT_SPINBUTTON,
        "Precision"   : 0,
        "Range"       : (0, 255),
        "GetDisplay"  : lambda prof, v: v,
        "SetDisplay"  : lambda prof, v: v,
    },

    # Invisible field to hold Angle120, EBSEnable, SoftStartEnable, LowVoltageHalt
    "BitFlags" :
    {
        "Type"        : "i",
        "ToRaw"       : BitFlagsToRaw,
        "FromRaw"     : BitFlagsFromRaw,
    }
}

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

class Profile (infineon.Profile):

    # Parameter order when loading from .asv files
    ParamLoadOrder = [
        0, # was "ControllerModel",
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
        "EBSForce",
        "ReverseSpeed",
        "EBSLimVoltage",
        "GuardLevel",
        "ThrottleProtect",
        "PASLevel",
        "PASStartPulse",
        "DefaultSpeed",
        "Speed4",
        "ControllerModel", # 24
        "LimitCruise",
        "PASMaxSpeed",
        "FluxWeaken",
        "FluxFineTune",
        "FluxWeakPosition",
        "FluxWeakTurnPoint",
        "BitFlags", # 31
        0,
        "LowVoltageSpeed1",
        "LowVoltageSpeed2",
        "LowVoltageSpeed3",
        "LowVoltageSpeed4",
        "Current1",
        "Current2",
        "Current3",
        "Current4",
        "LowVoltageCurrent",
        "SoftStartTime",
        "SlowSpeed",
        "RecoverySpeed",
        "CurrentCompensation",
        0,
        0,
        0
    ]

    # The order of parameters in the profile edit dialog
    ParamEditOrder = [
        [ ],
        "ControllerModel",

        [ _("Current/Voltage design") ],
        "BatteryCurrent",
        "PhaseCurrent",
        "BlockTime",
        "SoftStartEnable",
        "SoftStartTime",
        "LowVoltage",
        "LowVoltageTolerance",
        "LowVoltageHalt",
        "LowVoltageCurrent",
        "CurrentCompensation",

        [ _("Speed modes") ],
        "SpeedSwitchMode",
        "Speed1",
        "Current1",
        "Speed2",
        "Current2",
        "Speed3",
        "Current3",
        "Speed4",
        "Current4",
        "LowVoltageSpeed1",
        "LowVoltageSpeed2",
        "LowVoltageSpeed3",
        "LowVoltageSpeed4",
        "DefaultSpeed",
        "LimitedSpeed",
        "ReverseSpeed",
        "SlowSpeed",
        "RecoverySpeed",

        [ _("Regeneration") ],
        "EBSEnable",
        "EBSForce",
        "EBSLimVoltage",
        "SlipChargeMode",

        [ _("Pedal Assist Sensor") ],
        "PASLevel",
        "PASStartPulse",
        "PASMaxSpeed",

        [ _("Flux weakening") ],
        "FluxWeaken",
        "FluxFineTune",
        "FluxWeakPosition",
        "FluxWeakTurnPoint",

        [ _("External devices") ],
        "Angle120",
        "AutoCruisingTime",
        "LimitCruise",
        "GuardLevel",
        "ThrottleProtect",
        "IndicatorMode",
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
        "EBSForce",
        "ReverseSpeed",
        "EBSLimVoltage",
        "GuardLevel",
        "ThrottleProtect",
        "PASLevel",
        "PASStartPulse",
        "DefaultSpeed",
        "Speed4",
        "ControllerModel",
        "LimitCruise",
        "PASMaxSpeed",
        "FluxWeaken",
        "FluxFineTune",
        "FluxWeakPosition",
        "FluxWeakTurnPoint",
        "BitFlags",
        0,
        "LowVoltageSpeed1",
        "LowVoltageSpeed2",
        "LowVoltageSpeed3",
        "LowVoltageSpeed4",
        "Current1",
        "Current2",
        "Current3",
        "Current4",
        "LowVoltageCurrent",
        "SoftStartTime",
        "SlowSpeed",
        "RecoverySpeed",
        "CurrentCompensation",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0
    ]


    def __init__ (self, Family, FileName):
        infineon.Profile.__init__ (self, Family, FileName, \
            ControllerModelDesc, ControllerParameters)
        self.OpenSerial = self.OpenSerial_EB3xx_KH6xx
        self.Upload = self.Upload_EB3xx_KH6xx
        self.Download = self.Download_EB3xx_KH6xx


def DetectFormat4 (l):
    if len (l) < 48:
        return False

    i = l [23].find (':')
    if i >= 0:
        ct = l [23][i + 1:]
        if ct [:3] == "KH6":
            return True

    return False


infineon.RegisterFamily (_("KH6xx (Infineon 4)"), Profile, DetectFormat4, infineon.CAP_DOWNLOAD, \
    ControllerModelDesc)
