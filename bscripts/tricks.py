from PIL                     import Image
from PyQt6.QtCore            import QObject, pyqtSignal
from bscripts.database_stuff import DB, sqlite
from datetime                import datetime
from functools               import partial
from queue                   import Queue
from urllib.request          import Request, urlopen
import hashlib
import os
import pathlib
import pickle
import random
import requests
import shutil
import ssl
import tempfile
import threading
import time
import uuid

default_dict = dict(
    default=dict(
        main=dict(value='background-color:rgb(30,30,40);color:white'),
        searcher=dict(value='background-color:rgb(25,25,40);color:green'),
        smartlineedit=dict(value=f'background-color:rgba(140,140,0,150);color:yellow'),
        searchlineedits=dict(value=f'background-color:rgb(15,15,20);color:rgba(100,250,150,200)'),
        searchlinetips=dict(value=f'background-color:transparent;color:rgba(120,240,120,100)'),
    ),
    highlight=dict(
        globlahighlight=[
            dict(activated_on=dict(background='rgb(250,250,250)', color='black')),
            dict(activated_off=dict(background='rgb(200,200,200)', color='black')),
            dict(deactivated_on=dict(background='rgb(150,150,150)', color='black')),
            dict(deactivated_off=dict(background='rgb(100,100,100)', color='black')),
        ],
        slot_fortified=[
            dict(activated_on=dict(background='rgb(210,210,250)', color='black', border='black')),
            dict(activated_off=dict(background='rgb(180,180,210)', color='black', border='black')),
            dict(deactivated_on=dict(background='rgb(210,210,210)', color='black', border='black')),
            dict(deactivated_off=dict(background='rgb(180,180,180)', color='black', border='black')),
        ],
        slot_free=[
            dict(activated_on=dict(background='rgb(210,210,250)', color='rgb(60,60,60)', border='black')),
            dict(activated_off=dict(background='rgb(180,180,210)', color='rgb(60,60,60)', border='black')),
            dict(deactivated_on=dict(background='rgb(210,210,210)', color='rgb(60,60,60)', border='black')),
            dict(deactivated_off=dict(background='rgb(180,180,180)', color='rgb(60,60,60)', border='black')),
        ],
        slot_complete=[
            dict(activated_on=dict(background='rgb(210,230,210)', color='rgb(5,5,5)', border='black')),
            dict(activated_off=dict(background='rgb(180,210,180)', color='rgb(5,5,5)', border='black')),
            dict(deactivated_on=dict(background='rgb(210,230,210)', color='rgb(5,5,5)', border='black')),
            dict(deactivated_off=dict(background='rgb(180,210,180)', color='rgb(5,5,5)', border='black')),
        ],
        settings_btn=[
            dict(deactivated_on=dict(background='rgba(10,230,10,100)', color='rgb(5,5,5)')),
            dict(deactivated_off=dict(background='rgba(200,10,60,100)', color='rgb(5,5,5)')),
        ],
    ))

for i in default_dict['default']:
    if 'activated' not in default_dict['default'][i]:
        default_dict['default'][i].update({'activated': True})

class WorkerSignals(QObject):
    finished       = pyqtSignal()
    error          = pyqtSignal()
    killswitch     = pyqtSignal()
    listdelivery   = pyqtSignal(list)
    dictdelivery   = pyqtSignal(dict)
    objectdelivery = pyqtSignal(object)
    highlight      = pyqtSignal(str)
    stringdelivery = pyqtSignal(str)
    filedelivery   = pyqtSignal(str)
    progress       = pyqtSignal(dict)

def md5_hash_string(string=None, random=False, upper=False, under=False):
    if not string or random:
        salt = 'how_much_is_the_fi2H'
        string = f'{uuid.uuid4()}{time.time()}{salt}{string or ""}'

    hash_object = hashlib.md5(string.encode())
    rv = hash_object.hexdigest()
    rv = rv.upper() if upper else rv
    rv = '_' + rv if under else rv

    return rv

