import os,sqlite3,pathlib,sys

class SQLite:
    def __init__(s, ini_variable='_default', filename=None, basedir='/home/plutonergy/Documents', path=None):
        s.cache = {}
        s.dev_mode = True if any(x for x in sys.argv if 'dev_mode' in x) else False
        kwgs = dict(ini_variable=ini_variable, filename=filename, basedir=basedir, path=path)
        rvd = s.make_direct_with_path(**kwgs) if path else s.generate_connection_using_kwargs(**kwgs)

        s.connection = sqlite3.connect(rvd[ini_variable])
        s.cursor = s.connection.cursor()

    def make_direct_with_path(s, ini_variable, filename, basedir, path, **kwargs):
        return {ini_variable: path}

    def generate_connection_using_kwargs(s, ini_variable, filename, basedir, **kwargs):
        s.basedir = basedir if os.path.exists(basedir) else os.environ['BASEDIR']
        s.basedir = f"{os.path.realpath(s.basedir)}{os.sep}{os.environ['PROGRAM']}"

        rvd = s.parse_ini_file()

        if not [k for k,v in rvd.items() if k.lower() == ini_variable.lower()]:
            s.add_var_to_ini_file(ini_variable, filename)
            rvd = s.parse_ini_file()

        if not os.path.exists(rvd[ini_variable]):
            tmp = rvd[ini_variable].split(os.sep)

            if not os.path.exists(os.sep.join(tmp[0:-1])):
                try: pathlib.Path(os.sep.join(tmp[0:-1])).mkdir(parents=True)
                except PermissionError:
                    print(f"Permissionerror when creating database folder, fallback to {os.environ['BASEDIR']}")
                    rvd[ini_variable] = f"{os.environ['BASEDIR']}{os.sep}{filename or ini_variable}.sqlite"
                    rvd[ini_variable] = os.path.realpath(rvd[ini_variable])
        return rvd

    def parse_ini_file(s):
        rvd = {}
        with open(os.environ['SETTINGSFILE']) as f:
            tmp = [x.split('=') for x in f.read().split('\n')]
            for i in [x for x in tmp if len(x) > 1]:
                rvd[i[0].strip('" ')] = '='.join(i[1:]).strip('" ')
        return rvd

    def add_var_to_ini_file(s, ini_variable, filename):
        if ini_variable.startswith('_'):  # we dont do unders
            return

        rvd = s.parse_ini_file()
        if ini_variable.lower() not in [k.lower() for k,v in rvd.items()]:
            head = f"{s.basedir}{os.sep}{filename or ini_variable.lower()}"
            head = head.split('.')
            head = ".".join(head) if head[-1].lower() != 'sqlite' else ".".join(head[0:-1])
            path = os.path.realpath(f"{head}.sqlite")
            rvd.update({ini_variable.lower(): path})

        with open(os.environ['SETTINGSFILE'], 'w') as f:
            tmp = ["=".join([k, v]) for k,v in rvd.items()]
            tmp = "\n".join(tmp)
            f.write(tmp)

    def soft_cache_update(s):
        s.cursor.execute("select name from sqlite_master where type='table'")
        for table in [x for x in s.cursor.fetchall() if x != 'sqlite_sequence']:
            s.cursor.execute(f'PRAGMA table_info("{table[0]}")')
            for table_info in [x for x in s.cursor.fetchall()]:
                try: s.cache[table[0]][table_info[1]] = table_info[0]
                except KeyError:
                    s.cache[table[0]] = {table_info[1]: table_info[0]}

    def get_enum(s, table, column, type='text', auto=True):
        try: return s.cache[table][column]
        except KeyError: s.soft_cache_update()

        try: return s.cache[table][column]
        except KeyError:

            #  creating new table at will
            try: s.cursor.execute(f'select * from "{table}"')
            except sqlite3.Error:
                query = f'create table "{table}"'
                query += ' (id INTEGER PRIMARY KEY AUTOINCREMENT)' if auto else ""
                s.cursor.execute(query)
                s.connection.commit()

            # creating new column at will
            try: s.cursor.execute(f'select * from "{table}" where {column} is not null')
            except sqlite3.Error:
                query = f'alter table "{table}" add column {column} {type.upper()}'
                s.cursor.execute(query)
                s.connection.commit()

            s.soft_cache_update()

        return s.cache[table][column]

    def empty_insert_query(s, table):
        query = 'PRAGMA table_info("' + str(table,) + '")'
        tables = s.cursor.execute(query)
        tables = [x for x in tables]
        query_part1 = 'insert into "' + table + '" values'
        query_part2 = "(" + ','.join(['?'] * len(tables)) + ")"
        values = [None] * len(tables)

        return query_part1 + query_part2, values

    def execute(s, query, values=False, all=False):
        if query.lower().startswith('select'):
            if values:
                s.cursor.execute(query, tuple(values) if isinstance(values, list) else values)
            else:
                s.cursor.execute(query)
            return s.cursor.fetchall() if all else s.cursor.fetchone()
        else:
            with s.connection:
                if isinstance(values, list):
                    s.cursor.executemany(query, values)
                elif values:
                    s.cursor.execute(query, values)
                else:
                    s.cursor.execute(query)

            s.dev_mode_print(query, values)

    def dev_mode_print(s, query, values, hide_bytes=True):
        if not s.dev_mode:
            return

        if values and type(values[0]) == bytes and hide_bytes:
            print('SQLITE execute QUERY:', query, ':::BYTES:::')

        elif type(values) == list and hide_bytes:
            print('SQLITE executemany QUERY:', query, 'LENGHT:', len(values))

        elif type(values) == tuple and hide_bytes:
            proxyvalues = [x for x in values]
            for count in range(len(proxyvalues)):
                if type(proxyvalues[count]) == bytes:
                    proxyvalues[count] = ':::BYTES:::'
            print('SQLITE execute QUERY:', query, proxyvalues)

        else:
            print('SQLITE event QUERY:', query, values)

