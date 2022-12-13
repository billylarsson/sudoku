from PIL             import Image, ImageDraw
from bscripts.tricks import Antihammer, Cutouter, download_file, md5_hash_string
from bscripts.tricks import tech as t, tmp_file
import PIL
import json
import math
import os
import random

class DifferentFolders:
    def __init__(s):
        s.images = {}
        s.basedir = os.environ['BASEDIR'] + os.sep + 'img'
        for var, val in {'flagfiles_folder': 'flagimages', 'continents_folder': 'continents',}.items():
            setattr(s, var, s.basedir + os.sep + val)

class Basic(DifferentFolders):

    def __call__(s, foldername:(list,str), filename:(list,str), units=1, number=False, *args, **kwargs):
        foldername = [foldername] if isinstance(foldername, str) else foldername
        filename = [filename] if isinstance(filename, str) else filename
        key = str(foldername)

        try: filedicts = [x for x in s.images[key]]
        except KeyError:
            s.gather_files_and_folders(foldername)
            filedicts = [x for x in s.images[key]]

        for count in range(len(filedicts)-1,-1,-1):

            if any(x for x in filename if x not in filedicts[count]['filename']) or filename == ['']:
                filedicts.pop(count)
                continue

            elif type(number) == int and filedicts[count]['number'] != number:
                filedicts.pop(count)
                continue

        while filedicts and len(filedicts) < units:

            if units >= len(filedicts) * 2:
                filedicts += filedicts
            else:
                filedicts += filedicts[0:units-len(filedicts)]

        return filedicts[0]['fullpath'] if filedicts and units == 1 else [x['fullpath'] for x in filedicts]

    def gather_files_and_folders(s, foldername:list):
        key = str(foldername)
        s.images[key] = []

        for walk in os.walk(s.basedir):

            for folder in walk[1]:

                if len([x for x in foldername if x in folder]) == len(foldername):  # TODO /flag_files and /files_with_flags is a shared target
                    walkfolder = s.basedir.rstrip(os.sep) + os.sep + folder
                    for walk in os.walk(walkfolder):

                        files = [x[2] for x in os.walk(walkfolder)][0]
                        tmp = [dict(fullpath=walkfolder + os.sep + x, filename=x, folder=walkfolder) for x in files]

                        for fo in tmp:
                            value = ""

                            for i in fo['filename']:
                                if value and not i.isdigit():
                                    break
                                elif i.isdigit():
                                    value += i

                            fo['number'] = int(value) if value else -1

                        tmp.sort(key=lambda x:x['filename'])
                        tmp.sort(key=lambda x:x['number'])

                        tmp1 = [x for x in tmp if x['number'] != -1]
                        tmp2 = [x for x in tmp if x['number'] == -1]

                        s.images[key] = tmp1 + tmp2
                        return walkfolder