def digit_prolonger(numeric_value, digits=2):
    try: numeric_value = float(numeric_value)
    except: return 'N/A'

    numeric_value += 0.00
    if numeric_value >= 100 and digits:
        digits = 0

    return f"%.{digits}f" % numeric_value

class CustomThreadPool:
    def __init__(s):
        s.spider_nests = {}

    class SpiderSignals(QObject):
        start_master = pyqtSignal(dict)

    def dummy(s, dummy):
        return time.sleep(dummy) if type(dummy) in (int, float) else False

    def __call__(s,

        slave_fn=None,
        slave_args=(),
        slave_kwargs={},
        master_fn=None,
        master_args=(),
        master_kwargs={},
        threads=1,
        name='default',
        dummy=False,
        **kwargs
        ):

        s.dummy(dummy) if dummy else dummy

        try: tp_queue = s.spider_nests[name]
        except:
            s.spider_nests[name] = Queue(maxsize=threads)
            tp_queue = s.spider_nests[name]

            s.cellar_spider = threading.Thread(target=s.spider_queen, args=(tp_queue,), daemon=True)
            s.cellar_spider.start()

        work = dict(
            slave_fn=slave_fn, slave_args=slave_args, slave_kwargs=slave_kwargs,
            master_fn=master_fn, master_args=master_args, master_kwargs=master_kwargs,
            signal=s.SpiderSignals()
            )
        work['signal'].start_master.connect(s.spider_kings_work)
        threading.Thread(target=s.feed_spider_queen, args=(tp_queue, work,), daemon=True).start()

    def feed_spider_queen(s, tp_queue, work):
        tp_queue.put(work)

    def spider_queen(s, tp_queue):
        while True:
            work = tp_queue.get()
            tp_queue.mutex.acquire_lock() if tp_queue.unfinished_tasks >= tp_queue.maxsize else None
            threading.Thread(target=s.spider_queens_work, args=(tp_queue, work,)).start()

    def spider_queens_work(s, tp_queue, work):  # slave thread
        if work['slave_fn']:

            slave_fn = work['slave_fn']
            slave_args = work['slave_args']
            slave_kwargs = work['slave_kwargs']

            if slave_args and slave_kwargs:
                slave_fn(*slave_args, **slave_kwargs)
            elif slave_args:
                slave_fn(*slave_args)
            elif slave_kwargs:
                slave_fn(**slave_kwargs)
            else:
                slave_fn()

        try: work['signal'].start_master.emit(work)
        except RuntimeError: print("THREAD DISCONTINUED")

        tp_queue.mutex.release_lock() if tp_queue.mutex.locked_lock() else None
        tp_queue.task_done()

    def spider_kings_work(s, work):  # main thread
        for master_fn in work['master_fn'] if isinstance(work['master_fn'], list) else [work['master_fn']]:
            master_args = work['master_args']
            master_kwargs = work['master_kwargs']

            if master_args and master_kwargs:
                master_fn(*master_args, **master_kwargs)
            elif master_args:
                master_fn(*master_args)
            elif master_kwargs:
                master_fn(**master_kwargs)
            elif master_fn:
                master_fn()

thread = CustomThreadPool()

class Antihammer:
    def __init__(s, timer=10, floodlimit=25, *args, **kwargs):
        s.timer, s.floodlimit = timer, floodlimit
        s.signal = s.TimerSignal()
        s.signal.reset.connect(s.reset)
        s.signal.tick.connect(s.floodcounter)
        s.lock = threading.Lock()
        s.max_epoch = time.time() - 1
        s.points_left = s.floodlimit - 1

    class TimerSignal(QObject):
        reset = pyqtSignal(bool)
        tick = pyqtSignal(int)

    def __call__(s, url=None, *args, **kwargs):
        tmpfile = tmp_file(url, reuse=True, *args, **kwargs) if url else None
        if url and os.path.exists(tmpfile):
            return True

        s.lock.acquire()

        if s.points_left <= 0:
            wait = s.max_epoch - time.time()
            time.sleep(wait) if wait > 0.01 else None
            s.signal.reset.emit(True)
        else:
            s.signal.tick.emit(1)

    def floodcounter(s, tick):
        s.points_left -= tick
        s.lock.release()

    def reset(s, *args):
        s.max_epoch = time.time() + s.timer
        s.points_left = s.floodlimit - 1
        s.lock.release()

