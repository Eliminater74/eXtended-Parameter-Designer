#!/usr/bin/python3
"""eXtended Parameter Designer
"""

__author__ = "Andrey Zabolotnyi"
__email__ = "zap@cobra.ru"
__license__ = """
xpd - an extended e-bike controller parameter designer tool
Copyright (C) 2011 Andrey Zabolotnyi <zap@cobra.ru>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

try:
    import serial
except ImportError:
    raise SystemExit("FATAL: This program requires PySerial to run")

import sys, os
import gettext
import xpdm
import locale

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk as gtk, GObject as gobject
except ImportError:
    print("This program requires PyGTK to run")
    sys.exit(1)

import KT  # Import the KT module here

# check PySerial version number
from distutils.version import LooseVersion
# PySerial version 2.3 incorrectly reports version 1.35... eeek!
if serial.VERSION == "1.35":
    serial.VERSION = "2.3"
if LooseVersion(serial.VERSION) < LooseVersion("2.3"):
    dialog = gtk.MessageDialog(None, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.CLOSE,
                               "This program requires PySerial version 2.3 and above")
    dialog.run()
    dialog.destroy()
    sys.exit(1)

if __name__ == "__main__":
    try:
        # Additional windows-specific mumbo-jumbo
        from xpdm import gettext_windows
        xpdm.gettext_windows.setup_env()

        # Find the language translation files
        localedir = None
        if not gettext.find("xpd"):
            localedir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "locale")

        # Load the language translation file for our application
        gettext.install("xpd", localedir)

        # Set the translation domain for libintl (Python uses its own locale library)
        try:
            locale.bindtextdomain("xpd", localedir)
            locale.bind_textdomain_codeset("xpd", 'utf-8')
        except AttributeError:
            # hack: windows locale doesn't contain bindtextdomain
            import ctypes
            libintl = ctypes.cdll.LoadLibrary("intl.dll")
            libintl.bindtextdomain('xpd', localedir)
            libintl.bind_textdomain_codeset('xpd', 'utf-8')

    except Exception as e:
        # Fallback to English
        import builtins
        builtins.__dict__['_'] = str

    try:
        # Load the GUI now so that translation of global statics will work
        from xpdm import gui

        app = gui.Application()
        app.Initialize("xpd")
        gtk.main()

    except Exception as e:
        import traceback
        dialog = gtk.MessageDialog(None, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.CLOSE,
                                   _("Ooops! Something bad happened, and I can't handle it! "\
                                     "Please report the following information to author:\n\n%(msg)s") % \
                                   {"msg": "\n".join(traceback.format_exception(*sys.exc_info()))})
        dialog.run()
        dialog.destroy()
        sys.exit(1)
