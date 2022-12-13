from PyQt6                    import QtCore, QtGui, QtWidgets
from bscripts.database_stuff  import *
from bscripts.tricks          import *
from bscripts.widgets         import *
import os, random, uuid

class Check:
    def complete(s):
        return all(x.number for x in s.slots)

    def number_taken(s, num):
        return [x.number for x in s.slots].count(num)

    def number_same_row(s, num, row):
        return [num == x.number and row == x.row for x in s.slots].count(True)

    def number_same_column(s, num, col):
        return [num == x.number and col == x.column for x in s.slots].count(True)

class GUISheet(Label, Check):
    def leaveEvent(s, a0: QtCore.QEvent) -> None:
        s.all_slots_off()

    def all_slots_off(s):
        for square in s.squares:
            for slot in square.slots:
                slot.activation_toggle(force=False) if slot.activated else None

        signal_highlight()

    def game_finished(s):
        if any(not x.complete() for x in s.squares):
            return False

        cols, rows = [], []
        for square in s.squares:
            rows.append(square.row) if square.row not in rows else None
            cols.append(square.column) if square.column not in cols else None
            for num in range(1, 10):
                if square.number_taken(num) != 1:
                    return False

        for col in cols:
            for row in rows:
                squares = [x for x in s.squares if x.row == col]
                for num in range(1, 10):
                    check = [x.number_same_column(num, row) for x in squares]
                    if sum(check) != 1:
                        return False

        for row in rows:
            for col in cols:
                squares = [x for x in s.squares if x.column == row]
                for num in range(1, 10):
                    check = [x.number_same_row(num, col) for x in squares]
                    if sum(check) != 1:
                        return False

                    #printout = ['-' if x < 1 else 'X' for x in check]
                    #print("".join(printout), 'NUMBER:', num, 'ROW:',row, 'COLUMN:', "".join([str(x+1) for x in range(3) if printout[x] == 'X']), check)
                #print('\n')

        for square in s.squares:
            style(square, background='green')
            for slot in square.slots:
                slot.fortified = True
                highlight_style(slot, name='slot_complete')
        signal_highlight()

class GUISquare(Label, Check):
    def expand_me(s):
        w = max(x.geometry().right() + 3 for x in s.slots)
        h = max(x.geometry().bottom() + 3 for x in s.slots)
        pos(s, size=[w, h], top=(s.row - 1) * h, left=(s.column - 1) * w)
        pos(s, move=[(s.column - 1) * 5, (s.row - 1) * 5])

    def change_background_color(s):
        bkg_color = random_rgb(variable=f"{s.row}{s.column}", string=True)
        style(s, background=bkg_color)

    def leaveEvent(s, a0: QtCore.QEvent) -> None:
        s.all_slots_off()

class GUISlot(HighlightLabel, Check):
    def position_me(s, size):
        kwgs = dict(left=(s.row - 1) * size, top=(s.column - 1) * size)
        pos(s, size=[size, size], **kwgs, move=[2, 2])

    def change_background_color(s):
        highlight_style(s, name='slot_fortified' if s.fortified else 'slot_free')

    def mouseReleaseEvent(s, ev: QtGui.QMouseEvent) -> None:
        if s.fortified:
            return
        elif ev.button().value > 2:
            s.number = 0
        else:
            s.number = (s.number + 1) if ev.button().value == 1 else (s.number - 1)
            s.number = 0 if s.number > 9 else s.number
            s.number = 9 if s.number < 0 else s.number

        s.setText(str(s.number or ''))
        s.missing.hide() if 'missing' in dir(s) else None
        s.show_missing_plate() if not s.number else None
        s.game_finished()

    def enterEvent(s, *args):
        s.all_slots_off()

        line_x = [x for x in s.squares if x.row == s.square.row]
        line_y = [x for x in s.squares if x.column == s.square.column]

        for square in line_x:
            for slot in square.slots:
                if slot.column == s.column:
                    slot.activation_toggle(force=True) if not slot.activated else None

        for square in line_y:
            for slot in square.slots:
                if slot.row == s.row:
                    slot.activation_toggle(force=True) if not slot.activated else None

        try: s.signal.highlight.emit(s.name)
        except AttributeError: return

    def leaveEvent(s, *args):
        s._highlight('turn_me_black')
        s.missing.hide() if 'missing' in dir(s) else None

    def mouseMoveEvent(s, ev: QtGui.QMouseEvent) -> None:
        s.show_missing_plate()

    def show_missing_plate(s):
        missing = []
        for i in range(1, 10):
            if s.square.number_taken(i) == 0:
                missing.append(i)

        if missing and not s.fortified and not s.number:
            try:
                s.missing.show()
            except AttributeError:
                kwgs = dict(background='transparent', color='gray', center=True, fontsize=8)
                s.missing = Label(s, **kwgs)
                pos(s.missing, inside=s)
                s.missing.nums = []
                for row in range(1, 4):
                    for col in range(1, 4):
                        thing = Label(s.missing, **kwgs)
                        pos(thing, size=[s.width() * 0.33, s.width() * 0.33])
                        find_free_horizontal_position(s.missing, thing, s.missing.nums)

            for count, i in enumerate(s.missing.nums):
                if s.main.setting_btn1.value == 2:
                    i.setText(str(count + 1) if count + 1 in missing else "")
                elif s.main.setting_btn1.value == 1:
                    i.setText(str(missing[0]) if missing else "")
                    missing.pop(0) if missing else None
                else:
                    i.setText('')
        else:
            s.missing.hide() if 'missing' in dir(s) else None