class Flag(DifferentFolders):

    def __call__(s, filename:str, *args, **kwargs):
        flag_args = ('flagimages', filename,) if 'foldername' not in kwargs else (filename,)
        return s.basic(*flag_args, *args, **kwargs) or s.filename_extraction(filename, *args, **kwargs)

    def filename_extraction(s, filename, *args, **kwargs):
        try: return s.ff_webp_cache[filename]
        except (AttributeError, KeyError):
            webpfile = s.flagfiles(filename, *args, **kwargs)
            try: s.ff_webp_cache[filename] = webpfile
            except AttributeError: s.ff_webp_cache = {filename: webpfile}
            return s.ff_webp_cache[filename]

    def flagfiles(s, filename, download=True, *args, **kwargs):
        filename = [filename] if isinstance(filename, str) else filename

        def moreplain(string):
            if string.find('(') > 0 and string.find(')') > string.find('('):
                string = string[:string.find('(')-1] + string[string.find(')')+1:]
            for k,v in {' of ':" ", 'st.':'saint', 'dem.':'democratic','rep.':'republic', '.':"", ',':"", '  ':' '}.items():
                string = string.replace(k,v).strip()
            string = string[3:] if string.startswith('the') else string
            string = string[:-3] if string.endswith('the') else string
            return string.strip()

        flagfiles = t.config('flagfiles_urls', curious=True) or s.download_and_update_flagfiles_cache()
        org_filename, filename = ' '.join(filename).lower(), moreplain(' '.join(filename).lower().strip())

        for laps in [False, True]:
            for i in flagfiles:
                country = moreplain(i['country'].lower().strip())

                for k, v in {
                    'republic':"",
                    'democratic':"",
                    'lao pdr':'laos',
                    ' rb':"",
                    "cote d'ivoire":'ivory coast',
                    'darussalam':"",
                    'fed sts':"",
                    'timor-leste':'east timor',
                    'cabo verde':'cape verde',
                    'saint martin': 'sint maarten',
                    'saint eustatius': 'sint eustatius',
                    'turkiye': 'turkey',
                    "people's": 'north',
                    '  ':' ',
                    }.items() if laps else {}:
                    country = country.replace(k, v).strip()
                    filename = filename.replace(k, v).strip()

                startswiths = ('Syria', 'Iran', 'Congo', 'Slovak', 'Kyrgyz', 'Egypt', 'Russia', 'United States', 'Micronesia', 'Czech')
                for change in [x for x in startswiths if i['country'].startswith(x) and filename.startswith(x.lower())] if laps else []:
                    filename = change.lower()
                    country = change.lower()

                filename = 'korea south' if i['country'] == 'Korea, South' and filename == 'korea' else filename
                filename = 'korea north' if i['country'] == 'Korea, North' and filename == 'korea' else filename
                filename = 'us virgin islands' if 'U.S. Virgin Islands' in i['country'] and 'virgin islands' in filename else filename
                criteria_one = country in filename or filename in country
                criteria_two = len(country) >= len(filename) * 0.9 and len(country) <= len(filename) * 1.1

                if laps and criteria_two:
                    for letter in [filename[x] for x in range(len(filename)) if filename[x].isascii()]:
                        if country and not country[0].isascii():
                            country = country[1:]
                        elif letter not in country:
                            break
                        else:
                            country = country[country.find(letter)+1:]
                    else:
                        if len(country) <= 1:
                            criteria_one, criteria_two = True, True

                if criteria_one and criteria_two:
                    webp_file = s.flagfiles_folder + os.sep + i['country'] + '.webp'

                    if not os.path.exists(webp_file) and download:
                        try: s.flagfiles_antihammer()
                        except AttributeError:s.flagfiles_antihammer = Antihammer(timer=0.50, floodlimit=2)
                        png_file = tmp_file(i['url'], reuse=True, extension='png')
                        png_file = download_file(i['url'], png_file, reuse=True) if not os.path.exists(png_file) else png_file
                        try:
                            png_file = Image.open(png_file)
                            png_file.save(webp_file, 'webp', quality=90, method=6)
                            return webp_file
                        except: continue

                    if os.path.exists(webp_file) or not download:
                        return webp_file

    def download_and_update_flagfiles_cache(s):
        flagfiles = t.config('flagfiles_urls') or []

        if not flagfiles and os.path.exists(s.flagfiles_folder + os.sep + 'flags_data.json'):
            with open(s.flagfiles_folder + os.sep + 'flags_data.json') as f:
                flagfiles = json.loads(f.read())
                t.save_config('flagfiles_urls', flagfiles)

        elif not flagfiles and not t.config('anti_flagfiles_hammer'):
            for i in [
                'https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags',
                'https://commons.wikimedia.org/wiki/Flags_of_extinct_states',
                'https://commons.wikimedia.org/wiki/Flags_of_active_autonomist_and_secessionist_movements',
                'https://commons.wikimedia.org/wiki/Dependent_territory_flags']:
                tmpfile = download_file(i, reuse=True, extension='html')
                if not tmpfile:
                    continue

                with open(tmpfile, encoding="UTF-8") as f:
                    org_cont = f.read()
                    cont = org_cont.split('src="https://upload.wikimedia.org/wikipedia')
                    cont = org_cont.split('src="//upload.wikimedia.org/wikipedia') if len(cont) < 10 else cont
                    for i in cont[1:] if len(cont) > 1 else []:
                        tmp = [i.find('</table>')+1, i.find('</li>')+1]

                        try: i = i[0: min(x for x in tmp if x)]
                        except: continue

                        name_co = Cutouter(i, first_find=['title="Flag of', '">'], then_find='</a', forward=True)
                        name_co = Cutouter(i.split('title="w:')[-1], first_find='">', then_find='</a', forward=True) if not name_co else name_co
                        flag_co = Cutouter(i, first_find='/', then_find='"', forward=True)
                        if not name_co or not flag_co:
                            continue

                        flagurl = 'https://upload.wikimedia.org/wikipedia/' + flag_co.text[0: flag_co.text.rfind('/')]
                        tmp = flagurl.split('/')
                        flagurl = '/'.join(tmp) + f"/320px-{tmp[-1]}.png"
                        [setattr(name_co, 'text', name_co.text.replace(x, '')) for x in ('w:', 'Flag of') if name_co.text.startswith(x)]
                        if not [x for x in flagfiles if x['country'] == name_co.text.strip()]:
                            flagfiles.append(dict(country=name_co.text.strip(), url=flagurl.strip())) if '/' not in name_co.text else None

            with open(s.flagfiles_folder + os.sep + 'flags_data.json', 'w') as f:
                f.write(json.dumps(flagfiles))
                t.save_config('flagfiles_urls', flagfiles)
                t.save_config('anti_flagfiles_hammer', True)

        return flagfiles