def tmp_file(
        file_of_interest=None,
        reuse=False,
        delete=False,
        hash=True,
        extension=None,
        days=False,
        minutes=False,
    ):

    base_dir = os.environ['TMPFOLDER'] if os.path.exists(os.environ['TMPFOLDER']) else tempfile.gettempdir()
    file_of_interest = md5_hash_string(string=file_of_interest) if hash or not file_of_interest else file_of_interest

    f = base_dir + os.sep + file_of_interest
    f += "" if not extension else f".{extension.strip('.')}"
    f = os.path.realpath(f)

    if os.path.exists(f):
        if delete:
            os.remove(f)
        elif days:
            os.remove(f) if os.path.getmtime(f) < time.time() - (86400 * days) else False
        elif minutes:
            os.remove(f) if os.path.getmtime(f) < time.time() - (60 * minutes) else False
        elif not reuse:
            os.remove(f)

    return f

def tmp_folder(
        folder_of_interest=None,
        reuse=False,
        delete=False,
        hash=False,
        create_dir=True,
    ):

    f = md5_hash_string(folder_of_interest) if hash or not folder_of_interest else folder_of_interest
    f = os.path.realpath(f"{os.environ['TMPFOLDER']}{os.sep}{f}")

    shutil.rmtree(f) if os.path.isdir(f) and delete else False
    shutil.rmtree(f) if os.path.isdir(f) and not reuse else False
    pathlib.Path(f).mkdir(parents=True) if not os.path.isdir(f) and create_dir else False

    return f

def close_and_pop(thislist):
    [(thislist[x].close(), thislist.pop(x)) for x in range(len(thislist) - 1, -1, -1)]

def shrink_label_to_text(label, x_margin=2, y_margin=2, width=True, height=False):
    label.show()

    if height:
        rvsize = label.fontMetrics().boundingRect(label.text()).height() + y_margin
        QtPosition(label, height=rvsize)

    if width:
        rvsize = label.fontMetrics().boundingRect(label.text()).width() + x_margin
        QtPosition(label, width=rvsize)

def get_fontsize(widget):
    construct = style(widget, curious=dict)
    try:
        tmp = construct['base']['font'] or construct['tooltip']['font']
        tmp = [x for x in tmp if x.isdigit()]
        return int("".join(tmp))
    except (TypeError,KeyError):
        pass

def random_rgb(max_rgb_tuple=(150,150,150), min_rgb_tuple=False, variable=None, string=True, alpha=False):
    variable = md5_hash_string() if not variable else variable
    random.seed(variable)

    min_rgb_tuple = (max_rgb_tuple[0] / 5, max_rgb_tuple[1] / 5, max_rgb_tuple[2] / 5) if not min_rgb_tuple else min_rgb_tuple
    max_rgb_tuple = [max(max_rgb_tuple[c], min_rgb_tuple[c]) for c in range(len('RGB'))]

    rgb = [random.randint(int(min_rgb_tuple[c]), int(max_rgb_tuple[c])) for c in range(len('RGB'))]
    rgb = [x for x in rgb+[alpha]] if alpha else rgb
    rgb = [0 if rgb[c] < 0 else rgb[c] for c in range(len(rgb))]
    rgb = [255 if rgb[c] > 255 else rgb[c] for c in range(len(rgb))]

    return tuple(int(rgb[c]) for c in range(len(rgb))) if not string else f"rgb{'a' if alpha else ''}({','.join([str(x) for x in rgb])})"

