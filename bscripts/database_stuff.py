from bscripts.sqlite_handler import SQLite

sqlite = SQLite(ini_variable='local_database')

class DB:
    class settings:
        config = sqlite.get_enum(table='settings', column='config', type='blob')