class Square(Check):
    def __init__(s, row, col):
        s.row = row
        s.column = col
        s.slots = []
        for row in range(1, 4):
            for col in range(1, 4):
                slot = lambda: None
                slot.row = row
                slot.column = col
                slot.number = None
                s.slots.append(slot)

class CustomSlider(SpawnSliderRail):
    class SpawnSlider(SpawnSliderRail.SpawnSlider):
        def show_status(s, small, large):
            s.setText(f"{str(large)}%")

        def spawn_thingey(s, x):
            step = s.parent.width() / s.steps if s.parent.width() / s.steps >= s.min_width else s.min_width
            w = max(step, s.parent.width()/8, x)
            w = s.parent.width() * 0.9 if w > s.parent.width() * 0.9 else w
            w = s.parent.width() * 0.1 if w < s.parent.width() * 0.1 else w
            pos(s, left=0, width=w)

        def incapacitate_thingey(s):
            pass

class SettingsBTN(HighlightLabel):
    def mouseReleaseEvent(s, ev: QtGui.QMouseEvent) -> None:
        s.value = (s.value + 1) if s.value < 3 else 1
        guide = {1:'STRAIGHT GUIDELINES', 2:'SPREAD GUIDELINES', 3:'NO GUIDELINES'}
        s.main.setWindowTitle(guide[s.value])

    def enterEvent(s, *args):
        s.main.setWindowTitle('SQUARE GUIDELINES')
        try: s.signal.highlight.emit(s.name)
        except AttributeError: return

    def leaveEvent(s, *args):
        default_title = f"{os.environ['PROGRAM']} {os.environ['VERSION']}"
        s.main.setWindowTitle(default_title)
        s._highlight('turn_me_black')