class QtPosition:
    def __init__(s, thing=None, adjust=True, pedantic=True, **kwargs):
        s.thing = thing

        s.x = thing.pos().x() if thing else 0
        s.y = thing.pos().y() if thing else 0
        s.w = thing.width() if thing else 0
        s.h = thing.height() if thing else 0

        for k,v in {k:v for k,v in kwargs.items() if k not in ('add', 'sub', 'margin', 'x_margin', 'y_margin')}.items():
            try: getattr(s, k)(**kwargs)
            except AttributeError: continue

            if pedantic:
                s.x, s.y, s.w, s.h = int(s.x), int(s.y), int(s.w), int(s.h)

            s.extra(action=k, **kwargs)

        s.adjust(**kwargs) if thing and adjust else False

    def between(s, between, **kwargs):
        if between[0].geometry().top() != between[1].geometry().top():
            s.y = sum([x.geometry().top() for x in between]) / 2
        else:
            s.y = between[0].geometry().top()

        between.sort(key=lambda x:x.geometry().right())
        delta = between[1].geometry().left() - between[0].geometry().right()

        if delta > 0:
            s.x = between[0].geometry().right() + (delta / 2) - (s.w / 2) + 1

    def width(s, width, **kwargs):
        s.w = width if isinstance(width, (int, float)) else width.width()

    def height(s, height, **kwargs):
        s.h = height if isinstance(height, (int, float)) else height.height()

    def size(s, size, **kwargs):
        s.w = size[0] if isinstance(size, (list, tuple)) else size.width()
        s.h = size[1] if isinstance(size, (list, tuple)) else size.height()

    def coat(s, coat, **kwargs):
        s.x = coat.pos().x()
        s.y = coat.pos().y()
        s.w = coat.width()
        s.h = coat.height()

    def inside(s, inside, **kwargs):
        s.x = 0
        s.y = 0
        s.w = inside.width()
        s.h = inside.height()

    def after(s, after, **kwargs):
        s.x = after.geometry().right() + 1
        s.y = after.geometry().top()

    def before(s, before, **kwargs):
        s.x = before.geometry().left() - s.w
        s.y = before.geometry().top()

    def above(s, above, **kwargs):
        s.x = above.geometry().left()
        s.y = above.geometry().top() - s.h

    def below(s, below, **kwargs):
        s.x = below.geometry().left()
        s.y = below.geometry().bottom() + 1

    def center(s, center, **kwargs):
        try: fit = max(center) - min(center)
        except TypeError:
            tmp = [(x, x.geometry().right()) for x in center]
            tmp.sort(key=lambda x:x[1])
            center = tmp[0][0].geometry().right(), tmp[1][0].geometry().left()
            fit = max(center) - min(center)
        s.x = min(center) + (fit - s.w) / 2

    def left(s, left, **kwargs):
        s.x = left if isinstance(left, (int, float)) else left.geometry().left()

    def right(s, right, **kwargs):
        s.x = right - (s.w + 1) if isinstance(right, (int, float)) else right.geometry().right() - (s.w + 1)

    def top(s, top, **kwargs):
        s.y = top if isinstance(top, (int, float)) else top.geometry().top()

    def bottom(s, bottom, **kwargs):
        s.y = bottom - (s.h - 1) if isinstance(bottom, (int, float)) else bottom.geometry().bottom() - (s.h - 1)

    def move(s, move, **kwargs):
        s.x += move[0] if isinstance(move[0], (int, float)) else move[0].width()
        s.y += move[1] if isinstance(move[1], (int, float)) else move[1].height()

    def reach(s, reach, **kwargs):
        for side in reach:

            if side == 'right' and isinstance(reach[side], (int, float)):
                s.w += (reach[side] - (s.x + s.w - 1))

            elif side == 'left' and isinstance(reach[side], (int, float)):
                s.w += (s.x - reach[side] + 1)
                s.x -= (s.x - reach[side] + 1)

            elif side == 'bottom' and isinstance(reach[side], (int, float)):
                s.h += (reach[side] - (s.y + s.h - 1))

            elif side == 'top' and isinstance(reach[side], (int, float)):
                s.h += (s.y - reach[side] + 1)
                s.y -= (s.y - reach[side] + 1)

    def extra(s, action, margin=0, add=0, sub=0, x_margin=0, y_margin=0, **kwargs):

        if margin and action in ('inside', 'coat'):
            s.w -= (margin*2)
            s.h -= (margin*2)
            s.x += margin
            s.y += margin

        elif sum([add, sub]) and action in ('size', 'width', 'height'):
            s.w += add if action in ('width','size') else 0
            s.h += add if action in ('height','size') else 0
            s.w -= sub if action in ('width','size') else 0
            s.h -= sub if action in ('height','size') else 0

        elif x_margin and action in ('right', 'after'):
            s.x += x_margin

        elif x_margin and action in ('left', 'before'):
            s.x -= x_margin

        elif y_margin and action in ('bottom', 'below'):
            s.y += y_margin

        elif y_margin and action in ('top', 'above'):
            s.y -= y_margin

    def adjust(s, **kwargs):
        s.thing.setGeometry(int(s.x), int(s.y), int(s.w), int(s.h))

