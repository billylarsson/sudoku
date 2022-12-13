import sys, os, tempfile

PROGRAM = 'SUDOKU'
VERSION = '30.3'
BASEDIR = os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind(os.sep)]
SETTINGSFILE = os.path.realpath(BASEDIR + os.sep + 'settings.ini')
IMGFOLDER = os.path.realpath(BASEDIR + os.sep + 'img')
tail =  os.sep + PROGRAM.replace(' ', '_')
TMPFOLDER = '/mnt/ramdisk' + tail if os.path.exists('/mnt/ramdisk') else os.path.realpath(tempfile.gettempdir() + tail)

os.environ['BASEDIR'] = BASEDIR
os.environ['PROGRAM'] = PROGRAM
os.environ['VERSION'] = VERSION
os.environ['SETTINGSFILE'] = SETTINGSFILE
os.environ['IMGFOLDER'] = IMGFOLDER
os.environ['TMPFOLDER'] = TMPFOLDER

for var in ['TMPFOLDER']:
    path = os.environ[var]
    try: os.mkdir(path) if not os.path.exists(path) and not os.path.isdir(path) else None
    except PermissionError:
        tmpfolder = os.path.realpath(tempfile.gettempdir())
        os.environ[var] = tmpfolder
        print(f'Error creating {path} falling back to {tmpfolder}')

if not os.path.exists(SETTINGSFILE):
    try:
        f = open(SETTINGSFILE, 'w')
        f.close()
    except PermissionError:
        pass

from PyQt6 import QtWidgets
from bscripts.main import Main

if '__main__' in __name__:
    app = QtWidgets.QApplication(sys.argv)
    window = Main(qapplication=app)
    app.exec()