import sublime
import sublime_plugin
import datetime
import re
import os
import logging
import getpass
import OrgExtended.asettings as sets
import OrgExtended.pymitter as evt
import OrgExtended.orgextension as ext
import OrgExtended.orgparse.date as orgdate

log = logging.getLogger(__name__)

# I think I will model this feature after org-roam dailies.
# olBc has not really gotten back to me on the subject and I think
# dailies makes a lot of sense.

def dayPageGetPath():
    dpPath = sets.Get("dayPagePath",None)
    if(dpPath == None):
        sublime.status_message("Day Page error. dayPagePath setting is not set!")
        log.error(" Cannot create day page without dayPathPath in configuration")
        return None
    os.makedirs(dpPath, exist_ok=True)
    return dpPath

def dayPageGetDateString(dt):
    formatStr = sets.Get("dayPageNameFormat","%a_%Y_%m_%d")
    return dt.strftime(formatStr)

def dayPageFilenameToDateTime(view):
    filename = view.file_name()
    if(not filename):
        return None
    formatStr = sets.Get("dayPageNameFormat","%a_%Y_%m_%d")
    filename = os.path.splitext(os.path.basename(filename))[0]
    return datetime.datetime.strptime(filename,formatStr)

def dayPageGetName(dt):
    return os.path.join(dayPageGetPath(),dayPageGetDateString(dt) + ".org")


def OnLoaded(view,dt):
    snippet  = sets.Get("dayPageSnippet","dayPageSnippet")
    snipName = ext.find_extension_file('orgsnippets',snippet,'.sublime-snippet')
    if(snipName == None):
        log.error(" Could not locate snippet file: " + str(snippet) + ".sublime-snippet using default")
        snipName = ext.find_extension_file('orgsnippets','dayPageSnippet.sublime-snippet')
    # NeoVintageous users probably prefern not to have to hit insert when editing things.
    view.run_command('_enter_insert_mode', {"count": 1, "mode": "mode_internal_normal"})
    now  = dt
    inow = orgdate.OrgDate.format_date(now, False)
    anow = orgdate.OrgDate.format_date(now, True)
    ai = view.settings().get('auto_indent')
    view.settings().set('auto_indent',False)
    # "Packages/OrgExtended/orgsnippets/"+snippet+".sublime-snippet"
    # OTHER VARIABLES:
    # TM_FULLNAME - Users full name
    # TM_FILENAME - File name of the file being edited
    # TM_CURRENT_WORD - Word under cursor when snippet was triggered
    # TM_SELECTED_TEXT - Selected text when snippet was triggered
    # TM_CURRENT_LINE - Line of snippet when snippet was triggered
    #insert_snippet {"name": "Packages/OrgExtended/orgsnippets/page.sublime-snippet"}
    view.run_command("insert_snippet",
        { "name" : snipName
        , "ORG_INACTIVE_DATE": inow
        , "ORG_ACTIVE_DATE":   anow
        , "ORG_DATE":          str(dt.date().today())
        , "ORG_TIME":          dt.strftime("%H:%M:%S")
        , "ORG_CLIPBOARD":     sublime.get_clipboard()
        , "ORG_SELECTION":     view.substr(view.sel()[0])
        , "ORG_LINENUM":       str(view.curRow())
        , "ORG_FILENAME":      dayPageGetDateString(dt)
        , "ORG_AUTHOR":        getpass.getuser()
        })
    view.settings().set('auto_indent',ai)

def LoadedCheck(view,dt):
    if(view.is_loading()):
        sublime.set_timeout(lambda: LoadedCheck(view,dt),1)
    else:
        OnLoaded(view,dt)

def dayPageInsertSnippet(view,dt):
    window   = view.window()
    window.focus_view(view)
    LoadedCheck(view,dt)

def dayPageCreateOrOpen(dt):
    dpPath      = dayPageGetName(dt)
    dateString  = dayPageGetDateString(dt)
    didCreate   = False
    if(not os.path.exists(dpPath)):
        with open(dpPath,"w") as f:
            f.write("")
            didCreate = True
    tview = sublime.active_window().open_file(dpPath, sublime.ENCODED_POSITION)
    if(didCreate):
        dayPageInsertSnippet(tview,dt)

class OrgDayPagePreviousCommand(sublime_plugin.TextCommand):
    def OnDone(self):
        evt.EmitIf(self.onDone)

    def run(self, edit, onDone=None):
        self.edit   = edit
        self.onDone = onDone
        self.dt     = datetime.datetime.now()
        dt          = dayPageFilenameToDateTime(self.view)
        maxScan     = 90
        for i in range(maxScan):
            dt = dt - datetime.timedelta(days=1)
            if(sets.Get("dayPageCreateOldPages",False)):
                dayPageCreateOrOpen(dt)
                break
            else:
                fn = dayPageGetName(dt)
                if(os.path.exists(fn)):
                    tview = sublime.active_window().open_file(fn, sublime.ENCODED_POSITION)
                    sublime.active_window().focus_view(tview)
                    break
                else:
                    #log.warning("Day page does not exist: " + fn)
                    pass

class OrgDayPageNextCommand(sublime_plugin.TextCommand):
    def OnDone(self):
        evt.EmitIf(self.onDone)

    def run(self, edit, onDone=None):
        self.edit   = edit
        self.onDone = onDone
        self.now    = datetime.datetime.now()
        dt          = dayPageFilenameToDateTime(self.view)
        maxScan     = 90
        for i in range(maxScan):
            dt = dt + datetime.timedelta(days=1)
            if(dt.date() < self.now.date()):
                fn = dayPageGetName(dt)
                if(os.path.exists(fn)):
                    tview = sublime.active_window().open_file(fn, sublime.ENCODED_POSITION)
                    sublime.active_window().focus_view(tview)
                    break
                else:
                    #log.warning("Day page does not exist: " + fn)
                    pass
            elif(dt.date() == self.now.date()):
                dayPageCreateOrOpen(dt)
                break
            else:
                fn = dayPageGetName(dt)
                log.error(" Create day page in the future? " + fn)
                break


class OrgDayPageCreateCommand(sublime_plugin.TextCommand):
    def OnDone(self):
        evt.EmitIf(self.onDone)

    def run(self, edit, onDone=None):
        self.edit   = edit
        self.onDone = onDone
        self.dt     = datetime.datetime.now()
        dayPageCreateOrOpen(self.dt)
        self.OnDone()