class Main(QtWidgets.QMainWindow):
    def __init__(s, qapplication, *args, **kwargs):
        super().__init__(styleSheet='background:rgb(10,10,10);color:white', *args, **kwargs)
        s._qapplication = qapplication
        default_title = f"{os.environ['PROGRAM']} {os.environ['VERSION']}"
        s.setWindowTitle(default_title)
        s.virgin = True
        s.make_start_btn_and_slider()
        s.slider.thingey.large = 40
        s.genereate_new_board()
        s.show()

        s.slider.thingey.visuals()
        s.slider.thingey.spawn_thingey(s.width() * 0.4)
        s.slider.thingey.visuals()
        s.slider.thingey.setText('40%')
        s.slider.thingey.large = 40

    def make_start_btn_and_slider(s):
        s.start_btn = HighlightLabel(s, text='NEW BOARD', center=True)
        Trigger(s.start_btn, mousebutton=True, fn=s.genereate_new_board)
        pos(s.start_btn, height=24, left=8)
        shrink_label_to_text(s.start_btn, x_margin=20)
        kwgs = dict(steps=[x for x in range(0, 100, 1)], center=True, color='black')
        spawnslider = dict(left_zero_lock=True, background='rgba(200,190,150,125)', **kwgs)
        s.slider = CustomSlider(s, spawnslider=spawnslider, background='rgba(50,50,50,50)')
        pos(s.slider, after=s.start_btn, height=s.start_btn)
        def resize_to_main():
            pos(s.slider, reach=dict(right=s.width()))
        Trigger(s, resize=True, fn=resize_to_main)
        s.setting_btn1 = SettingsBTN(s, main=s)
        highlight_style(s.setting_btn1, name='settings_btn')
        pos(s.setting_btn1, height=s.start_btn, reach=dict(right=s.start_btn.geometry().left()-2))
        s.setting_btn1.value = 1

    def genereate_new_board(s):
        squares = s.generate_squares()
        s.draw_sheet(squares)
        s.hide_this_percentage_of_slots()
        signal_highlight()

    def screen_starting_geometry(s, x_factor=0.8, y_factor=0.8, primary=True):
        for screen in s._qapplication.screens():

            x = screen.geometry().left()
            y = screen.geometry().top()
            w = screen.geometry().width()
            h = screen.geometry().height()

            bleed_x = (w - (w * x_factor)) * 0.5
            bleed_y = (h - (h * y_factor)) * 0.5

            geo = int(bleed_x) + x, int(bleed_y) + y, int(w * x_factor) or 1280, int(h * y_factor) or 768

            if primary and screen == QtGui.QGuiApplication.primaryScreen():
                s.setGeometry(*geo)
                return

            elif not primary and screen != QtGui.QGuiApplication.primaryScreen():
                s.setGeometry(*geo)
                return

        s.setGeometry(0, 0, 1280, 768)  # fallback

    def generate_squares(s):
            large = 0
            while large < 100:
                large += 1
                small = 0

                squares = []
                for row in range(1, 4):
                    for col in range(1, 4):
                        squares.append(Square(row=row, col=col))

                random.seed('S4lt4P1nn4r_' + str(uuid.uuid4()))
                while small < 100 and any(not x.complete() for x in squares):
                    small += 1

                    for square in [x for x in squares if not x.complete()]:
                        nums = [x for x in range(1, 10) if not square.number_taken(x)]
                        random.shuffle(nums)

                        for slot in square.slots:
                            if slot.number:
                                continue

                            line_x = [x for x in squares if x != square and x.row == square.row]
                            line_y = [x for x in squares if x != square and x.column == square.column]

                            for num in [x for x in nums]:
                                if any(x.number_same_column(num, slot.column) for x in line_x):
                                    continue
                                elif any(x.number_same_row(num, slot.row) for x in line_y):
                                    continue
                                else:
                                    slot.number = num
                                    nums.remove(num)

                if all(x.complete() for x in squares):
                    return squares

    def draw_sheet(s, squares=None, size=50):
        squares = squares if squares else s.generate_squares()
        if any(not x.complete() for x in squares):
            s.setWindowTitle('FAILURE, PLEASE REDRAW!')
            return

        try: s.sheet.close()
        except: pass

        s.sheet = GUISheet(s, background='transparent', color='transparent')
        s.sheet.squares = []
        fontsize = False
        for i in squares:

            back = GUISquare(s.sheet)
            back.all_slots_off = s.sheet.all_slots_off
            back.row = int(i.row)
            back.column = int(i.column)
            back.change_background_color()
            back.slots = []

            for slot in i.slots:
                thing = GUISlot(back, text='#', center=True, fontsize=fontsize or 90, main=s)
                thing.row = int(slot.row)
                thing.column = int(slot.column)
                thing.number = int(slot.number)
                thing.square = back
                thing.squares = s.sheet.squares
                thing.all_slots_off = s.sheet.all_slots_off
                thing.game_finished = s.sheet.game_finished
                thing.position_me(size)
                fontsize = fontsize if fontsize else font_fitter(thing, x_margin=8, y_margin=8)
                back.slots.append(thing)

            back.expand_me()
            s.sheet.squares.append(back)


        w = max(x.geometry().right() + 1 for x in s.sheet.squares)
        h = max(x.geometry().bottom() + 1 for x in s.sheet.squares) + s.start_btn.height()
        pos(s.sheet, size=[w, h], top=size + s.start_btn.height(), left=size)
        for screen in s._qapplication.screens():
            if screen == QtGui.QGuiApplication.primaryScreen() and s.virgin:
                pos(s, size=[w, h], add=size * 2)
                x1 = (screen.geometry().width() - s.width()) * 0.5
                y1 = (screen.geometry().height() - s.height()) * 0.5
                pos(s, left=x1, top=y1)
                s.setFixedSize(s.size())
                s.virgin = False

        s.setWindowTitle('SUDOKU')

    def hide_this_percentage_of_slots(s):
        try: percentage = s.slider.get_small_large()[1] or 40
        except: percentage = 40
        finally: percentage = percentage * 0.01

        slots = []
        for square in s.sheet.squares:
            slots += square.slots

        random.seed('S4lt4P1nn4r_' + str(uuid.uuid4()))
        random.shuffle(slots)
        for count, slot in enumerate(slots):
            slot.fortified = count >= len(slots) * percentage
            slot.number = 0 if not slot.fortified else slot.number
            slot.setText(str(slot.number or ""))
            slot.change_background_color()
