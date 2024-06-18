# -*- coding: utf-8 -*-
# KT-style e-bike controller profile
#

import serial
import time
import locale
from xpdm import infineon

# Define constants and mappings specific to KT controllers

# Example: Controller model descriptions
KT_ControllerModelDesc = [
    {
        "Name": "KT36/48SVPRD",
        "PhaseCurrent2Raw": lambda I: I * 3.0,
        "Raw2PhaseCurrent": lambda R: R / 3.0,
        "BattCurrent2Raw": lambda I: I * 4.5,
        "Raw2BattCurrent": lambda R: R / 4.5,
        "Voltage2Raw": lambda U: U * 2.5,
        "Raw2Voltage": lambda R: R / 2.5,
        "ControllerModel": 1,
    },
    # Add more models as necessary
]

# Define parameters specific to KT controllers
KT_ControllerParameters = {
    "ControllerModel": {
        "Type": "i/",
        "Name": _("Controller model"),
        "Description": _("The type of your KT controller."),
        "Default": 1,
        "Widget": infineon.PWT_COMBOBOX,
        "Range": (1, len(KT_ControllerModelDesc)),
        "GetDisplay": lambda prof, v: KT_ControllerModelDesc[v - 1]["Name"],
        "ToRaw": lambda prof, v: KT_ControllerModelDesc[v - 1]["ControllerModel"],
    },
    # Define other parameters similarly
}

class KT_Profile(infineon.Profile):
    # Define parameter orders and any specific methods for KT profiles
    ParamLoadOrder = [
        "ControllerModel",
        "PhaseCurrent",
        "BatteryCurrent",
        # Add more parameters as necessary
    ]

    ParamEditOrder = [
        ["General"],
        "ControllerModel",
        "PhaseCurrent",
        "BatteryCurrent",
        # Add more parameters as necessary
    ]

    ParamRawOrder = [
        "ControllerModel",
        "PhaseCurrent",
        "BatteryCurrent",
        # Add more parameters as necessary
    ]

    def __init__(self, Family, FileName):
        infineon.Profile.__init__(self, Family, FileName, KT_ControllerModelDesc, KT_ControllerParameters)
        self.OpenSerial = self.OpenSerial_EB3xx_KH6xx
        self.Upload = self.Upload_EB3xx_KH6xx
        self.Download = self.Download_EB3xx_KH6xx

def KT_DetectFormat(l):
    if len(l) < 10:
        return False
    # Implement detection logic based on KT controller specifics
    return True

infineon.RegisterFamily(_("KT Controllers"), KT_Profile, KT_DetectFormat, infineon.CAP_DOWNLOAD, KT_ControllerModelDesc)