pos = QtPosition

class Cutouter:
    def __init__(self, contents, *args, **kwargs):
        self.org_contents = contents
        self.cache = None
        self.reset()
        self(*args, **kwargs)

    def __call__(self,
                    first_find=None,
                    find_first=None,
                    then_find=False,
                    start_from=False,
                    search_range=False,
                    preshrink=False,
                    plow=False,
                    rewind=0,
                    forward=0,
                    *args,
                    **kwargs,
                    ):

        self.plow_mode(plow)

        if find_first or first_find:
            self.set_starting_point(start_from)
            self.set_ending_point(search_range, preshrink)
            self.find_first_target(find_first or first_find, rewind, forward, search_range)

        if then_find:
            self.find_second_target(then_find)

    def __bool__(self):
        return self.status

    def __str__(self):
        if self.status:
            return self.text

    def reset(self):
        self.status, self.focus, self.back_focus = False, 0, -1

    def plow_mode(self, plow):
        """ will discard previous tracks as machine only plow forward, never backwards """
        if self.status and plow and max(self.focus, self.back_focus) > 0:
            self.org_contents = self.org_contents[max(self.focus, self.back_focus):]
            self.reset()

    def set_starting_point(self, start_from):
        """ set cache beginning, starting point will be fixed from here on """
        if start_from and len(self.org_contents) > start_from:
            self.cache = self.org_contents[start_from:]
        else:
            self.cache = self.org_contents

    def set_ending_point(self, search_range, preshrink=False):
        """ this only happens if first target has been discovered unless foreced """
        if search_range and len(self.cache) > search_range:
            if preshrink or self.focus > -1:

                if self.focus > -1:
                    self.cache = self.cache[self.focus:]
                    self.focus = 0

                if len(self.cache) > search_range:
                    self.cache = self.cache[0:search_range]

    def find_first_target(self, find_first, rewind=0, forward=0, search_range=False):
        if type(find_first) == str:
            find_first = [find_first]

        for query in find_first or []:

            self.status = False
            self.focus = self.cache[self.focus:].find(query) + self.focus

            if self.focus > -1:

                if type(rewind) == str:
                    self.focus += (0 - len(rewind))
                elif type(rewind) == bool and rewind:
                    self.focus += (0 - len(query))

                if type(forward) == str:
                    self.focus += len(forward)
                elif type(forward) == bool and forward:
                    self.focus += len(query)

                self.set_ending_point(search_range)

                self.text = self.cache[self.focus:]
                self.status = True
            else:
                return False

    def find_second_target(self, then_find):
        """then_find usually a string, but if its a list
        or tuple its a combined/additional first_find """
        if then_find and self.focus > -1:

            if type(then_find) == str:
                then_find = [then_find]

            for count, query in enumerate(then_find or []):
                self.status = False

                if count+1 < len(then_find):
                    self.find_first_target(query)  # backwards compatible
                    if not self.status:
                        return False
                else:
                    self.back_focus = self.cache[self.focus:].find(query) + self.focus

                    if self.back_focus > self.focus:
                        self.text = self.cache[self.focus:self.back_focus]
                        self.status = True
                    else:
                        return False