class Continent(DifferentFolders):

    def __call__(s, *args, **kwargs):
        new_kwgs = s.updated_kwargs(**kwargs)
        generated = s.generate_unique(*args, **new_kwgs)

        if s.basic(foldername='continent', filename=generated):
            return s.basic(foldername='continent', filename=generated)

        elif os.path.exists(tmp_file(generated, hash=False, reuse=True, extension='webp')):
            return tmp_file(generated, hash=False, reuse=True, extension='webp')

        return s.start_work(generated, *args, **new_kwgs)

    def updated_kwargs(s, country=None, countries=None, **kwargs):
        countries = country if not countries else countries
        countries = [countries] if isinstance(countries, dict) else countries
        countries.sort(key=lambda x:x['country']) if isinstance(countries, list) else None
        kwargs.update({'countries': countries})
        return kwargs

    def generate_unique(s, *args, **kwargs):
        gen_args = str(" ".join([str(x) for x in args].sort()) if args else "")
        gen_kwgs = str({k:v for k,v in sorted(kwargs.items(), key=lambda item: item[0])})
        return md5_hash_string(gen_args + gen_kwgs)

    def start_work(s, generated, countries=None, world=True, zoom=False, *args, **kwargs):
        workdict = dict(im=s.create_image(**kwargs), data=s.gather_chunks(*args, **kwargs))
        s.draw_world(workdict, *args, **kwargs) if world else None
        s.draw_countries(workdict, countries, *args, **kwargs) if countries else None
        s.zoom_in_center_fourth_out(workdict, countries, **kwargs) if zoom else None
        return s.save_file(workdict, generated, world, countries)

    def zoom_in_center_fourth_out(s, workdict, countries, **kwargs):
        factor = workdict['im'].width / 360
        chunks, whitelist = [], {x['country'] for x in countries}

        for data in workdict['data']:

            if not s.approval_from_whitelist_and_blacklist(data['properties'], whitelist=whitelist):
                continue

            for chunk in data['chunks'] if data['type'] == 'Polygon' else [x[0] for x in data['chunks']]:
                chunks.append(chunk)

        chunks.sort(key=len)
        for i in chunks[-1:]:  # takes the heaviest chunk and uses that as a center (benefit: avoiding frensh colonies)
            s.cut_world_around_chunks(workdict, [(x[0] * factor + 180 * factor, x[1] * factor + 90 * factor) for x in i], **kwargs)

    def cut_world_around_chunks(s, workdict, chunks, zoom=0.3, width_ratio=2, minwidth=0.1, maxwidth=0.25, **kwargs):
        xmin, xmax = min(x[0] for x in chunks or [(0,0)]), max(x[0] for x in chunks or [(0,0)])
        ymin, ymax = min(x[1] for x in chunks or [(0,0)]), max(x[1] for x in chunks or [(0,0)])
        w, h = xmax - xmin, ymax - ymin
        xmin, ymin, xmax, ymax = (xmin - (w * zoom)), (ymin - (h * zoom)), (xmax + (w * zoom)), (ymax + (h * zoom))

        if minwidth:
            if xmax - xmin < workdict['im'].width * minwidth:
                extra = (workdict['im'].width * minwidth) - (xmax - xmin)
                xmin -= extra * 0.5
                xmax += extra * 0.5

        if maxwidth:
            if xmax - xmin > workdict['im'].width * maxwidth:
                extra = (xmax - xmin) - (workdict['im'].width * maxwidth)
                xmin += extra * 0.5
                xmax -= extra * 0.5

        while ((ymax - ymin) or 1) * width_ratio < ((xmax - xmin) or 1) and ymax - ymin >= 0:
            ymin -= 1
            ymax += 1

        while ((ymax - ymin) or 1) * width_ratio > ((xmax - xmin) or 1) and ymax - ymin < workdict['im'].height:
            ymin += 1
            ymax -= 1

        if ymin < 0:
            ymax += -ymin
            ymin = 0

        if xmin < 0:
            xmax += -xmin
            xmin = 0

        if ymax > workdict['im'].height:
            ymin -= ymax - workdict['im'].height
            ymax = workdict['im'].height

        if xmax > workdict['im'].width:
            xmin -= xmax - workdict['im'].width
            xmax = workdict['im'].width

        xmin, xmax = xmin if xmin > 0 else 0, xmax if xmax < workdict['im'].width else workdict['im'].width
        ymin, ymax = ymin if ymin > 0 else 0, ymax if ymax < workdict['im'].height else workdict['im'].height

        workdict['im'] = workdict['im'].crop((int(xmin), int(ymin), int(xmax), int(ymax)))

    def save_file(s, workdict, generated, world, countries):
        if world and not countries:
            filename = f"{s.continents_folder}{os.sep}World {generated}.webp"
        elif countries and len(countries) == 1:
            for data in workdict['data']:
                if s.approval_from_whitelist_and_blacklist(data['properties'], whitelist={countries[0]['country']}) or countries[0]['country'] == 'World':
                    filename = f"{s.continents_folder}{os.sep}{countries[0]['country']} {generated}.webp"
                    break
            else:
                return False
        else:
            filename = tmp_file(generated, hash=False, reuse=True, extension='webp')

        workdict['im'].transpose(Image.FLIP_TOP_BOTTOM).save(filename, method=6, quality=90)
        return filename

    def create_image(s, im=None, width=None, height=None, **kwargs):
        width = height * 2 if height else 3840
        width = 3840 * 2 if width > 3840 * 2 else width  # decompression bomb
        return im if im else Image.new('RGBA', (math.ceil(width), math.ceil(width / 2)), (0,0,0,0))

    def gather_chunks(s, *args, **kwargs):
        jsonfile = s.continents_folder + os.sep + 'WB_countries_Admin0.geojson'
        if not os.path.exists(jsonfile):
            return

        countries = []
        with open(jsonfile) as f:
            data = json.loads(f.read())['features']

            for count, boundaries in enumerate(data):
                countries.append(
                    dict(
                        chunks=boundaries['geometry']['coordinates'],
                        properties=boundaries['properties'],
                        type=boundaries['geometry']['type'],
                        ))

        return countries

    def draw_world(s, workdict, **kwargs):
        kwgs = {x:True for x in ('fill', 'contours') if x not in kwargs}
        kwargs['whitelist'], kwargs['blacklist'] = {}, {}
        s.draw_entities(workdict, **kwgs, **kwargs)

    def draw_country(s, workdict, country:str, **kwargs):
        kwgs = {x:True for x in ('fill', 'contours') if x not in kwargs}
        kwargs['whitelist'], kwargs['blacklist'] = {country}, {}
        s.draw_entities(workdict, **kwgs, **kwargs)

    def draw_countries(s, workdict, countries:list, **kwargs):
        for i in countries:
            kwgs = {x:True for x in ('fill', 'contours') if x not in i}
            s.draw_country(workdict, **i, **kwgs)

    def draw_entities(s, workdict, fill=False, contours=False, fillcolor=(200,200,200,255), linecolor=(0,0,0,255), linewidth=1, **kwargs):
        factor = workdict['im'].width / 360
        draw = ImageDraw.Draw(workdict['im'])

        for data in workdict['data']:

            if not s.approval_from_whitelist_and_blacklist(data['properties'], **kwargs):
                continue

            poly = dict(fill=data['fillcolor'] if 'fillcolor' in data else fillcolor)
            line = dict(fill=data['linecolor'] if 'linecolor' in data else linecolor)
            line.update(dict(width=data['linewidth'] if 'linewidth' in data else linewidth, joint='curve'))

            for chunk in data['chunks'] if data['type'] == 'Polygon' else [x[0] for x in data['chunks']]:
                chunk = [(x[0] * factor + 180 * factor, x[1] * factor + 90 * factor) for x in chunk]
                draw.polygon(chunk, **poly) if fill else None
                draw.line(chunk, **line) if contours else None

    def approval_from_whitelist_and_blacklist(s, data, whitelist={}, blacklist={}, wb_keys={'WB_NAME', 'NAME_EN', 'FORMAL_EN'}, **kwargs):
        if not whitelist and not blacklist:
            return True

        whitelist = {s.flag.filename_extraction(x, download=False) for x in whitelist} if whitelist else set()
        blacklist = {s.flag.filename_extraction(x, download=False) for x in blacklist} if blacklist else set()

        for i in [s.flag.filename_extraction(v, download=False) for k,v in data.items() if isinstance(k, str) and k in wb_keys]:
            if i and i in blacklist:
                break
            elif i and i in whitelist:
                return i

