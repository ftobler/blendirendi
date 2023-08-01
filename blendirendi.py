#tornado needs this or it does not run
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from bottle import route, run, template, request, response, static_file
import os
import shutil
import sqlite3
import json
import traceback
import time
import sys
import requests
import subprocess
from PIL import Image
from zipfile import ZipFile, ZipInfo
from io import RawIOBase
import psutil
import socket
import cpuinfo


#reqired librarys:
'''
psutil
Pillow (PIL)
bottle (not anymore)
tornado
py-cpuinfo
requests

'''

#todo
'''
Login
GPU/CPU detection
output format
SSL
Automatic Render crash control
multi file scenes (.zip)
rename job file

'''

#status in db table frame
'''
0 = not rendered/reset
1 = in progress
2 = completed
3 = disabled

'''

#print welcome text
print("  _     _                _ _                    _ _ ")
print(" | |   | |              | (_)                  | (_)")
print(" | |__ | | ___ _ __   __| |_ _ __ ___ _ __   __| |_ ")
print(" | '_ \\| |/ _ \\ '_ \\ / _` | | '__/ _ \\ '_ \\ / _` | |")
print(" | |_) | |  __/ | | | (_| | | | |  __/ | | | (_| | |")
print(" |_.__/|_|\\___|_| |_|\\__,_|_|_|  \\___|_| |_|\\__,_|_|")
print("                                                    ")
print("blendirendi by ftobler")


#initialize config file
config_file = open("blendirendi.json", "r")
settings = json.load(config_file)
config_file.close()


#some global main configuration
is_server = True  #default mode is server
server_url = "http://localhost:8080"
blender_path = "./blender2.92/blender.exe"
port = 8080
listen = "0.0.0.0"

server_url   = settings["client"]["server_url"]
blender_path = settings["client"]["blender_path"]
port         = settings["server"]["port"]
listen       = settings["server"]["listen"]







#fetch client/server mode from arguments
if len(sys.argv) >= 2:
    if sys.argv[1] == "server":
        is_server = True
    if sys.argv[1] == "client":
        is_server = False
if is_server:
    print("starting in SERVER mode")
else:
    print("starting in CLIENT mode")


#initialization stuff to do in SERVER mode
if is_server:
    dbtemplate = "blendirendidefault.db"
    dblocation = "data/blendirendi.db"
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(dblocation):
        print("create new db")
        shutil.copyfile(dbtemplate, dblocation)
    db = sqlite3.connect(dblocation)


#initialization stuff to do in CLIENT mode
if not is_server:
    try:
        shutil.rmtree("cache")
    except:
        traceback.print_exc()
        pass
    if not os.path.exists("cache"):
        os.makedirs("cache")


#return the current epoch milliseconds
def current_milli_time():
    return round(time.time() * 1000)


#handle the login. Currently does nothing
def assertLogin():
    #print("request incoming")
    #session = request.get_cookie("sessionid")
    #print(session)
    return False


#handle server exception
#sends predefined error format out
def resp_exception(reason):
    return json.dumps({"exception":reason})


#convert a string to integer with a default
def toint(str, default=0):
    try:
        return int(str)
    except Exception:
        return default


#convert a string to inteboolean ger with a default
def tobool(str, default=False):
    try:
        str = str.lower()
        if str=="on" or str=="true" or str=="1" or str=="yes":
            return True
        if str=="off" or str=="false" or str=="0" or str=="no":
            return False
    except Exception:
        pass
    return default

#bottle web handler
#serve (static) start page
@route('/')
def home():
    return static_file("blendirendi.html", root='web')


#bottle web handler
#serve a generic (static) file
@route('/<name>')
def home(name):
    return static_file(name, root='web')


#bottle web api handler
#get list of all current jobs
@route('/api/jobs')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    #cursor.execute("""select * from jobs where status=? and enabled=?""", (0,1))
    '''cursor.execute("select * from job order by status desc")
    jobs = []
    for row in cursor:
        jobs.append({"id": row[0], "name": row[1], "enabled": row[2], "status": row[3], "priority": row[4], "framestart": row[5],"frameend": row[6]})
    return json.dumps({"jobs":jobs})'''

    cursor.execute("select * from job join (select idjob, status, count(idjob) as count from frame group by idjob, status) where id=idjob order by job.id")
    jobs = []
    job = {}
    jobidold = None
    for row in cursor:
        jobid = row[0]
        if jobid != jobidold:
            job = {} #new job
            jobs.append(job)
            job["id"] = row[0]
            job["name"] = row[1]
            job["enabled"] = row[2]
            job["priority"] = row[3]
            job["framestart"] = row[4]
            job["frameend"] = row[5]
            job["memory"] = row[6]
            job["starttime"] = row[7]
            job["endtime"] = row[8]
            job["count_pending"] = 0
            job["count_rendering"] = 0
            job["count_done"] = 0
        if row[10] == 0:
            job["count_pending"] = row[11]
        elif row[10] == 1:
            job["count_rendering"] = row[11]
        elif row[10] == 2:
            job["count_done"] = row[11]
        jobidold = jobid
    return json.dumps({"jobs":jobs})