def find_free_horizontal_position(place, widget, widgets, x_margin=0, y_margin=0):
    pos = QtPosition

    widgets.remove(widget) if widget in widgets else None
    widgets.sort(key=lambda x:x.geometry().left())
    widgets.sort(key=lambda x:x.geometry().top())

    def get_position(this):
        top, bottom = this.geometry().top(), this.geometry().bottom()
        left, right = this.geometry().left(), this.geometry().right()
        return top,bottom,left,right

    def place_taken(nt, nb, nl, nr):
        for i in widgets:

            if nl > i.geometry().right() or nt > i.geometry().bottom(): # comes after or under
                continue
            elif nr < i.geometry().left() or nb < i.geometry().top(): # comes before or above
                continue

            return True

    if not place_taken(*get_position(widget)):
        widgets.append(widget)
        return

    for i in widgets:
        if i.geometry().right() + 1 + widget.width() <= place.width():
            x, y, w, h = i.geometry().right() + 1 + x_margin, i.geometry().top() + y_margin, widget.width(), widget.height()
            if place_taken(y, y+h, x, x+w):
                continue

            pos(widget, after=i, x_margin=x_margin)
            widgets.append(widget)
            return

    widgets.sort(key=lambda x:x.geometry().bottom())
    widgets.sort(key=lambda x:x.geometry().left(), reverse=True)

    pos(widget, below=widgets[-1], y_margin=y_margin) if widgets else None
    widgets.append(widget)

def signal_highlight(name='_global', message='_'):
    signal = tech.signals(name)
    signal.highlight.emit(message)

def font_fitter(object, maxsize=24, minsize=1, x_margin=10, y_margin=0, shorten=False):
    style(object, font=maxsize) if not style(object, curious=dict)['base']['font'] else None

    for count in range(0 if not shorten else len(object.text())):
        object.show()
        if object.fontMetrics().boundingRect(object.text()).width() + x_margin > object.width():
            text = object.text()
            object.setText(text[0:-3] + '..')
        elif count == 0:
            return False
        else:
            return True

    for count in range(maxsize, minsize, -1):
        object.show()
        if object.fontMetrics().boundingRect(object.text()).width() + x_margin > object.width():
            style(object, font=count)
        elif object.fontMetrics().boundingRect(object.text()).height() + y_margin > object.height():
            style(object, font=count)
        else:
            return count + 1

def style(widget=None, background=None, color=None, font=None, tooltip=None, curious=False, border=None, px=0, construct=False, name=False):
    future = dict(
                base={
                'background-color': None,
                'color': None,
                'font': None,
                'border': None},
                QToolTip={
                'background-color': None,
                'color': None,
                'font': None,
                'border': None})

    try: current = tech.config(setting=name, curious=True) or widget.styleSheet() if name else construct.styleSheet() if construct else widget.styleSheet()
    except AttributeError: widget, current = construct, construct.styleSheet() if construct else ""
    finally: current = 'base{' + current + '}' if '{' not in current else current

    while '{' in current and current.find('}') > current.find('{'):
        cut = current.find('{')
        key = current[:cut].strip()
        key = 'base' if key != 'QToolTip' else 'QToolTip'
        current = current[cut + 1:]

        cut = current.find('}')
        strings = current[:cut].split(';')
        current = current[cut + 1:]

        while strings:

            thing = strings[0].split(':')
            strings.pop(0)

            if len(thing) == 2 and thing[0].strip() in future[key]:
                future[key][thing[0].strip()] = thing[-1].strip()

    key = 'QToolTip' if tooltip else 'base'
    for k,v in {'background-color':background, 'color':color, 'font':font, 'border':border}.items():
        v = f"{px or 1}px solid {v}" if k == 'border' and v else v
        v = f"{v}pt" if k == 'font' and v else v
        future[key][k] = str(v) if v else future[key][k]
        # overwrites present styling only if not none

    string = ""
    for i in [x for x in ('base', 'QToolTip') if any(True for k,v in future[x].items() if v)]:
        string += widget.metaObject().className() if i == 'base' else i
        strings = [':'.join([k,v]) for k,v in future[i].items() if v] if any(True for k,v in future[i].items() if v) else []
        string += '{' + ';'.join(strings) + '}' if strings else ""

    if curious:
        return string if curious == True else future

    widget.setStyleSheet(string) if widget.styleSheet() != string else None