images = Basic()
flags = Flag()
continent = Continent()

cycle = {'basic': images, 'flag': flags, 'continent': continent}
for var, imgobj  in cycle.items():
    [setattr(v, var, imgobj) for k,v in cycle.items() if v != imgobj and var not in dir(v)]

class SpreadSheetLoader:
    def __init__(s):
        s.images = {}

    def __call__(s, width="", height="", foldername='spreadsheets', filename=None, method=1, quality=100, path=False):

        try: return s.images[path or images(foldername=foldername, filename=filename)]
        except KeyError:
            path = images(foldername=foldername, filename=filename) if not path else path

            if not width and not height:

                for letter in path.split(os.sep)[-1]:
                    if type(width) != int and width and not letter.isdigit():
                        width = int(width)
                    elif type(width) != int and letter.isdigit():
                        width += letter
                    elif type(width) == int and height and not letter.isdigit():
                        height = int(height)
                    elif type(width) == int and letter.isdigit():
                        height += letter

            if type(width) != int and type(height) != int:
                s.images[path] = [[path]]
                return s.images[path]

            s.images[path] = []
            orgimage = Image.open(path)

            while orgimage.height-height >= len(s.images[path]) * height:

                ycrop = (0, height * len(s.images[path]), orgimage.width, height + len(s.images[path]) * height,)
                row = orgimage.crop(ycrop)
                tmp = []

                while row.width-width >= len(tmp) * width:
                    xcrop = (len(tmp) * width, 0, width + len(tmp) * width, height,)
                    img = row.crop((xcrop))

                    if img.mode == 'RGB' or any(x for x in img.getdata() if x[3] != 0):
                        tmpfile = tmp_file(f"{path + str(ycrop) + str(xcrop)}", extension='webp', reuse=True)
                        img.save(tmpfile, method=method, quality=quality)
                        tmp.append(tmpfile)
                    else:
                        break

                if not tmp:
                    break

                s.images[path].append(tmp)

            return s.images[path] if path in s.images else False

