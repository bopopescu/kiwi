#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2006 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Johan Dahlin <jdahlin@async.com.br>
#

"""Widget for displaying a list of objects"""

import gtk
from gtk import gdk, keysyms

from kiwi.utils import gsignal
from kiwi.ui.widgets.entry import Entry

class _ComboEntryPopup(gtk.Window):
    gsignal('text-selected', str)
    def __init__(self, comboentry):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.add_events(gdk.BUTTON_PRESS_MASK)
        self.connect('key-press-event', self._on__key_press_event)
        self.connect('button-press-event', self._on__button_press_event)
        self._comboentry = comboentry

        # Number of visible rows in the popup window, sensible
        # default value from other toolkits
        self._visible_rows = 10
        self._initial_text = None

        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        self.add(frame)
        frame.show()

        vbox = gtk.VBox()
        frame.add(vbox)
        vbox.show()

        self._sw = gtk.ScrolledWindow()
        self._sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        vbox.pack_start(self._sw)
        self._sw.show()

        self._model = gtk.ListStore(str)
        self._treeview = gtk.TreeView(self._model)
        self._treeview.set_enable_search(False)
        self._treeview.connect('motion-notify-event',
                               self._on_treeview__motion_notify_event)
        self._treeview.connect('button-release-event',
                               self._on_treeview__button_release_event)
        self._treeview.add_events(gdk.BUTTON_PRESS_MASK)
        self._selection = self._treeview.get_selection()
        self._selection.set_mode(gtk.SELECTION_BROWSE)
        self._treeview.append_column(
            gtk.TreeViewColumn('Foo', gtk.CellRendererText(),
                               text=0))
        self._treeview.set_headers_visible(False)
        self._sw.add(self._treeview)
        self._treeview.show()

        self._label = gtk.Label()
        vbox.pack_start(self._label, False, False)
        self._label.show()

        self.set_resizable(False)
        self.set_screen(comboentry.get_screen())

    def popup(self, text=None):
        """
        Shows the list of options. And optionally selects an item
        @param text: text to select
        """
        combo = self._comboentry
        if not (combo.flags() & gtk.REALIZED):
            return

        treeview = self._treeview
        if treeview.flags() & gtk.MAPPED:
            return
        toplevel = combo.get_toplevel()
        if isinstance(toplevel, gtk.Window) and toplevel.group:
            toplevel.group.add_window(self)

        x, y, width, height = self._get_position()
        self.set_size_request(width, height)
        self.move(x, y)
        self.show_all()

        treeview.set_hover_expand(True)
        selection = treeview.get_selection()
        if text:
            for row in treeview.get_model():
                if text in row:
                    selection.select_iter(row.iter)
                    treeview.scroll_to_cell(row.path, use_align=True,
                                            row_align=0.5)
                    treeview.set_cursor(row.path)
                    break
        self.grab_focus()

        if not (self._treeview.flags() & gtk.HAS_FOCUS):
            self._treeview.grab_focus()

        if not self._popup_grab_window():
            self.hide()
            return

        self.grab_add()

    def popdown(self):
        combo = self._comboentry
        if not (combo.flags() & gtk.REALIZED):
            return

        self.grab_remove()
        self.hide_all()

    def set_label_text(self, text):
        self._label.set_text(text)

    def set_model(self, model):
        self._treeview.set_model(model)
        self._model = model

    # Callbacks

    def _on__key_press_event(self, window, event):
        """
        Mimics Combobox behavior

        Escape or Alt+Up: Close
        Enter, Return or Space: Select
        """

        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()
        if (keyval == keysyms.Escape or
            ((keyval == keysyms.Up or keyval == keysyms.KP_Up) and
             state == gdk.MOD1_MASK)):
            self.popdown()
            return True
        elif keyval == keysyms.Tab:
            self.popdown()
            # XXX: private member of comboentry
            self._comboentry._button.grab_focus()
            return True
        elif (keyval == keysyms.Return or
              keyval == keysyms.space or
              keyval == keysyms.KP_Enter or
              keyval == keysyms.KP_Space):
            model, treeiter = self._selection.get_selected()
            self.emit('text-selected', model[treeiter][0])
            return True

        return False

    def _on__button_press_event(self, window, event):
        # If we're clicking outside of the window
        # close the popup
        if (event.window != self.window or
            (tuple(self.allocation.intersect(
                   gdk.Rectangle(x=int(event.x), y=int(event.y),
                                 width=1, height=1)))) == (0, 0, 0, 0)):
            self.popdown()

    def _on_treeview__motion_notify_event(self, treeview, event):
        retval = treeview.get_path_at_pos(int(event.x),
                                          int(event.y))
        if not retval:
            return
        path, column, x, y = retval
        self._selection.select_path(path)
        self._treeview.set_cursor(path)

    def _on_treeview__button_release_event(self, treeview, event):
        retval = treeview.get_path_at_pos(int(event.x),
                                          int(event.y))
        if not retval:
            return
        path, column, x, y = retval

        model = treeview.get_model()
        self.emit('text-selected', model[path][0])

    def _popup_grab_window(self):
        activate_time = 0L
        if gdk.pointer_grab(self.window, True,
                            (gdk.BUTTON_PRESS_MASK |
                             gdk.BUTTON_RELEASE_MASK |
                             gdk.POINTER_MOTION_MASK),
                             None, None, activate_time) == 0:
            if gdk.keyboard_grab(self.window, True, activate_time) == 0:
                return True
            else:
                self.window.get_display().pointer_ungrab(activate_time);
                return False
        return False

    def _get_position(self):
        treeview = self._treeview
        treeview.realize()
        cell = treeview.get_cell_area(0, treeview.get_column(0))

        sample = self._comboentry.entry

        # We need to fetch the coordinates of the entry window
        # since comboentry itself does not have a window
        x, y = sample.window.get_origin()
        width = sample.allocation.width

        hpolicy = vpolicy = gtk.POLICY_NEVER
        self._sw.set_policy(hpolicy, vpolicy)

        pwidth = self.size_request()[0]
        if pwidth > width:
            self._sw.set_policy(gtk.POLICY_ALWAYS, vpolicy)
            pwidth, pheight = self.size_request()

        rows = len(self._model)
        if rows > self._visible_rows:
            rows = self._visible_rows
            self._sw.set_policy(hpolicy, gtk.POLICY_ALWAYS)

        # This needs some quite serious improvements
        focus_padding = treeview.style_get_property('focus-line-width') * 2
        height = (cell.height *
                  (rows + focus_padding) -
                  (2 + focus_padding))

        screen = self._comboentry.get_screen()
        monitor_num = screen.get_monitor_at_window(sample.window)
        monitor = screen.get_monitor_geometry(monitor_num)

        if x < monitor.x:
            x = monitor.x
        elif x + width > monitor.x + monitor.width:
            x = monitor.x + monitor.width - width

        if y + sample.allocation.height + height <= monitor.y + monitor.height:
            y += sample.allocation.height
        elif y - height >= monitor.y:
            y -= height
        elif (monitor.y + monitor.height - (y + sample.allocation.height) >
              y - monitor.y):
            y += sample.allocation.height
            height = monitor.y + monitor.height - y
        else :
            height = y - monitor.y
            y = monitor.y

        # Use half of the available screen space
        max_height = monitor.height / 2
        if height > max_height:
            height = int(max_height)

        return x, y, width, height

    def get_selected_iter(self):
        return self._selection.get_selected()[1]

    def set_selected_iter(self, iter):
        self._selection.select_iter(iter)

