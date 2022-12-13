from PyQt6           import QtCore, QtGui, QtWidgets
from PyQt6.QtCore    import QEvent, QObject, pyqtSignal
from bscripts.tricks import QtPosition as pos, font_fitter, get_fontsize
from bscripts.tricks import highlight_style, make_image_into_blob
from bscripts.tricks import make_new_file_from_blob, md5_hash_string, random_rgb
from bscripts.tricks import shrink_label_to_text, style, tech as t, thread
import os
import time


class Trigger(QObject):
    event_highjack = pyqtSignal()

    def __init__(s, triggerwidget, fn, resize=False, move=False, mousebutton=False, close=None):
        super().__init__(triggerwidget)
        for enum in [k for k,v in {14:resize, 13:move, 19:close, 2:mousebutton}.items() if v]:
            s.eventtype = QEvent.type(QEvent(enum))
        s.master_fn = fn
        s._widget = triggerwidget
        s.widget.installEventFilter(s)
        if s.master_fn:
            s.event_highjack.connect(s.master_fn)

    @property
    def widget(s):
        return s._widget

    def eventFilter(s, widget, event) -> bool:
        if widget == s._widget and event.type() == s.eventtype:
            s.event_highjack.emit()
        return super().eventFilter(widget, event)

class GOD:
    def __init__(s,
            name=False,
            inherit_name=False,
            parent=False,
            main=False,
            signal=False,
            autoload=True,
            dieswith=None,
            *args,
            **kwargs
        ):
        s._define_parent(parent)
        s._define_name(name, inherit_name, parent)
        s._define_main(main)
        s._define_signal(signal)
        s._activation(autoload)
        s._dieswith(dieswith)
        super().__init__(*args, **kwargs)

    def _dieswith(s, dieswith):
        if dieswith:
            s._killfilter1 = Trigger(dieswith, close=True, fn=lambda: s.close())
            s._killfilter2 = Trigger(s, close=True, fn=lambda: s._killfilter1.event_highjack.disconnect())

    def _activation(s, autoload):
        if autoload and t.config(s.name):
            s.activated = True
        else:
            s.activated = False

    def activation_toggle(s, force=None):
        if type(force) == bool:
            s.activated = force
        elif s.activated:
            s.activated = False
        else:
            s.activated = True

    def _define_signal(s, signal):
        if signal == True:
            s.signal = t.signals()
        elif 'signal' in dir(signal):
            s.signal = signal.signal

    def _define_main(s, main):
        if main:
            s.main = main

    def _define_parent(s, parent):
        if parent:
            s.parent = parent
        elif 'parent' not in dir(s):
            s.parent = None

    def _define_name(s, name, inherit_name, parent):
        if name:
            s.name = name

        elif 'name' in dir(inherit_name):
            s.name = inherit_name.name

        elif inherit_name and 'name' in dir(parent):
            s.name = parent.name

        elif inherit_name and 'parent' in dir(s) and 'name' in dir(s.parent):
            s.name = s.parent.name

        else:
            s.name = md5_hash_string(random=True, under=True)

QTA = QtCore.Qt.AlignmentFlag
ALIGN = dict(center_y=QTA(0x0080), center_x=QTA(0x0004), left=QTA(0x0001), right=QTA(0x0002), top=QTA(0x0020), bottom=QTA(0x0040))
class LOOKS:
    def __init__(s, *args, **kwargs):
        s(**kwargs)
        s.show()

    def __call__(s,
            center=False,
            left=False,
            right=False,
            top=False,
            bottom=False,
            monospace=False,
            bold=False,
            qframebox=False,
            background=False,
            color=False,
            border=False,
            font=False,
            fontsize=False,
            construct=False,
            px=0,
            **kwargs
        ):
        kwgs = dict(background=background, color=color, border=border, font=font or fontsize, px=px, construct=construct)
        align = [ALIGN[k] for k,v in {'top': top, 'bottom': bottom, 'left': left, 'right': right}.items() if v]
        align.append(ALIGN['center_y']) if center and any(x for x in [left, right]) else None
        align.append(ALIGN['center_x']) if center and any(x for x in [top, bottom]) else None
        align.append(ALIGN['center_x']|ALIGN['center_y']) if center and not align else None
        s.setAlignment(align[0]) if len(align) == 1 else None
        s.setAlignment(align[0] | align[1]) if len(align) == 2 else None
        s.setAlignment(align[0] | align[1] | align[2]) if len(align) == 3 else None

        s.setFrameShape(QtWidgets.QFrame.Shape(1)) if qframebox else None
        font = QtGui.QFont("Monospace") if monospace else None
        font.setBold(True) if bold and font else None
        s.setFont(font) if monospace else None
        style(s, **kwgs) if any(True for k,v in kwgs.items() if v) else None