spreadsheets = SpreadSheetLoader()


def save_rgb_data_new_file(open_image, tmpfile, destination_image_datas):
    new_im = Image.new('RGBA', open_image.size)
    new_im.putdata(destination_image_datas)
    new_im.save(tmpfile, 'webp', method=1, quality=100)
    [x.close() for x in (new_im, open_image)]
    return tmpfile if os.path.exists(tmpfile) else False

def full_alpha(rgb_data):
    if len(rgb_data) > 3 and rgb_data[-1] == 0:
        return True

def source_color_match(rgb_data, rgb_find_color, span, **kwargs):
    for i in range(len('RGB')):
        if rgb_data[i] - span > rgb_find_color[i]:
            return False
        elif rgb_data[i] + span < rgb_find_color[i]:
            return False
    return True

def prework_resize_image(open_image, width=False, height=False, **kwargs):
    if width and open_image.width != width or height and open_image.height != height:
        size = int(width if width else open_image.width), int(height if height else open_image.height)
        open_image, _ = open_image.resize(size, Image.LANCZOS), open_image.close()

    return open_image

def open_image_file_and_getdatas(source_image_path, **kwargs):
    try:
        open_image = Image.open(source_image_path)
        open_image = prework_resize_image(open_image, **kwargs)
        return open_image, open_image.getdata()
    except PIL.UnidentifiedImageError:
        raise PIL.UnidentifiedImageError
        return False, False
    except:
        print(f'ERROR LOADING: {source_image_path}')
        return False, False