class ComboEntry(gtk.HBox):
    gsignal('changed')
    def __init__(self):
        gtk.HBox.__init__(self)

        self.entry = Entry()
        self.entry.connect('scroll-event',
                           self._on_entry__scroll_event)
        self.entry.connect('key-press-event',
                           self._on_entry__key_press_event)
        self.pack_start(self.entry, True, True)

        self._button = gtk.ToggleButton()
        self._button.connect('scroll-event',
                             self._on_entry__scroll_event)
        self._button.set_focus_on_click(False)
        self._button.connect('toggled', self._on_button__toggled)
        self._popping_down = False
        self.pack_end(self._button, False, False)

        arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_NONE)
        arrow.show()
        self._button.add(arrow)

        self._popup = _ComboEntryPopup(self)
        self._popup.set_size_request(-1, 24)
        self._popup.connect('text-selected', self._on_popup__text_selected)
        self._popup.connect('hide', self._on_popup__hide)

        self.set_model(self.entry.get_completion().get_model())

    # Callbacks

    def _on_entry__scroll_event(self, entry, event):
        model = self.get_model()
        curr = model[self._popup.get_selected_iter()].path[0]
        # Scroll up, select the previous item
        if event.direction == gdk.SCROLL_UP:
            curr -= 1
            if curr >= 0:
                self.set_active_iter(model[curr].iter)
        # Scroll down, select the next item
        elif event.direction == gdk.SCROLL_DOWN:
            curr += 1
            if curr < len(model):
                self.set_active_iter(model[curr].iter)

    def _on_entry__key_press_event(self, entry, event):
        """
        Mimics Combobox behavior

        Alt+Down: Open popup
        """
        keyval, state = event.keyval, event.state
        state &= gtk.accelerator_get_default_mod_mask()
        if ((keyval == keysyms.Down or keyval == keysyms.KP_Down) and
            state == gdk.MOD1_MASK):
            self.popup()
            return True

    def _on_popup__hide(self, popup):
        self._popping_down = True
        self._button.set_active(False)
        self._popping_down = False

    def _on_popup__text_selected(self, popup, text):
        self.entry.set_text(text)
        popup.popdown()
        self.entry.grab_focus()
        self.entry.set_position(len(self.entry.get_text()))

    def _on_button__toggled(self, button):
        if self._popping_down:
            return
        self.popup()

    # Private

    def _update(self):
        model = self._model
        if not len(model):
            return

        iter = self._popup.get_selected_iter()
        if not iter:
            iter = model[0].iter
        self._popup.set_selected_iter(iter)

    # Public API

    def set_model(self, model):
        """
        Set the tree model to model
        @param model: new model
        @type model: gtk.TreeModel
        """
        self._model = model
        self._popup.set_model(model)
        completion = self.entry.get_completion()
        completion.set_model(model)

        self._update()

    def get_model(self):
        """
        @returns: our model
        @rtype: gtk.TreeModel
        """
        return self._model

    def popup(self):
        """
        Hide the popup window
        """
        self._popup.popup(self.entry.get_text())

    def popdown(self):
        """
        Show the popup window
        """
        self._popup.popdown()

    def prefill(self, strs):
        """
        See L{kiwi.ui.entry}
        """
        self.entry.set_completion_strings(strs)

    def set_text(self, text):
        """
        @param text:
        """
        self.entry.set_text(text)
        self.emit('changed')

    def set_active_iter(self, iter):
        """
        @param iter: iter to select
        @type iter: gtk.TreeIter
        """
        self._popup.set_selected_iter(iter)
        self.set_text(self._model[iter][0])

    def get_active_iter(self):
        """
        @returns: the selected iter
        @rtype: gtk.TreeIter
        """
        return self._popup.get_selected_iter()

    # IconEntry

    def set_pixbuf(self, pixbuf):
        self.entry.set_pixbuf(pixbuf)

    def update_background(self, color):
        self.entry.update_background(color)

    def get_icon_window(self):
        return self.entry.get_icon_window()