class Label(QtWidgets.QLabel, GOD, LOOKS):
    def __init__(s,
            place,
            *args,
            **kwargs
        ):
        super().__init__(place, *args, **kwargs)

    def set_ai_color(s, **kwargs):
        style(s, background=random_rgb(**kwargs))

class ImageDropper(Label):
    def __init__(s, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s.setAcceptDrops(True)

    def dragEnterEvent(s, ev):
        data = ev.mimeData().urls()
        ev.acceptProposedAction() if data else None

    def dropEvent(s, ev):
        if [x for x in ev.mimeData().urls()]:
            ev.accept()
            files = [x.path() for x in ev.mimeData().urls()]
            s.filesdropped([x for x in files if os.path.exists(x)], ev)

    def filesdropped(s, files, ev, *args):
        for i in files:
            blob = make_image_into_blob(i, width=s.width(), height=s.height())
            if blob:
                t.save_config('icon' + s.parent.path, blob)
                tmpfile = make_new_file_from_blob(blob)
                s.show_pixmap(tmpfile)
                break

    def show_pixmap(s, path):
        if os.path.exists(path):
            s.clear()
            pixmap = QtGui.QPixmap(path).scaled(s.size(), transformMode=QtCore.Qt.TransformationMode(1))
            s.setPixmap(pixmap)

class LineEdit(QtWidgets.QLineEdit, GOD, LOOKS):
    def __init__(s,
            place,
            qframebox=False,
            *args,
            **kwargs
        ):
        super().__init__(place, *args, **kwargs)

class HighlightLabel(Label):

    def __init__(s,
            place,
            mouse=True,
            signal=False,
            highlight_signal='_global',
            activated_on=None,
            activated_off=None,
            deactivated_on=None,
            deactivated_off=None,
            *args, **kwargs
        ):
        super().__init__(place, signal=False, *args, **kwargs)

        s.setMouseTracking(mouse)
        s.signal = t.signals(highlight_signal)
        s.signal.highlight.connect(s._highlight)

        for k,v in {
            'activated_on': activated_on,
            'activated_off': activated_off,
            'deactivated_on': deactivated_on,
            'deactivated_off': deactivated_off
            }.items():
            setattr(s, k, v) if v else highlight_style(s, 'globlahighlight', specific=k)

        style(s, **s.deactivated_on if s.activated else s.deactivated_off)

    def closeEvent(s, *args):
        try: s.signal.highlight.disconnect(s._highlight)
        except: pass

    def set_ai_color(s, **kwargs):
        deact_rgb_off = random_rgb(string=False, **kwargs)
        tmp = [deact_rgb_off[c] * 1.25 for c in range(len('RGB'))]
        deact_rgb_on = random_rgb(max_rgb_tuple=tmp, min_rgb_tuple=tmp, string=False)

        tmp = [deact_rgb_on[c] * 1.1 for c in range(len('RGB'))]
        act_rgb_off = random_rgb(max_rgb_tuple=tmp, min_rgb_tuple=tmp, string=False)
        tmp = [act_rgb_off[c] * 1.25 for c in range(len('RGB'))]
        act_rgb_on = random_rgb(max_rgb_tuple=tmp, min_rgb_tuple=tmp, string=False)

        for k,v in {
            'activated_on': act_rgb_on,
            'activated_off': act_rgb_off,
            'deactivated_on': deact_rgb_on,
            'deactivated_off': deact_rgb_off
            }.items():
            setattr(s, k, dict(background=random_rgb(min_rgb_tuple=v, max_rgb_tuple=v)))

    def _highlight(s, string):
        if string != s.name:
            if s.activated:
                style(s, **s.activated_off)
            else:
                style(s, **s.deactivated_off)
        else:
            if s.activated:
                style(s, **s.activated_on)
            else:
                style(s, **s.deactivated_on)

    def enterEvent(s, *args):
        try: s.signal.highlight.emit(s.name)
        except AttributeError: return

    def leaveEvent(s, *args):
        s._highlight('turn_me_black')

class TipLabel(Label):
    def __init__(s, place, background='rgba(0,0,0,0)', color='rgb(200,200,200)', x_margin=10, autohide=True, *args, **kwargs):
        super().__init__(place, background=background, color=color, *args, **kwargs)
        s._parent = place

        if 'tiplabel' not in dir(place):
            place.tiplabel = s

        if autohide:
            try: s._parent.textChanged.connect(s._text_changed)
            except AttributeError: pass

        fontsize = get_fontsize(s._parent)
        if fontsize:
            style(s, font=fontsize - 4)

        s._eventfilter_resize = Trigger(place, resize=True, fn=s._follow_parent)
        shrink_label_to_text(s, x_margin=x_margin) if s.text() else None
        s._follow_parent()

    def _text_changed(s, text):
        s.hide() if text else s.show()

    def _follow_parent(s):
        pos(s, height=s._parent, right=s._parent.width() - 1)

class HighlightTipLabel(HighlightLabel, TipLabel):
    def __init__(s, place, *args, **kwargs):
        super().__init__(place, *args, **kwargs)

 # <<======ABOVE:ME=======<{ [               OTHERS              ] ==============================<<
 # >>======================= [        MOVABLESCROLLWIDGET        ] }>============BELOW:ME========>>

class MovableScrollWidget(Label):
    def __init__(s, place, gap=0, toolplate={}, backplate={}, title={}, scrollarea={}, scroller={}, fortified=False, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        s.fortified = fortified
        s.place = place  # earlier s.parent wich conflicts if parent in kwargs
        s.gap = gap
        s.toolplate = s.ToolPlate(s, parent=s, **toolplate)
        s.title = s.Title(s.toolplate, parent=s, **title)
        s.backplate = s.BackPlate(s, parent=s, **backplate)
        s.scroller = s.ScrollThiney(place, parent=s, dieswith=s, **scroller)
        s.scrollarea = s.ScrollArea(s, **scrollarea)
        s.widgets = []
        s.toolplate.widgets = [s.title]
        s.steady = True
        s._resizeEvent = Trigger(s, resize=True, fn=s._resize_to_parent)

    def _resize_to_parent(s):
        if s.steady:
            s.toolplate.take_place()
            s.title.take_place()
            pos(s.backplate, width=s)
            s.scrollarea.take_place()

    def mousePressEvent(s, ev):
        s.old_position = ev.globalPosition()
        s.raise_()

    def mouseMoveEvent(s, ev):
        if s.fortified:
            return

        try: delta = ev.globalPosition() - s.old_position
        except AttributeError:
            s.old_position = ev.globalPosition()
            return

        s.move(s.pos().x() + int(delta.x()), s.pos().y() + int(delta.y()))
        s.old_position = ev.globalPosition()

    class ToolPlate(Label):
        def take_place(s):
            pos(s, height=max(x.geometry().bottom()+1 for x in s.parent.toolplate.widgets), width=s.parent)

    class Title(Label):
        def __init__(s, place, center=True, height=30, *args, **kwargs):
            super().__init__(place, center=center, *args, **kwargs)
            pos(s, height=height)

        def take_place(s):
            pos(s, width=s.parent.toolplate)

    class BackPlate(Label):
        def take_place(s):
            construct = style(s.parent.scrollarea, curious=dict)
            try: border = int("".join([x for x in construct['base']['border'] if x.isdigit()]))
            except (KeyError, TypeError): border = 0

            if s.parent.widgets:
                height = max(x.geometry().bottom()+1 for x in s.parent.widgets)
                pos(s, width=s.parent.scrollarea, height=height, sub=border*2)

            if s.parent.height() - s.parent.toolplate.height() > s.height():
                pos(s, height=s.parent.height() - s.parent.toolplate.height(), sub=border*2)

    class ScrollArea(QtWidgets.QScrollArea):
        def __init__(s, place, *args, **kwargs):
            super().__init__(place, *args, **kwargs)
            s.parent = place
            s.setWidget(s.parent.backplate)
            s.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy(1))
            s.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy(1))
            s.setFrameShape(QtWidgets.QFrame.Shape(0))
            s.setLineWidth(0)
            s.setStyleSheet('background-color:rgba(0,0,0,0);color:rgba(0,0,0,0)')
            s.verticalScrollBar().valueChanged.connect(s.parent.scroller.change_position)
            s.show()

        def take_place(s):
            w = s.parent.width()
            h = s.parent.height() - s.parent.toolplate.height()
            pos(s, size=[w, h], below=s.parent.toolplate)

    def expand_me(s, collapse=False, min_bottom=False, max_bottom=False):
        s.steady = False

        s.toolplate.take_place()
        s.title.take_place()

        if collapse:
            pos(s, height=s.toolplate)
            pos(s.backplate, height=0, width=s, below=s.toolplate)
            pos(s.scrollarea, height=0, width=s, below=s.toolplate)
            s.scroller.hide()
        else:
            if min_bottom:  # uses parent min_bottom isnt a number
                pos(s, reach=dict(bottom=s.place.height() if min_bottom == True else min_bottom))

            elif max_bottom and s.widgets:  # must a number
                bottom = max(x.geometry().bottom() for x in s.widgets) + s.toolplate.height() + s.geometry().top()
                pos(s, reach=dict(bottom=max_bottom if max_bottom < bottom else bottom), y_margin=1)

            elif s.widgets:
                floor =  s.geometry().top() + max(x.geometry().bottom()+1 for x in s.widgets)
                if floor > s.place.height():
                    pos(s, reach=dict(bottom=s.place.height()))
                else:
                    pos(s, height=max(x.geometry().bottom()+1 for x in s.widgets) + s.toolplate.height())
            else:
                pos(s, height=s.toolplate)

            s.organize_children() if s.widgets else None

        s.steady = True

    def organize_children(s):
        s.scrollarea.take_place()
        s.backplate.take_place()
        s.scroller.show_if_needed()
        s.everyone_add_gap()

    def everyone_add_gap(s):
        if s.gap:
            pos(s.scrollarea, below=s.toolplate, y_margin=s.gap)
            pos(s, height=s, add=s.gap)

    class ScrollThiney(Label):
        def __init__(s, place, background='GREEN', color='BLACK', border='black', px=1, after=True, *args, **kwargs):
            s.old_position, s.holding, s.scroller_offset = None, False, 0
            super().__init__(place, *args, **kwargs)
            s.after = after
            style(s, background=background, color=color, border=border, px=px)
            s.hide()

        def show_if_needed(s):
            floor =  max(x.geometry().bottom() for x in s.parent.widgets) + s.parent.toolplate.height() + s.parent.geometry().top()
            if floor > s.parent.place.height():

                if s.old_position == None:
                    pos(s, size=[7,20])
                    s._eventfilter1 = Trigger(s.parent, move=True, fn=s.follow_parent)
                    s._eventfilter2 = Trigger(s.parent, resize=True, fn=s.follow_parent)
                    s._eventfilter3 = Trigger(s.parent, mousebutton=True, fn=s.follow_parent)
                    s.old_position = False
                    s.follow_parent()

                s.show()
            else:
                s.hide()

        def change_position(s, ev):
            if not s.holding and s.parent.scrollarea.verticalScrollBar().maximum() and ev:  # ZeroDivisionError
                top = (s.parent.scrollarea.height() - s.height()) * (ev / s.parent.scrollarea.verticalScrollBar().maximum())
                pos(s, top=s.parent, move=[0,  s.parent.toolplate.height() + top])
                s.scroller_offset = s.geometry().top() - s.parent.geometry().top()
                s.raise_()

        def follow_parent(s, *args, **kwargs):
            if not s.old_position:
                pos(s, after=s.parent, move=[0, s.parent.toolplate.height()], x_margin=-s.width()-2 if not s.after else 0)
            else:
                pos(s, after=s.parent, top=s.parent, move=[0, s.scroller_offset], x_margin=-s.width()-2 if not s.after else 0)

            s.raise_()

        def mouseMoveEvent(s, ev: QtGui.QMouseEvent) -> None:
            if not s.old_position:
                s.old_position = ev.globalPosition()

            tmp = ev.globalPosition() - s.old_position
            y = s.pos().y() + QtCore.QPoint(int(tmp.x()), int(tmp.y())).y()

            top = s.parent.geometry().top() + s.parent.toolplate.height()
            bottom = s.parent.geometry().bottom() - s.height() + s.lineWidth()

            maximum = s.parent.scrollarea.verticalScrollBar().maximum()
            maxpix = s.parent.height() - s.parent.toolplate.height()

            pixels_process = y - top

            if not pixels_process:
                value = 0
            else:
                value = pixels_process / maxpix
                value = int(maximum * value)
                if value > maximum:
                    value = maximum

            s.parent.scrollarea.verticalScrollBar().setValue(value)

            if y >= top and y <= bottom:
                s.move(s.pos().x(), y)
                s.old_position = ev.globalPosition()

            s.scroller_offset = s.geometry().top() - s.parent.geometry().top()

        def mousePressEvent(s, ev: QtGui.QMouseEvent) -> None:
            s.holding = True
            s.old_position = ev.globalPosition()
            if ev.button() == 1:
                s.raise_()

        def mouseReleaseEvent(s, ev):
            s.holding = False

 # <<======ABOVE:ME=======<{ [         MOVABLESCROLLWIDGET       ] ==============================<<
 # >>======================= [              SLIDERS              ] }>============BELOW:ME========>>

