#
# Graphical User Interface for XPD
#

import os
import sys
import glob
import copy
import pygtk
import gtk
import gobject
import glib
import gio
import pango
import time
import locale
from xpdm import VERSION, FNENC, comports
from xpdm import infineon, EB2xx, EB3xx, KH6xx


#-----------------------------------------------------------------------------
#                          The GUI application class
#-----------------------------------------------------------------------------
class Application:
    def __init__(self):
        self.Dead = False
        self.ActiveProfile = None

        # Figure out our installation paths
        self.DATADIR = os.path.join(os.path.dirname(os.path.abspath(
            sys.argv[0])), "share")
        if not os.path.exists(self.DATADIR):
            self.DATADIR = os.path.join(os.path.normpath(sys.prefix),
                                        "share/xpd")
            if not os.path.exists(self.DATADIR):
                self.DATADIR = os.path.join(os.path.normpath(os.path.join(
                    os.path.dirname(os.path.abspath(sys.argv[0])), "..")),
                    "share/xpd")

        if not os.path.exists(self.DATADIR):
            raise SystemExit(_("FATAL: Could not find data directory"))

        self.LOCALDATADIR = os.path.join(glib.get_user_data_dir(), "xpd")
        if not os.access(self.LOCALDATADIR, os.F_OK):
            os.makedirs(self.LOCALDATADIR, 0o700)

        self.CONFIGDIR = os.path.join(glib.get_user_config_dir(), "xpd")
        if not os.access(self.CONFIGDIR, os.F_OK):
            os.makedirs(self.CONFIGDIR, 0o700)

        print("Global program data directory:", self.DATADIR)
        print("Local program data directory:", self.LOCALDATADIR)
        print("User config directory:", self.CONFIGDIR)

    def Initialize(self, textdomain):
        # Load the widgets from the GtkBuilder file
        self.builder = gtk.Builder()
        self.builder.set_translation_domain(textdomain)
        try:
            self.builder.add_from_file(self.DATADIR + "/gui.xml")
        except RuntimeError as e:
            raise SystemExit(str(e))

        # Cache most used widgets into variables
        for widget in ("AboutDialog",
                       "MainWindow", "StatusBar", "SerialPortsList", "ProfileList",
                       "ParamVBox", "UserChoice", "UserHints",
                       "CreateProfileDialog", "CreateProfileName", "CreateControllerFamily",
                       "EditProfileDialog", "ProfileName", "ControllerFamily",
                       "DownloadProfileDialog", "DownloadControllerGroup",
                       "DownloadProfileName"):
            setattr(self, widget, self.builder.get_object(widget))

        # Due to a bug in libglade we can't embed controls into the status bar
        self.ButtonCancelUpload = gtk.Button(stock="gtk-cancel")
        self.StatusBar.pack_end(self.ButtonCancelUpload, False, True, 0)
        self.ButtonCancelUpload.connect("clicked", self.on_ButtonCancelUpload_clicked)

        alignment = gtk.Alignment(0.5, 0.5)
        self.StatusBar.pack_end(alignment, False, True, 0)
        alignment.show()

        self.ProgressBar = gtk.ProgressBar()
        alignment.add(self.ProgressBar)

        self.StatusCtx = self.StatusBar.get_context_id("")

        self.builder.connect_signals(self)

        self.InitProfileList()
        self.LoadProfiles()

        self.FillFamilies(self.ControllerFamily)
        self.FillFamilies(self.CreateControllerFamily)
        self.FillGroups(self.DownloadControllerGroup)

        # Dynamic serial port list update worker
        self.SerialPortsHash = None
        self.UpdateSerialPorts()
        glib.timeout_add_seconds(1, self.RefreshSerialPorts)

        # Enable image buttons on Windows; on Linux you can change it via preferences
        if os.name == "nt":
            settings = gtk.settings_get_default()
            settings.set_property("gtk-button-images", True)

        self.MainWindow.show()

        self.SetStatus(_("Ready"))

    # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

    def ClearChildren(self, widget, vbox):
        vbox.remove(widget)

    def SetStatus(self, msg):
        if not self.Dead:
            self.StatusBar.pop(self.StatusCtx)
            self.StatusBar.push(self.StatusCtx, msg)

    def Message(self, typ, msg):
        d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, typ, gtk.BUTTONS_CLOSE, msg)
        d.run()
        d.destroy()

    def InitProfileList(self):
        self.ProfileListStore = gtk.ListStore(str, str, str, str)

        self.ProfileList.set_model(self.ProfileListStore)

        column = gtk.TreeViewColumn(_("Family"), gtk.CellRendererText(), text=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_resizable(True)
        column.set_sort_column_id(0)
        column.set_min_width(150)
        self.ProfileList.append_column(column)

        column = gtk.TreeViewColumn(_("Model"), gtk.CellRendererText(), text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_resizable(True)
        column.set_sort_column_id(1)
        column.set_min_width(120)
        self.ProfileList.append_column(column)

        column = gtk.TreeViewColumn(_("Description"), gtk.CellRendererText(), text=2)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_resizable(True)
        column.set_sort_column_id(2)
        self.ProfileList.append_column(column)

        self.ProfileListStore.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def RefreshSerialPorts(self):
        if self.Dead:
            return False
        if self.ButtonCancelUpload.get_visible():
            return True

        spl = []
        sph = 0
        for order, port, desc, hwid in sorted(comports()):
            spl.append(port)
            sph += hash(port)

        if sph == self.SerialPortsHash:
            return True

        self.UpdateSerialPorts(spl, sph)
        return True

    def UpdateSerialPorts(self, spl=None, sph=None):
        if spl is None:
            spl = []
            sph = 0
            for order, port, desc, hwid in sorted(comports()):
                spl.append(port)
                sph += hash(port)

        store = self.SerialPortsList.get_model()
        if store is None:
            selport = None

            store = gtk.ListStore(str)
            cell = gtk.CellRendererText()
            self.SerialPortsList.pack_start(cell, True)
            self.SerialPortsList.add_attribute(cell, 'text', 0)
            self.SerialPortsList.set_model(store)
        else:
            selport = self.SerialPortsList.get_active_text()

        store.clear()
        idx = 0
        act = 0
        for port in spl:
            store.append([port])
            if selport == port:
                act = idx
            idx += 1
        self.SerialPortsList.set_active(act)
        self.SerialPortsHash = sph

        self.SetStatus(_("Serial ports list updated"))

    def UpdateProgress(self, pos=None, msg=None):
        if msg is not None:
            self.SetStatus(msg)
        if pos is None:
            self.ProgressBar.pulse()
        else:
            if pos > 1.0:
                pos = 1.0
            self.ProgressBar.set_fraction(pos)
        while gtk.events_pending():
            gtk.main_iteration()

        return not (self.UploadCancelled or self.Dead)

    def EditProfile(self, prof, oldsel=None):
        if prof is None:
            return

        if oldsel is None:
            selected_prof = prof.Description[:]
        else:
            selected_prof = oldsel
        self.ProfileName.set_text(prof.Description)
        self.SelectFamily(prof.Family)
        prof.FillParameters(self.ParamVBox)

        self.ActiveProfile = prof

        self.EditProfileDialog.show()
        ok = self.EditProfileDialog.run() == gtk.RESPONSE_APPLY
        self.EditProfileDialog.hide()

        self.ParamVBox.foreach(self.ClearChildren, self.ParamVBox)
        prof = self.ActiveProfile
        self.ActiveProfile = None

        if ok:
            # Rename profile, if profile name changed
            try:
                newname = self.ProfileName.get_text().strip()
                if newname != prof.Description:
                    prof.SetDescription(newname)
                    selected_prof = newname[:]
                    self.SetStatus(_("Profile renamed"))
            except OSError as e:
                self.Message(gtk.MESSAGE_ERROR,
                             _("Failed to rename profile %(desc)s:\n%(msg)s") %
                             {"desc": prof.Description, "msg": e})
                self.SetStatus(_("Failed to rename profile"))

            # Save profile, if we have enough access rights
            try:
                prof.Save()
                selected_prof = prof.Description[:]
                self.SetStatus(_("Profile saved"))
            except IOError as e:
                self.Message(gtk.MESSAGE_ERROR,
                             _("Failed to save profile %(desc)s:\n%(msg)s") %
                             {"desc": prof.Description, "msg": e})
                self.SetStatus(_("Failed to save profile"))

        self.LoadProfiles(selected_prof)

    def LoadProfiles(self, sel=None):
        # Remember the old selection, before re-filling the list
        model = self.ProfileList.get_model()
        if not sel:
            sel = self.ProfileList.get_selection().get_selected()[1]
            if sel:
                sel = model[sel][2]

        self.ProfileListStore.clear()
        # Python bug: glob() with unicode argument will use locale.getpreferredencoding()
        # for file name encoding, which is not compatible with glib filename encodings
        for x in glob.glob(os.path.join(self.DATADIR.encode(FNENC), "*.asv")) + \
                 glob.glob(os.path.join(self.LOCALDATADIR.encode(FNENC), "*.asv")) + \
                 glob.glob(os.path.join(self.CONFIGDIR.encode(FNENC), "*.asv")):
            try:
                prof = self.LoadProfile(x.decode(FNENC))
                if not (prof is None):
                    self.ProfileListStore.append(
                        (prof.Family, prof.GetModel(), prof.Description,
                         prof.FileName))
            except IOError as e:
                self.Message(gtk.MESSAGE_WARNING,
                             _("Failed to load profile %(fn)s:\n%(msg)s") %
                             {"fn": x, "msg": str(e.strerror)})
            except ValueError as e:
                self.Message(gtk.MESSAGE_WARNING,
                             _("Failed to load profile %(fn)s:\n%(msg)s") %
                             {"fn": x, "msg": e})

        # Re-select previously selected profile
        if sel:
            i = model.get_iter_first()
            while i:
                if model[i][2] == sel:
                    self.ProfileList.get_selection().select_iter(i)
                    break
                i = model.iter_next(i)

    def FillFamilies(self, lbox):
        store = gtk.ListStore(str)
        cell = gtk.CellRendererText()
        lbox.pack_start(cell, True)
        lbox.add_attribute(cell, 'text', 0)

        for x in infineon.Families:
            store.append([x.Family])

        lbox.set_model(store)
        lbox.set_active(0)

    def FillGroups(self, lbox):
        store = gtk.ListStore(str, str, str)
        cell = gtk.CellRendererText()
        lbox.pack_start(cell, True)
        lbox.add_attribute(cell, 'text', 0)

        for x in infineon.Families:
            if (x.Capabilities & infineon.CAP_DOWNLOAD) == 0:
                continue

            model = None
            model_groups = {}
            for y in x.ModelDesc:
                model = y["ControllerModel"]
                if model_groups.get(model) is None:
                    model_groups[model] = []
                model_groups[model].append(y["Name"])

            wildcards = []
            for y in model_groups.values():
                if len(y) > 1:
                    wc = self.MakeWildCard(y)
                    for w in wc:
                        if not (w in wildcards):
                            wildcards.append(w)

            for w in wildcards:
                if w == "*":
                    store.append([x.Family, x.Family, None])
                else:
                    store.append([x.Family + ", " + w, x.Family, w])
            if len(wildcards) == 0:
                store.append([x.Family, x.Family, None])

        lbox.set_model(store)
        lbox.set_active(0)

    def MakeWildCard(self, arr):
        res = []
        max_len = 0
        for x in arr:
            x = x.split('/')
            res.append(x)
            if len(x) > max_len:
                max_len = len(x)

        for n in range(0, max_len):
            if n >= len(res[0]):
                break

            val = res[0][n]
            eq = True
            for y in res:
                if (n >= len(y)) or (y[n] != val):
                    eq = False
                    break
            if eq:
                for y in res:
                    y[n] = "*"

        for n in range(len(res)):
            res[n] = "/".join(res[n])
        return res

    def SelectFamily(self, Family):
        store = self.ControllerFamily.get_model()
        for i in range(len(store)):
            if store[i][0] == Family:
                self.ControllerFamily.set_active(i)
                break

    def SelectedFamily(self, cbox):
        store = cbox.get_model()
        famnam = store[cbox.get_active()][0]
        for x in infineon.Families:
            if famnam == x.Family:
                return x
        return None

    def SelectedGroup(self, cbox):
        store = cbox.get_model()
        n = cbox.get_active()
        fam = store[n][1]
        wc = store[n][2]
        for x in infineon.Families:
            if fam == x.Family:
                return x, wc
        return None, None

    def LoadProfile(self, fn):
        with open(fn, "r", encoding=FNENC) as f:
            l = f.readlines()
        prof = None
        for fam in infineon.Families:
            if fam.DetectFormat(l):
                prof = fam.CreateProfile(fn)
                break

        if prof is not None:
            prof.Load(fn, l)

        return prof

    def GetSelectedProfile(self):
        sel = self.ProfileList.get_selection().get_selected()[1]
        if not sel:
            self.SetStatus(_("No profile selected"))
            return None

        return self.ProfileListStore[sel][2]

    def LoadSelectedProfile(self):
        sel = self.ProfileList.get_selection().get_selected()[1]
        if not sel:
            self.SetStatus(_("No profile selected"))
            return None

        return self.LoadProfile(self.ProfileListStore[sel][3])

    # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

    def on_MainWindow_destroy(self, win):
        self.Dead = True
        self.UploadCancelled = True
        gtk.main_quit()

    def on_ButtonCancelUpload_clicked(self, but):
        self.UploadCancelled = True

    def on_ButtonApply_clicked(self, but):
        prof = self.LoadSelectedProfile()
        if prof is None:
            return

        serport = self.SerialPortsList.get_active_text()
        if not serport:
            self.SetStatus(_("No serial port selected"))
            return

        self.UploadCancelled = False
        self.SetStatus(_("Uploading settings to controller"))
        self.UserChoice.hide()
        self.UserHints.show()
        self.ProgressBar.show()
        self.ButtonCancelUpload.show()
        self.ButtonCancelUpload.grab_add()
        self.MainWindow.set_deletable(False)

        while gtk.events_pending():
            gtk.main_iteration()

        self.UserHints.set_label(_("""\
Applying profile: <b>%(prof)s</b>
Controller model: <b>%(ctrl)s</b>
Serial port: <b>%(port)s</b>

Please connect the controller to the programming cable which, in turn, \
must be connected to one of the computer's USB sockets. Once you're ready, \
press the button on the programming cable and hold it steadily for \
at least 10 seconds. You may release the button when this text is replaced \
back with a list of existing controller profiles.

If the controller programs only once (that is, when you're doing it second time, \
the message "Waiting for controller ready" stays forever and program won't react \
to the cable button) you will need to completely disconnect temporarily either \
the controller from the cable, or the cable from the USB port.\
""") % {"prof": prof.Description, "ctrl": prof.GetModel(), "port": serport})

        msg = None
        try:
            ok = prof.Upload(serport, self.UpdateProgress)
            if ok:
                self.SetStatus(_("Settings uploaded successfully"))
            else:
                self.SetStatus(_("Upload cancelled"))

        except Exception as e:
            msg = str(e)

        if msg is not None:
            self.SetStatus(_("Upload failed: %(msg)s") % {"msg": str(e)})

        self.MainWindow.set_deletable(True)
        self.ButtonCancelUpload.grab_remove()
        self.ButtonCancelUpload.hide()
        self.ProgressBar.hide()
        self.UserHints.hide()
        self.UserChoice.show()

    def on_ButtonEdit_clicked(self, but):
        prof = self.LoadSelectedProfile()
        if not (prof is None):
            self.EditProfile(prof)

    def on_ButtonCreate_clicked(self, but):
        self.CreateProfileName.set_text(_("New profile"))
        self.CreateProfileName.grab_focus()

        self.CreateProfileDialog.show()
        ok = self.CreateProfileDialog.run() == gtk.RESPONSE_APPLY
        self.CreateProfileDialog.hide()

        if ok:
            fam = self.SelectedFamily(self.CreateControllerFamily)
            nam = self.CreateProfileName.get_text().strip()
            prof = fam.CreateProfile(os.path.join(self.CONFIGDIR, nam))
            self.EditProfile(prof, self.GetSelectedProfile())

    def on_ButtonCopy_clicked(self, but):
        prof = self.LoadSelectedProfile()
        if prof is None:
            return

        prof.SetFileName(os.path.join(self.CONFIGDIR, _("New ") +
                        prof.Description + ".asv"), False)
        self.EditProfile(prof, self.GetSelectedProfile())

    def on_ButtonDelete_clicked(self, but):
        prof = self.LoadSelectedProfile()
        if prof is None:
            return

        d = gtk.MessageDialog(None,
                              gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL,
                              _("Are you sure you want to delete profile \"%s\"?") % prof.Description)
        rc = d.run()
        d.destroy()
        if rc == gtk.RESPONSE_OK:
            try:
                prof.Remove()
                self.LoadProfiles()
                self.SetStatus(_("Profile deleted"))
            except:
                self.Message(gtk.MESSAGE_ERROR,
                             _("Failed to remove profile file %(fn)s") %
                             {"fn": prof.FileName})
                self.SetStatus(_("Failed to delete profile"))

    def on_ButtonDownload_clicked(self, but):
        serport = self.SerialPortsList.get_active_text()
        if not serport:
            self.SetStatus(_("No serial port selected"))
            return

        self.DownloadProfileName.set_text(_("New profile"))
        self.DownloadProfileName.grab_focus()

        self.DownloadProfileDialog.show()
        ok = self.DownloadProfileDialog.run() == gtk.RESPONSE_APPLY
        self.DownloadProfileDialog.hide()

        if ok:
            fam, wc = self.SelectedGroup(self.DownloadControllerGroup)
            nam = self.DownloadProfileName.get_text().strip()
            prof = fam.CreateProfile(os.path.join(self.CONFIGDIR, nam))

            self.UploadCancelled = False
            self.SetStatus(_("Reading profile from controller"))
            self.UserChoice.hide()
            self.UserHints.show()
            self.ProgressBar.show()
            self.ButtonCancelUpload.show()
            self.ButtonCancelUpload.grab_add()
            self.MainWindow.set_deletable(False)

            while gtk.events_pending():
                gtk.main_iteration()

            self.UserHints.set_label(_("""\
Creating profile: <b>%(prof)s</b>
Controller family: <b>%(family)s</b>
Controller subgroup: <b>%(group)s</b>
Serial port: <b>%(port)s</b>

Trying to read controller profile data.

Not all controller types support reading.
""") % {"prof": prof.Description, "family": prof.Family, "port": serport,
                 "group": wc or _("all")})

            msg = None
            try:
                ok = prof.Download(serport, self.UpdateProgress, wc)
                if ok:
                    self.SetStatus(_("Settings downloaded successfully"))
                else:
                    self.SetStatus(_("Download cancelled"))

            except Exception as e:
                msg = str(e)

            self.MainWindow.set_deletable(True)
            self.ButtonCancelUpload.grab_remove()
            self.ButtonCancelUpload.hide()
            self.ProgressBar.hide()
            self.UserHints.hide()
            self.UserChoice.show()

            if msg is not None:
                self.SetStatus(_("Download failed: %(msg)s") % {"msg": str(e)})
            elif ok:
                self.EditProfile(prof, self.GetSelectedProfile())

    def on_ButtonAbout_clicked(self, but):
        self.AboutDialog.set_version(VERSION)
        self.AboutDialog.run()
        self.AboutDialog.hide()

    def on_ControllerFamily_changed(self, cb):
        if self.ActiveProfile is None:
            return

        fam = infineon.Families[cb.get_active()]
        if fam.Family == self.ActiveProfile.Family:
            return

        prof = fam.CreateProfile(self.ActiveProfile.FileName)
        prof.CopyParameters(self.ActiveProfile)
        self.ActiveProfile = prof

        self.ParamVBox.foreach(self.ClearChildren, self.ParamVBox)
        prof.FillParameters(self.ParamVBox)

    def on_UserHints_size_allocate(self, label, allocation):
        layout = label.get_layout()
        new_width = (allocation.width - label.get_layout_offsets()[0] * 2) * pango.SCALE
        if new_width != layout.get_width():
            layout.set_width(new_width)