def highlight_style(widget, name, specific=False):
    if name in default_dict['highlight']:
        for preset in default_dict['highlight'][name]:
            for k,v in preset.items():

                if specific and k != specific:
                    continue

                setattr(widget, k, v)

def header_generator(operatingsystem='windows', randominize=False):
    agents = [
        dict(agent='Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0', os='linux'),
        dict(agent='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0', os='windows'),
        dict(agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:10.0) Gecko/20100101 Firefox/10.0', os='mac'),
        dict(agent='Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0', os='android'),
        dict(agent='Mozilla/5.0 (Android 4.4; Tablet; rv:41.0) Gecko/41.0 Firefox/41.0', os='tablet'),
        dict(agent='Mozilla/5.0 (iPhone; CPU iPhone OS 8_3 like Mac OS X) AppleWebKit/600.1.4 \
        (KHTML, like Gecko) FxiOS/1.0 Mobile/12F69 Safari/600.1.4', os='iphone'),
        dict(agent='Mozilla/5.0 (iPad; CPU iPhone OS 8_3 like Mac OS X) AppleWebKit/600.1.4 \
        (KHTML, like Gecko) FxiOS/1.0 Mobile/12F69 Safari/600.1.4', os='ipad'),
    ]
    if randominize:
        random.shuffle(agents)
    else:
        agents = [x for x in agents if x['os'] == operatingsystem] or agents

    return {'User-Agent' : agents[0]['agent']}

def timeconverter(unixtime=None, stringdate=None, long=False, clock=False):
    """
    unixtime: 1640991600.0 (returns string 2021-01-07, long adds hours and seconds)
    stringdate: 2022-01-01 (returns epoch)
    """
    if unixtime:
        if type(unixtime) == str:
            try: unixtime = int(unixtime)
            except: return ""
        if long or clock:
            if clock:
                return datetime.fromtimestamp(unixtime).strftime('%H:%M:%S')
            else:
                return datetime.fromtimestamp(unixtime).strftime('%Y-%m-%d @ %H:%M:%S')
        else:
            return datetime.fromtimestamp(unixtime).strftime('%Y-%m-%d')
    elif stringdate.count('-') >= 2:
        stringdate = stringdate.split('-')
        stringdate += [0,0,0,0]
        stringdate = (int(x) for count, x in enumerate(stringdate) if count < 7)
        return datetime(*stringdate).timestamp()

def printout_downloaded_this_file(url, full_path='', force=False):
    clock = timeconverter(time.time(), clock=True)
    BROWN, GREEN, CYAN, GRAY, END = '\033[0;33m', '\033[92m', '\033[96m', '\033[0;37m', '\033[0m'
    text = f'{clock} {GRAY}DOWNLOADED {CYAN}{url}{GRAY} ---::]{END}'
    if full_path and os.path.exists(full_path):
        text += f' {GREEN}{full_path} {GRAY}{round(os.path.getsize(full_path) / 1000)}kb{END}'
    print(text)