def change_rgb_datalist(open_image, image_rgb_datalist, rgb_find_color, rgb_replace_color, span):
    destination_image_datas = []

    for y in range(open_image.height):
        for x in range(open_image.width):

            index = (y * open_image.width) + x
            rgb_data = image_rgb_datalist[index]

            if not full_alpha(rgb_data=rgb_data):

                if source_color_match(rgb_data=rgb_data, rgb_find_color=rgb_find_color, span=span):
                    destination_image_datas.append(rgb_replace_color)
                    continue

            destination_image_datas.append(rgb_data)

    return destination_image_datas

def sanitize_rgb_data(rgb_data):
    if any(True for x in rgb_data[:3] if x > 255 or x < 0):
        rgb_data = [x for x in rgb_data]
        for i in range(len('RGB')):
            rgb_data[i] = 255 if rgb_data[i] > 255 else rgb_data[i]  # sanitize top
            rgb_data[i] = 0 if rgb_data[i] < 0 else rgb_data[i]      # sanitize btm

    return tuple(rgb_data) if not isinstance(rgb_data, tuple) else rgb_data

def max_bright_to_rgb_color(max_bright_rgb_data, current_rgb_data, span):
    if any(True for count, x in enumerate(current_rgb_data[:3]) if x > max_bright_rgb_data[count]):

        rgb = [x for x in current_rgb_data]
        for i in range(len('RGB')):
            rgb[i] = max_bright_rgb_data[i] if rgb[i] > max_bright_rgb_data[i] + span else rgb[i]

        current_rgb_data = sanitize_rgb_data(rgb)

    return tuple(current_rgb_data) if not isinstance(current_rgb_data, tuple) else current_rgb_data

def dissort_rgb_data(rgb_data, lowspan=-25, highspan=25, rnd_threshold=0.95, **kwargs):
    if random.uniform(0, 1) < rnd_threshold:
        new = [0,0,0]
        for i in range(len('RGB')):
            new[i] = rgb_data[i] + random.randint(lowspan, highspan)

        rgb_data = sanitize_rgb_data(new)

    return tuple(rgb_data) if not isinstance(rgb_data, tuple) else rgb_data

def dissort_rgb_datalist(open_image, image_rgb_datalist, rgb_find_color, span, **kwargs):
    destination_image_datas = []

    for y in range(open_image.height):
        for x in range(open_image.width):

            index = (y * open_image.width) + x
            rgb_data = image_rgb_datalist[index]

            if not full_alpha(rgb_data=rgb_data):

                if source_color_match(rgb_data=rgb_data, rgb_find_color=rgb_find_color, span=span):
                    dissorted_rgb_data = dissort_rgb_data(rgb_data, **kwargs)
                    destination_image_datas.append(dissorted_rgb_data)
                    continue

            destination_image_datas.append(rgb_data)

    return destination_image_datas