class SliderWidget(Label):
    def __init__(
            s,
            place,
            different_states,
            slider={},
            slider_width=False,
            slider_width_factor=False,
            slider_shrink_factor=1,
            snap=True,
            *args, **kwargs
        ):
        """
        :param different_states: list with states (uses len(list) to calculte steps)
        :param slider_width: int (pixels width)
        :param slider_width_factor: float 0.25 (25% of s.width)
        :param slider_shrink: float (0.85 for slightly smaller slider than steps)
        """
        s.steady = False
        super().__init__(place, *args, **kwargs)
        s.slider_width_factor = slider_width_factor
        s.slider_width = slider_width
        s.different_states = different_states
        s.slider_shrink_factor = slider_shrink_factor
        s.slider_rail = s.SliderRail(place=s)
        s.slider = s.Slider(
            place=s,
            name=s.name,
            highlight_signal=md5_hash_string(),
            qframebox=True,
            center=True,
            snap=snap,
            parent=s,
            **slider,
        )
        s.slider.different_states = different_states
        s.slider.inrail = s.slider_rail.inrail
        s.steady = True

    class SliderRail(Label):
        def __init__(s, *args, **kwargs):
            super().__init__(*args, **kwargs)
            style(s, background='BLACK')
            s.inrail = Label(place=s)
            style(s.inrail, background='GRAY')

    def resizeEvent(s, a0: QtGui.QResizeEvent) -> None:
        if not s.steady:
            return

        elif s.slider_width_factor:
            width = s.width() / s.slider_width_factor
        elif s.slider_width:
            width = s.slider_width
        else:
            width = s.width() / len(s.different_states)

        pos(s.slider, height=s, width=width * s.slider_shrink_factor)
        w = s.width() - (s.slider.width() / 3)
        pos(s.slider_rail, height=3, top=s.height() / 2 - 1, width=w, left=s.slider.width()/6)
        s.slider.snap_widget(force=True)
        pos(s.slider_rail.inrail, left=1, top=1, width=s.slider.geometry().left(), height=1)

    def mouseMoveEvent(s, ev, *args):
        pass
    def mouseReleaseEvent(s, ev, *args):
        pass
    def mousePressEvent(s, ev: QtGui.QMouseEvent) -> None:
        """
        clicking the sliderrail will snap both save that
        state and snap the slider to that position
        """
        for i in range(len(s.different_states)):
            x1 = (s.width() / len(s.different_states)) * i
            x2 = x1 + (s.width() / len(s.different_states))
            if ev.pos().x() >= x1 and ev.pos().x() <= x2:
                s.slider.state = s.different_states[i]
                s.slider.snap_widget(force=True)
                t.save_config(s.slider.name, s.slider.state)
                break

    class Slider(HighlightLabel):
        def __init__(s, snap=True, *args, **kwargs):
            s.hold = False
            s.snap = snap
            super().__init__(*args, **kwargs)

            rv = t.config(s.name, raw=True)
            if rv and rv['value'] != None:
                s.state = rv['value']
            else:
                s.state = s.parent.different_states[0]

        def change_text(s):
            pass

        def snap_widget(s, force=False):
            """
            will adjust the slider so it fits right over the right state
            :param force: overrides non-snapping slider (used for preset)
            """
            if not s.snap and not force:
                return

            if s.state == s.different_states[0]:
                pos(s, left=0)
            elif s.state == s.different_states[-1]:
                pos(s, right=s.parent.width() - s.lineWidth())
            else:
                for count, i in enumerate(s.different_states):
                    if s.state == i:
                        each = s.parent.width() / len(s.different_states)
                        x1 = each * count
                        x2 = x1 + each
                        if s.width() < each:
                            pos(s, center=[x1, x2])
                        else:
                            side = (s.width() - each) / 2
                            pos(s, left=x1 - side)
                            if s.geometry().left() < 0:
                                pos(s, left=0)
                            elif s.geometry().right() > s.parent.width():
                                pos(s, right=s.parent.width() - s.lineWidth())
                        break

            pos(s.inrail, width=s.geometry().left())

        def save_state(s):
            """
            if slider is smaller than each state, state is the one that its touches the most (bleed)
            if slider is larger than each state, state is based on what the left side touches
            (s.parent.width() - s.width() since the left side can only reach parent minus self)
            :return:
            """
            each = s.parent.width() / len(s.different_states)
            if s.width() < each:
                for i in range(len(s.different_states)):
                    x1 = each * i
                    x2 = x1 + each
                    bleed = (s.width() * 0.5) + 1
                    if s.geometry().left() >= x1 - bleed and s.geometry().right() <= x2 + bleed:
                        s.state = s.different_states[i]
                        break
            else:
                each = (s.parent.width() - s.width()) / len(s.different_states)
                for i in range(len(s.different_states)):
                    x1 = each * i
                    x2 = x1 + each

                    if s.geometry().left() > x2:
                        continue

                    s.state = s.different_states[i]
                    break

        def mouseReleaseEvent(s, ev: QtGui.QMouseEvent) -> None:
            s.save_state()
            s.snap_widget()
            s.change_text()
            t.save_config(s.name, s.state)
            s.hold = False

        def mouseMoveEvent(s, ev: QtGui.QMouseEvent) -> None:
            if not s.hold:
                s.signal.highlight.emit(s.name)
                return

            delta = ev.globalPosition() - s.old_position

            if s.pos().x() + int(delta.x()) + s.width() > s.parent.width():
                s.move(s.parent.width() - s.width(), 0)

            elif s.pos().x() + int(delta.x()) < 0:
                s.move(s.pos().x() + 0, 0)

            else:
                s.move(s.pos().x() + int(delta.x()), 0)

            pos(s.inrail, width=s.geometry().left() - s.width() / 6)
            s.old_position = ev.globalPosition()

            s.save_state()
            s.change_text()

        def mousePressEvent(s, ev: QtGui.QMouseEvent) -> None:
            s.hold = True
            s.old_position = ev.globalPosition()

 # <<======ABOVE:ME=======<{ [               SLIDERS             ] ==============================<<
 # >>======================= [            SPAWNSLIDERS           ] }>============BELOW:ME========>>