def download_file(url, file=None, headers={}, reuse=True, days=False, minutes=False, **kwargs):

    def method_one(url, file, headers, gcontext=None, runner=0):
        while not os.path.exists(file) and runner < 5:
            runner += 1

            if runner == 1:  # first run do this!
                try:
                    with requests.get(url, stream=True, headers=headers) as r:
                        r.raw.read = partial(r.raw.read, decode_content=True)
                        with open(file, 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
                except:
                    time.sleep(random.uniform(1, 2))
            else:
                urlobj = Request(url, headers=headers)
                try:
                    with urlopen(urlobj, context=gcontext) as response, open(file, 'wb') as f:
                        shutil.copyfileobj(response, f)
                except:
                    time.sleep(random.uniform(1, 2))

            if os.path.exists(file):
                if os.path.getsize(file) > 0:
                    printout_downloaded_this_file(url, file)
                    break
                else:
                    os.remove(file)

            headers = header_generator(randominize=True)
            gcontext = ssl.SSLContext()

    file = tmp_file(file_of_interest=url, reuse=reuse, days=days, minutes=minutes, **kwargs) if not file else file

    headers = header_generator(**headers)

    method_one(url, file, headers)
    if os.path.exists(file):
        return file
    else:
        print('DOWNLOAD ERROR:', url, '->', file)

def make_image_into_blob(image_path, width=None, height=None, quality=70, method=6):
    try: image = Image.open(image_path)
    except: return False

    if width and image.size[0] < width:
        height = round(image.size[1] * (width / image.size[0]))
    elif height and image.size[1] < height:
        width = round(image.size[0] * (height / image.size[1]))
    elif height:
        width = image.size[1] * (image.size[0] / image.size[1])
    elif width:
        height = image.size[0] * (image.size[1] / image.size[0])
    else:
        width = image.size[0]
        height = image.size[1]

    image_size = int(width), int(height)
    image.thumbnail(image_size, Image.LANCZOS)

    tmpfile = tmp_file(extension='webp')
    image.save(tmpfile, 'webp', method=method, quality=quality)

    with open(tmpfile, 'rb') as f:
        blob = f.read()
        os.remove(tmpfile)
        image.close()
        return blob

def make_new_file_from_blob(blob, *args, **kwargs):
    tmpfile = tmp_file(*(str(blob),) if not args else args, **kwargs)
    if not os.path.exists(tmpfile) and blob:
        with open(tmpfile, 'wb') as output_file:
            output_file.write(blob)
    return tmpfile

class Victorinox:
    def __init__(s):
        s.techdict = {}
        s.signal = s.ConfigSignals()
        s.signal.save_config.connect(s._save_config)
        s._save_config(('dummy', None, 'default', True, None, True,))

    class ConfigSignals(QObject):
        save_config = pyqtSignal(tuple)

    def save_config(self, setting, value=None, theme='default', delete=False, signal=None, dummy=False):
        self.signal.save_config.emit((setting, value, theme, delete, signal, dummy,))

    def _save_config(self, signal_tuple):
        setting, value, theme, delete, signal, dummy = signal_tuple

        if not setting or type(setting) == str and setting[0] == '_':
            return  # we dont do _unders

        if not 'config' in self.techdict:
            blob = sqlite.execute('select * from settings where id is 1')
            if blob and blob[1]:
                self.techdict['config'] = pickle.loads(blob[1])
            else:
                query, values = sqlite.empty_insert_query('settings')
                sqlite.execute(query, tuple(values))
                self.techdict['config'] = {}

        if not theme in self.techdict['config']:
            self.techdict['config'][theme] = {}

        if setting in self.techdict['config'][theme]:
            thing = self.techdict['config'][theme][setting]
        else:
            thing = {'activated': True, 'value': None}
            self.techdict['config'][theme][setting] = thing

        if type(value) == bool:
            thing['activated'] = value
        else:
            thing['value'] = value

        if delete:
            self.techdict['config'][theme].pop(setting)

        if not dummy:
            data = pickle.dumps(self.techdict['config'])
            sqlite.execute('update settings set config = (?) where id = (?)', values=(data,1,))

        if signal:
            signal.finished.emit()

    def config(self, setting, theme='default', curious=False, raw=False):
        for container in [self.techdict['config'], default_dict]:
            if theme in container:
                if setting in container[theme]:
                    rv = False
                    if raw:
                        rv = container[theme][setting]
                    elif curious:
                        rv = container[theme][setting]['value']
                    elif container[theme][setting]['activated']:
                        rv = container[theme][setting]['value'] or True

                    if type(rv) == list:
                        rv = [x for x in rv]
                    elif type(rv) == dict:
                        rv = {k:v for k,v in rv.items()}

                    return rv

    def signals(s, name=False):
        try: return s.techdict['signals'][name] if name else WorkerSignals()
        except KeyError:
            try: s.techdict['signals'][name] = WorkerSignals()
            except KeyError: s.techdict['signals'] = {name: WorkerSignals()}
        return s.techdict['signals'][name]

tech = Victorinox()