def dark_gradient_L2R_rgb_datalist(open_image, source_rgb_datalist, rgb_find_color, max_bright_rgb, pixels_per_iter, lowspan, highspan, rnd_threshold, span):
    destination_image_datas = []

    for y in range(open_image.height):
        for x in range(open_image.width):

            index = (y * open_image.width) + x
            rgb_data = source_rgb_datalist[index]

            if not full_alpha(rgb_data=rgb_data):

                if source_color_match(rgb_data=rgb_data, rgb_find_color=rgb_find_color, span=span):

                    kwgs = dict(lowspan=lowspan + int(pixels_per_iter * x), highspan=highspan + int(pixels_per_iter * x))
                    dissorted_rgb_data = dissort_rgb_data(rgb_data, rnd_threshold=rnd_threshold, **kwgs)
                    dissorted_rgb_data = max_bright_to_rgb_color(max_bright_rgb, dissorted_rgb_data, span)
                    destination_image_datas.append(dissorted_rgb_data)
                    continue

            destination_image_datas.append(rgb_data)

    return destination_image_datas

def replace_rgb_with_rgb_new_file(source_image_path, rgb_find_color, rgb_replace_color, span=10, **kwargs):
    distinguish = f"{source_image_path} {rgb_find_color} {rgb_replace_color}"
    tmpfile = tmp_file(distinguish, reuse=True, extension='webp')

    if not os.path.exists(tmpfile):
        open_image, source_rgb_datalist = open_image_file_and_getdatas(source_image_path=source_image_path, **kwargs)

        if open_image:
            change_args = open_image, source_rgb_datalist, rgb_find_color, rgb_replace_color
            destination_image_datas = change_rgb_datalist(*change_args, span=span)
            tmpfile = save_rgb_data_new_file(open_image, tmpfile, destination_image_datas)

    return tmpfile if os.path.exists(tmpfile) else False

def add_rgb_dissort_new_file(source_image_path, rgb_find_color, lowspan=-25, highspan=25, rnd_threshold=0.95, span=10, **kwargs):
    distinguish = f"{source_image_path} {rgb_find_color} {lowspan} {highspan} {rnd_threshold}"
    tmpfile = tmp_file(distinguish, reuse=True, extension='webp')
    if not os.path.exists(tmpfile):
        open_image, source_rgb_datalist = open_image_file_and_getdatas(source_image_path=source_image_path, **kwargs)

        if open_image:
            kwgs = dict(rgb_find_color=rgb_find_color, rnd_threshold=rnd_threshold, lowspan=lowspan, highspan=highspan)
            destination_image_datas = dissort_rgb_datalist(open_image, source_rgb_datalist, span=span, **kwgs)
            tmpfile = save_rgb_data_new_file(open_image, tmpfile, destination_image_datas)

    return tmpfile if os.path.exists(tmpfile) else False

def dark_gradient_L2R_new_file(source_image_path, left_rgb_color, max_bright_rgb=None, lowspan=-100, highspan=-50, rnd_threshold=0.95, span=10, reach=0.6, **kwargs):
    distinguish = f"{source_image_path} {left_rgb_color} {lowspan} {highspan} {rnd_threshold} {max_bright_rgb} {reach}"
    tmpfile = tmp_file(distinguish, reuse=True, extension='webp')
    if not os.path.exists(tmpfile):
        open_image, source_rgb_datalist = open_image_file_and_getdatas(source_image_path=source_image_path, **kwargs)

        if open_image:
            gradient_width = open_image.width * reach
            gradient_increment = (highspan - lowspan) / gradient_width
            gradient_args = open_image, source_rgb_datalist, left_rgb_color, max_bright_rgb or left_rgb_color
            kwgs = dict(lowspan=lowspan, highspan=highspan, rnd_threshold=rnd_threshold, span=span, pixels_per_iter=gradient_increment)
            destination_image_datas = dark_gradient_L2R_rgb_datalist(*gradient_args, **kwgs)
            tmpfile = save_rgb_data_new_file(open_image, tmpfile, destination_image_datas)

    return tmpfile if os.path.exists(tmpfile) else False