#bottle web api handler
#get detail of a job
@route('/api/job')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()

    job_id = toint(request.query['id'], default=None)

    cursor.execute("select * from job join (select idjob, status, count(idjob) as count from frame group by idjob, status) where id=idjob and id=?", (job_id,))
    job = {} #new job
    first = True
    for row in cursor:
        if first:
            first = False
            job["id"] = row[0]
            job["name"] = row[1]
            job["enabled"] = row[2]
            job["priority"] = row[3]
            job["framestart"] = row[4]
            job["frameend"] = row[5]
            job["memory"] = row[6]
            job["starttime"] = row[7]
            job["endtime"] = row[8]
            job["count_pending"] = 0
            job["count_rendering"] = 0
            job["count_done"] = 0
        if row[10] == 0:
            job["count_pending"] = row[11]
        elif row[10] == 1:
            job["count_rendering"] = row[11]
        elif row[10] == 2:
            job["count_done"] = row[11]

    cursor.execute("select * from frame where idjob=? order by nr asc", (job_id,))
    frames = []
    for row in cursor:
        frames.append({"id": row[0], "nr": row[2], "status": row[3], "renderer": row[4], "starttime": row[5], "endtime": row[6]})
    return json.dumps({"job": job, "frames": frames})


#bottle web api handler
#delete a job
@route('/api/delete', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        job_id = toint(request.query["id"], default=None)
        print(job_id)
        cursor.execute("delete from job where id=?", (job_id,))
        cursor.execute("delete from frame where idjob=?", (job_id,))
        try:
            shutil.rmtree("data/%d" % job_id)
        except:
            traceback.print_exc()
            pass
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#modify a job
@route('/api/jobmod', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        job_id = toint(request.query["id"], default=None)
        if "enable" in request.query:
            enable = tobool(request.query["enable"])
            print(job_id)
            cursor.execute("update job set enabled=? where id=?", (1 if enable else 0, job_id))
        if "priority" in request.query:
            prority = toint(request.query["priority"])
            print(job_id)
            cursor.execute("update job set priority=? where id=?", (prority, job_id))
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#modify a image
@route('/api/framemod', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        image_id = toint(request.query["id"], default=None)
        delete_image_file = False

        if "reset" in request.query:
            cursor.execute("update frame set status=0, renderer='' where id=?", (image_id,))
            delete_image_file = True
        if "skip" in request.query:
            cursor.execute("update frame set status=3, renderer='' where id=?", (image_id,))
            delete_image_file = True

        if delete_image_file:
            cursor.execute("select idjob, nr from frame where id=?", (image_id,))
            data = cursor.fetchone()
            job_id = data[0]
            frame_nr = data[1]
            try:
                os.remove("data/%d/%04d.png" % (job_id, frame_nr))
            except Exception:
                pass #might fail if the image is not present
            try:
                os.remove("data/%d/%04d_thumb.png" % (job_id, frame_nr))
            except Exception:
                pass #might fail if the image is not present
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#upload new job
@route('/api/upload', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        startframe = toint(request.forms.get('startframe'), default = 1)
        endframe = toint(request.forms.get('endframe'), default=1)
        enable = tobool(request.forms.get('enable'), default=False)
        priority = toint(request.forms.get('priority'), default=0)
        memory = toint(request.forms.get('memory'), default=4)
        upload = request.files.get('upload')

        '''print("startframe")
        print(startframe)
        print("endframe")
        print(endframe)
        print("enable")
        print(enable)
        print("priority")
        print(priority)
        print("upload")
        print(upload)'''

        if startframe > endframe:
            endframe = startframe

        cursor.execute("insert into job (name, enabled, priority, framestart, frameend, memory, starttime) values (?, ?, ?, ?, ?, ?, ?)", (upload.filename, enable, priority, startframe, endframe, memory, current_milli_time()))
        
        cursor.execute("select id from job order by id desc limit 1")
        job_id = cursor.fetchone()[0]

        for framenr in range(startframe, endframe+1):
            cursor.execute("insert into frame (idjob, nr) values (?, ?)", (job_id, framenr))

        os.makedirs("data/%d" % (job_id,))
        print("save uploaded new job file")
        upload.save("data/%d/%s" % (job_id, upload.filename))

        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#render node get new job (eat blend)
@route('/api/eat', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        renderer = request.query['renderer']
        freemem = request.query['freemem']

        #get next edible frame job
        cursor.execute("select job.id, frame.id, frame.nr, job.name from job, frame where job.id = frame.idjob and job.enabled=1 and (frame.status=0 or (frame.status=1 and renderer=?)) and memory<=? order by job.priority desc, job.id asc, frame.nr asc limit 1", (renderer,freemem))
        data = cursor.fetchone()
        if data == None:
            #nothing available
            db.execute("commit transaction")
            return json.dumps({"exception":"no job available"})
        else:
            job_id = data[0]
            frame_id = data[1]
            frame_nr = data[2]
            job_name = data[3]

            cursor.execute("update frame set status=1, renderer=?, starttime=?, endtime=0 where id=?", (renderer, current_milli_time(), frame_id))
            cursor.fetchone()

            db.execute("commit transaction")
            return json.dumps({"job_id": job_id, "frame_id": frame_id, "frame_nr": frame_nr, "job_name": job_name})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#render node finish and upload a frame (poop out frame)
@route('/api/poop', method='POST')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        db.execute("begin transaction")
    except:
        pass
    try:
        frame_id = toint(request.query['frame_id'])
        success = tobool(request.query['success'])

        if success:
            #save the uploaded file
            print("save the uploaded frame file")
            upload = request.files.get('upload')
            cursor.execute("select idjob, nr from frame where id=?", (frame_id,))
            data = cursor.fetchone()
            job_id = data[0]
            frame_nr = data[1]
            filename_norm = "data/%d/%04d.png" % (job_id, frame_nr)
            filename_thumb = "data/%d/%04d_thumb.png" % (job_id, frame_nr)
            if not os.path.exists(filename_norm):
                upload.save(filename_norm)

            try:
                im = Image.open(filename_norm).convert('RGB')
                im.thumbnail((300,170))
                im.save(filename_thumb)
            except Exception:
                traceback.print_exc()
                print("creating thumbnail failed")
            
            #mark it in db as completed
            cursor.execute("update frame set status=2, endtime=? where id=?", (current_milli_time(), frame_id))
            cursor.execute("update job set endtime=? where id in (select job.id as id from frame, job where job.id=? and frame.idjob=job.id and frame.status>=2)", (current_milli_time(), job_id))
        else:
            #mark it in db as free
            print("client reportet some failure")
            cursor.execute("update frame set status=0, endtime=? where id=?", (current_milli_time(), frame_id,))

        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#serve the blend file of a job
@route('/api/blend')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    cursor = db.cursor()
    try:
        job_id = toint(request.query['id'])

        cursor.execute("select name from job where job.id=?", (job_id,))
        filename = cursor.fetchone()[0]
        print(filename)
        return static_file("data/%d/%s" % (job_id, filename), root='.')
    except Exception as e:
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#serve a rendered image file
@route('/api/frame')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    try:
        job_id = toint(request.query['id'])
        frame_no = toint(request.query['nr'])

        return static_file("data/%d/%04d.png" % (job_id, frame_no), root='.')
    except Exception as e:
        traceback.print_exc()
        return resp_exception(str(e))


#bottle web api handler
#serve a thumbnail of rendered image file
@route('/api/thumbnail')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    try:
        job_id = toint(request.query['id'])
        frame_no = toint(request.query['nr'])

        return static_file("data/%d/%04d_thumb.png" % (job_id, frame_no), root='.')
    except Exception as e:
        traceback.print_exc()
        return resp_exception(str(e))


#helper class for zipping file
#implements a stream which the ZIP object can write to instead of a file on disk
class UnseekableStream(RawIOBase):
    def __init__(self):
        self._buffer = b''
    def writable(self):
        return True
    def write(self, b):
        if self.closed:
            raise ValueError('Stream was closed!')
        self._buffer += b
        return len(b)
    def get(self):
        chunk = self._buffer
        self._buffer = b''
        return chunk


#helper function for zipping file
#generates (yield) the zip file
def zipfile_generator(files, stream):
    stream = UnseekableStream()
    with ZipFile(stream, mode='w') as zf:
        for file, name in files:
            zf.write(file, arcname=name)
            yield stream.get()
    # ZipFile was closed.
    yield stream.get()


#helper function for zipping file
#generates (yield) the zip file
def zipfile_generator2(files, stream):
    with ZipFile(stream, mode='w') as zf:
        for path, name in files:
            z_info = ZipInfo.from_file(path, arcname=name)
            with open(path, 'rb') as entry, zf.open(z_info, mode='w') as dest:
                for chunk in iter(lambda: entry.read(16384), b''):
                    dest.write(chunk)
                    # Yield chunk of the zip file stream in bytes.
                    yield stream.get()
    # ZipFile was closed.
    yield stream.get()


#bottle web api handler
#download all frames of a job as ZIP file
@route('/api/multiframe')
def index():
    if assertLogin():
        return resp_exception("not logged in")
    try:
        job_id = toint(request.query['id'])
        
        searchpath = "data/%d" % job_id
        files = [(os.path.join(searchpath, f), f) for f in os.listdir(searchpath) if os.path.isfile(os.path.join(searchpath, f)) and f.endswith(".png") and not f.endswith("_thumb.png")]

        return zipfile_generator2(files, UnseekableStream())
    except Exception as e:
        traceback.print_exc()
        return resp_exception(str(e))


#Server specific logic
if is_server:
    run(host=listen, port=port, server="tornado")


#################################################################################################################


#downloads the job .blend file to disk if needed
#if already present the file will not be downloaded again.
def cache_blend(job_id, job_name):
    local_directory = "cache/%d" % job_id
    local_blendname = "cache/%d/%s" % (job_id, job_name)
    if os.path.exists(local_blendname):
        print("file already cached  '%s'" % local_blendname)
        return
    else:
        #download blend file
        print("download blend file to '%s'" % local_blendname)
        with requests.get(server_url + "/api/blend?id=%d" % job_id, stream=True, timeout=(10, 300)) as r:
            r.raise_for_status()
            os.makedirs(local_directory)
            with open(local_blendname, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)


#client finished a frame
#uploads this frame to server
def poopout(job_id, frame_nr, frame_id):
    local_framename = "cache/%d/%04d.png" % (job_id, frame_nr)
    if os.path.exists(local_framename):
        print("render successful completed '%s'" % local_framename)
        f = open(local_framename, "rb")
        r = requests.post(server_url + "/api/poop?frame_id=%d&success=true" % frame_id, files={"upload": f}, timeout=10)
        print(r.text)
    else:
        r = requests.post(server_url + "/api/poop?frame_id=%d&success=false" % frame_id, timeout=10)
        print(r.text)
        print("something went wrong - no output. Penalty sleep")
        time.sleep(60)


#automatically emptys cache after some time
last_cache_cleanup = current_milli_time()
def do_cache_cleanup_if_need():
    global last_cache_cleanup
    now = current_milli_time()
    if now - last_cache_cleanup > 1000*60*60*3:
        searchpath = "cache"
        dirs = [os.path.join(searchpath, f) for f in os.listdir(searchpath) if os.path.isdir(os.path.join(searchpath, f))]
        for d in dirs:
            try:
                print("delete: '%s'", d)
                shutil.rmtree(d)
            except Exception:
                pass
        last_cache_cleanup = now



#Client specific logic
#main client working loop
if not is_server:
    renderername = socket.gethostname() + " " + cpuinfo.get_cpu_info()['brand_raw']
    while True:
        try:
            do_cache_cleanup_if_need()
            print("start fetch  job")
            freemem = psutil.virtual_memory()[4]/1024/1024/1024 #free memory in gigabytes
            respjson = json.loads(requests.post(server_url + "/api/eat?renderer=%s&freemem=%f" % (renderername, freemem), timeout=10).text)
            print(respjson)
            if "exception" in respjson:
                print("server has no job. Wait a bit")
                time.sleep(30)
            else:
                job_id = respjson["job_id"]
                frame_id = respjson["frame_id"]
                frame_nr = respjson["frame_nr"]
                job_name = respjson["job_name"]
                cache_blend(job_id, job_name)
                path_to_blend = "cache/%d/%s" % (job_id, job_name)
                blender_output_path = os.path.abspath("cache/%d/" %(job_id)) + "/"
                #Blender Engine Listing:
                #    BLENDER_EEVEE
                #    BLENDER_WORKBENCH
                #    CYCLES
                command = "%s -P setgpu.py -b %s -E CYCLES -o %s -f %d" % (blender_path, path_to_blend, blender_output_path, frame_nr)
                print(command)
                subprocess.run(command) #waits until comleted
                poopout(job_id, frame_nr, frame_id)
        except Exception as e:
            traceback.print_exc()
            time.sleep(5)
        time.sleep(2)
