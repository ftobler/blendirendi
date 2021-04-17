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




print("blendirendi by ftobler")

is_server = False  #default mode
server_url = "http://localhost:8080"
blender_path = "./blender2.92/blender.exe"

if len(sys.argv) >= 2:
    if sys.argv[1] == "server":
        is_server = True
    if sys.argv[1] == "client":
        is_server = False
if is_server:
    print("starting in SERVER mode")
else:
    print("starting in CLIENT mode")

dbtemplate = "blendirendidefault.db"
dblocation = "data/blendirendi.db"

if is_server:
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(dblocation):
        print("create new db")
        shutil.copyfile(dbtemplate, dblocation)
    db = sqlite3.connect(dblocation)
if not is_server:
    if not os.path.exists("cache"):
        os.makedirs("cache")


#status in db table frame
# 0 = not rendered/reset
# 1 = in progress
# 2 = completed
# 3 = disabled




def current_milli_time():
    return round(time.time() * 1000)

def assertLogin():
    print("request incoming")
    #session = request.get_cookie("sessionid")
    #print(session)
    return False

def resp_exception(reason):
    return json.dumps({"exception":reason})

def toint(str, default=0):
    try:
        return int(str)
    except Exception:
        return default

def tobool(str, default=False):
    print(str)
    try:
        str = str.lower()
        if str=="on" or str=="true" or str=="1" or str=="yes":
            return True
        if str=="off" or str=="false" or str=="0" or str=="no":
            return False
    except Exception:
        pass
    return default

#serve start page
@route('/')
def home():
    return static_file("blendirendi.html", root='.')

#serve a generic file
@route('/<name>')
def home(name):
    return static_file(name, root='.')

#examples
@route('/hello/<name>')
def index(name):
    return template('<b>Hello {{name}}</b>!', name=name)

        



#API jobs
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
            job["count_pending"] = 0
            job["count_rendering"] = 0
            job["count_done"] = 0
        if row[7] == 0:
            job["count_pending"] = row[8]
        elif row[7] == 1:
            job["count_rendering"] = row[8]
        elif row[7] == 2:
            job["count_done"] = row[8]
        jobidold = jobid
    return json.dumps({"jobs":jobs})


#API jobs
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
            job["count_pending"] = 0
            job["count_rendering"] = 0
            job["count_done"] = 0
        if row[7] == 0:
            job["count_pending"] = row[8]
        elif row[7] == 1:
            job["count_rendering"] = row[8]
        elif row[7] == 2:
            job["count_done"] = row[8]

    cursor.execute("select * from frame where idjob=? order by nr asc", (job_id,))
    frames = []
    for row in cursor:
        frames.append({"id": row[0], "nr": row[2], "status": row[3], "renderer": row[4], "date": row[5]})
    return json.dumps({"job": job, "frames": frames})


#API delete
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
        
        print("commit")
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#API job modification
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
        
        print("commit")
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))

#API image modification
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
            cursor.execute("update frame set status=0, renderer='', date='' where id=?", (image_id,))
            delete_image_file = True
        if "skip" in request.query:
            cursor.execute("update frame set status=3, renderer='', date=''  where id=?", (image_id,))
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

        print("commit")
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


#API upload
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

        cursor.execute("insert into job (name, enabled, priority, framestart, frameend) values (?, ?, ?, ?, ?)", (upload.filename, enable, priority, startframe, endframe))
        
        cursor.execute("select id from job order by id desc limit 1")
        job_id = cursor.fetchone()[0]

        for framenr in range(startframe, endframe+1):
            cursor.execute("insert into frame (idjob, nr) values (?, ?)", (job_id, framenr))

        os.makedirs("data/%d" % (job_id,))
        upload.save("data/%d/%s" % (job_id, upload.filename))

        print("commit")
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


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

        #get next edible frame job
        cursor.execute("select job.id, frame.id, frame.nr, job.name from job, frame where job.id = frame.idjob and job.enabled=1 and (frame.status=0 or (frame.status=1 and renderer=?)) order by job.priority desc, frame.nr asc limit 1", (renderer,))
        data = cursor.fetchone()
        if data == None:
            #nothing available
            print("commit")
            db.execute("commit transaction")
            return json.dumps({"exception":"no job available"})
        else:
            job_id = data[0]
            frame_id = data[1]
            frame_nr = data[2]
            job_name = data[3]

            cursor.execute("update frame set status=1, renderer=?, date=? where id=?", (renderer, current_milli_time(), frame_id))
            cursor.fetchone()

            print("commit")
            db.execute("commit transaction")
            return json.dumps({"job_id": job_id, "frame_id": frame_id, "frame_nr": frame_nr, "job_name": job_name})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


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
            print("save the uploaded file")
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
            cursor.execute("update frame set status=2, date=? where id=?", (current_milli_time(), frame_id))
        else:
            #mark it in db as free
            print("client reportet some failure")
            cursor.execute("update frame set status=0, date=? where id=?", (current_milli_time(), frame_id,))

        print("commit")
        db.execute("commit transaction")
        return json.dumps({})
    except Exception as e:
        print("rollback")
        db.execute("rollback transaction")
        traceback.print_exc()
        return resp_exception(str(e))


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


if is_server:
    run(host="localhost", port=8080, server="tornado")



#mostly client suff after this line

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


if not is_server:
    while True:
        try:
            print("start fetch  job")
            respjson = json.loads(requests.post(server_url + "/api/eat?renderer=test", timeout=10).text)
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
                command = "%s -P setgpu.py -b %s -E CYCLES -o %s -f %d" % (blender_path, path_to_blend, blender_output_path, frame_nr)
                print(command)
                subprocess.run(command) #waits until comleted
                poopout(job_id, frame_nr, frame_id)
        except Exception as e:
            traceback.print_exc()
            time.sleep(5)
        time.sleep(2)