class SpawnSliderRail(Label):
    def __init__(s, place, spawnslider=dict(background='ORANGE', qframebox=True, color='BLACK', center=True, fontsize=7), *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        s.pressed = False
        s.thingey = s.SpawnSlider(s, parent=s, **spawnslider)
        pos(s.thingey, center=[0,s.width()])
    def mousePressEvent(s, ev):
        s.pressed = ev.pos().x()
        s.grab_child(ev)
    def mouseReleaseEvent(s, ev):
        s.pressed = False
        s.thingey.left_press = False
        s.thingey.right_press = False
    def mouseMoveEvent(s, ev):
        if not s.pressed:
            return
        s.grab_child(ev)
    def grab_child(s, ev):
        s.thingey.spawn_thingey(ev.pos().x())
        s.thingey.visuals()
    def get_beyond_preyond(s):
        preyond = s.thingey.left_beyond.activated if 'left_beyond' in dir(s.thingey) else False
        beyond = s.thingey.right_beyond.activated if 'right_beyond' in dir(s.thingey) else False
        return preyond, beyond
    def get_small_large(s):
        return s.thingey.small, s.thingey.large
    def get_slider_data(s):
        preyond, beyond = s.get_beyond_preyond()
        small, large = s.get_small_large()
        return small, large, preyond, beyond

    class SpawnSlider(Label):
        def __init__(s, place, title=False, min_width=10, steps=None, show_beyond=True, left_zero_lock=False, *args, **kwargs):
            """
            :param left_zero_lock, locks the left end of the slider, moving not possible, only resize to the right possible
            """
            super().__init__(place, *args, **kwargs)
            s.show_beyond = show_beyond
            s.left_zero_lock = left_zero_lock
            s.left_press = False
            s.right_press = False
            s.title = title
            s.min_width = min_width
            s.steps = len(steps) if steps else 21
            s.steps_translate = {count:v for count, v in enumerate(steps or [x for x in range(s.steps)])}
            s.incapacitate_thingey()
            Trigger(s.parent, resize=True, fn=lambda: pos(s, height=s.parent))

        def incapacitate_thingey(s):
            s.small = None
            s.large = None
            s.setText('')
            s.title.setText('') if s.title else None
            pos(s, width=0)

        def mousePressEvent(s, ev):
            if ev.button().value == 2:
                s.incapacitate_thingey()
                return
            s.old_position = ev.globalPosition()

            handle = s.width() / 10 if s.width() / 10 > s.min_width / 3 else s.min_width / 3

            if s.left_zero_lock or ev.pos().x() >= s.width() - handle:
                s.right_press = True
                s.left_press = False
            elif ev.pos().x() <= handle and s.geometry().left() >= 0:
                s.left_press = True
                s.right_press = False
            else:
                s.left_press = False
                s.right_press = False

        def mouseReleaseEvent(s, ev):
            if s.width() < s.min_width:
                s.incapacitate_thingey()

        def mouseMoveEvent(s, ev):
            if s.right_press or s.left_press:
                s.resize_thingey(ev.pos().x())

            elif 'old_position' in dir(s):
                delta = ev.globalPosition() - s.old_position
                s.move(s.pos().x() + int(delta.x()), s.pos().y())

            s.old_position = ev.globalPosition()
            s.visuals()

        def visuals(s):
            s.thing_inside_parent()
            s.gather_values()
            s.show_beyond_visualization()

        def spawn_thingey(s, x):
            step = s.parent.width() / s.steps if s.parent.width() / s.steps >= s.min_width else s.min_width

            if s.left_zero_lock:
                w = max(step, s.parent.width()/4, x)
                w = s.parent.width() if w > s.parent.width() else w
                pos(s, left=0, width=w)
            elif s.width() < s.min_width:
                pos(s, left=x-(step / 2), width=max(step, s.parent.width()/4))
            else:
                pos(s, left=x-(s.width()/2))

        def resize_thingey(s, x):
            if s.right_press:
                reach = x+s.geometry().left() if x+s.geometry().left() > 0 else 0
                pos(s, reach=dict(right=reach if reach <= s.parent.width() else s.parent.width()))
            elif s.left_press:
                reach = x+s.geometry().left() if x+s.geometry().left() <= s.parent.width() else s.parent.width()
                pos(s, reach=dict(left=reach if reach >= 0 else 0))
            s.spawn_thingey(x)

        def thing_inside_parent(s):
            pos(s, right=s.parent.width()+1) if s.geometry().right() > s.parent.width()-1 else None
            pos(s, left=0) if s.geometry().left() < 0 else None

        def gather_values(s):
            step = s.parent.width() / s.steps
            left = s.geometry().left()
            right = s.geometry().right() if s.geometry().right() <= s.parent.width() else s.parent.width()

            c = [{'X1': x*step, 'X2': (x*step)+step, 'value': x, 'touch': False} for x in range(0, s.steps)]
            for dd in c:

                if left + (step * 0.43) >= dd['X1'] and left + (step * 0.43) <= dd['X2']:
                    dd['touch'] = True
                if right - (step * 0.43) >= dd['X1'] and right - (step * 0.43) <= dd['X2']:
                    dd['touch'] = True

            if [x['value'] for x in c if x['touch']]:
                small = min([x['value'] for x in c if x['touch']])
                large = max([x['value'] for x in c if x['touch']])
                s.small, s.large = s.steps_translate[small], s.steps_translate[large]
                s.show_status(s.small, s.large)
            else:
                s.small, s.large = None, None
                s.setText('')
                s.title.setText('') if s.title else None

        def show_status(s, small, large):
            if small == large:
                s.setText(str(small))
                s.title.setText(f"EXACTLY: {str(small)}") if s.title else None
            else:
                s.setText(f"{str(small)} - {str(large)}")
                s.title.setText(f"RANGE: {str(small)} - {str(large)}") if s.title else None

            font_fitter(s, shorten=False, maxsize=20, minsize=6)

        def show_beyond_visualization(s):
            if s.show_beyond:

                for d in [
                    {'name': 'right_beyond', 'kwgs': dict(height=s, width=3, right=s.width()+1), 'cond': s.geometry().right()+1 >= s.parent.width()},
                    {'name': 'left_beyond', 'kwgs': dict(left=0, height=s, width=3), 'cond': s.geometry().left() <= 0},]:

                    if d['name'] not in dir(s):
                        setattr(s, d['name'], Label(s, background='green', color='BLACK', qframebox=True))
                        getattr(s, d['name']).hide()
                        continue

                    label = getattr(s, d['name'])
                    label.activation_toggle(force=d['cond'])

                    if d['cond']:
                        pos(label, **d['kwgs'])
                        label.show()
                    else:
                        label.hide()

class StatusBar(Label):
    def __init__(s, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s.jobs = []
        s.queue = []
        s.freq = 0.3
        s.dot_change = True

    def recieve_message(s, message):
        if not s.queue or not s.jobs:
            s.queue.append(message)
            s.bot()
        else:
            s.queue.append(message)

    def adder(s):
        for count in range(len(s.queue) - 1, -1, -1):
            job = dict(text="", priority=5, duration=5, delay=0, irrelevant=5, urgent=0)
            [job.update({x: s.queue[count][x]}) for x in list(job.keys()) if x in s.queue[count]]
            job['start_time'] = s.now + job['delay'] - 0.01  # unstrict and lazy solution
            job['end_time'] = job['start_time'] + job['irrelevant']
            job['started'] = False
            job['urgent'] = 1 if job['urgent'] else 0
            s.jobs.append(job)
            s.queue.pop(count)

    def sorter(s):
        s.jobs.sort(key=lambda x: x['start_time'])
        s.jobs.sort(key=lambda x: x['urgent'], reverse=True)
        s.jobs.sort(key=lambda x: x['priority'])

    def clearer(s):
        s.jobs = [x for x in s.jobs if x['started'] or x['end_time'] > s.now]
        showing = s.current()
        if showing and showing['end_time'] < s.now:
            s.jobs = [x for x in s.jobs if not x['started']]
            s.setText('')

    def current(s):
        showing = [x for x in s.jobs if x['started']]
        return showing[0] if showing else False

    def change(s, text):
        if s.dot_change and '...' not in text:
            s.setText('...')
            thread(dummy=0.15, master_fn=lambda: s.setText(text), name=s.name)
        else:
            s.setText(text)

    def bot(s):
        s.now = time.time()
        s.adder()
        s.clearer()
        s.sorter()
        showing = s.current()

        for i in [x for x in s.jobs if not x['started'] and x['start_time'] < s.now]:

            if not showing:
                i['started'] = s.now
                s.change(i['text'])
                break

            elif showing and i['urgent'] and i['priority'] < showing['priority']:
                s.jobs = [x for x in s.jobs if not x['started']]
                i['started'] = s.now
                s.change(i['text'])
                break

        thread(lambda: time.sleep(s.freq), master_fn=s.bot, name=s.name) if s.jobs or s.queue else s.setText('')

