function start() {

    document.getElementById("app").style.display = "block"

    app = new Vue({
        el: '#app',
        data: {
            active_upload: true,
            active_jobs: true,
            active_job: true,
            active_viewer: false,
            viewer_frame: null,
            jobs: [],
            disk: [1,0,0],
            upload: {
                is_animation: false,
                framestart: 1,
                frameend: 1,
                enable: true,
                priority: 0,
                valid: false,
                error: "",
                info: "",
                memory: 4,
            },
            job: false,
            dragging: false,
            dropped_file: null,
        },
        created() {
            this.reload_jobs()
            setInterval(() => {
                this.reload_jobs()
            }, 60*1000)
        },
        mounted() {
            //after DOM create
            this.setup_drag_drop_listeners()
        },
        methods: {
            reload_jobs: function() {
                ajax({
                    type: "GET",
                    dataType: "application/json",
                    url: "/api/jobs",
                    success: (data) => {
                        var dat = JSON.parse(data)
                        this.jobs = dat.jobs
                        this.disk = dat.disk
                    },
                })
            },

            reload_job: function(job_id) {
                ajax({
                    type: "GET",
                    dataType: "application/json",
                    url: "/api/job" + build_query_parameter({id: job_id}),
                    success: (data) => {
                        let parsed = JSON.parse(data)
                        this.job = parsed.job
                        this.job.frames = parsed.frames
                    },
                })
            },

            action_delete: function(job) {
                if (confirm("Do you really want to delete project '" + job.name + "'?")) {
                    ajax({
                        type: "POST",
                        dataType: "application/json",
                        url: "/api/delete" + build_query_parameter({id: job.id}),
                        success: (data) => {
                            this.job = false
                            this.reload_jobs()
                        },
                    })
                }
            },

            action_reset_frame: function(job, frame) {
                if (confirm("Do you really want to reset frame nr " + frame.nr + " of project '" + job.name + "'?")) {
                    ajax({
                        type: "POST",
                        dataType: "application/json",
                        url: "/api/framemod" + build_query_parameter({id: frame.id, reset: 1}),
                        success: (data) => {
                            this.reload_job(job.id);
                            this.reload_jobs()
                        },
                    })
                }
            },

            action_skip_frame: function(job, frame) {
                if (confirm("Do you really want to skip frame nr " + frame.nr + " of project '" + job.name + "'?")) {
                    ajax({
                        type: "POST",
                        dataType: "application/json",
                        url: "/api/framemod" + build_query_parameter({id: frame.id, skip: 1}),
                        success: (data) => {
                            this.reload_job(job.id);
                            this.reload_jobs()
                        },
                    })
                }
            },

            action_download_frame: function(job, frame) {
                let link = document.createElement("a")
                link.href = "/api/frame" + build_query_parameter({id: job.id, nr: frame.nr})
                link.setAttribute('download', job.name.substr(0, job.name.lastIndexOf(".blend")) + "_" + pad(frame.nr, 4) + ".png")
                link.click()
            },

            action_download_blend: function(job) {
                let link = document.createElement("a")
                link.href = "/api/blend" + build_query_parameter({id: job.id})
                link.setAttribute('download', job.name)
                link.click()
            },

            action_download_multiframe: function(job) {
                let link = document.createElement("a")
                link.href = "/api/multiframe" + build_query_parameter({id: job.id})
                link.setAttribute('download', job.name.substr(0, job.name.lastIndexOf(".blend")) + ".zip")
                link.click()
            },

            action_download_all_files: function(job) {
                var jobs = []
                job.frames.forEach((frame) => {
                    if (frame.status == 2) {
                        jobs.push(frame.nr)
                    }
                })
                console.log(jobs)

                downloadFilesSequentially(job, jobs)
                    .then(() => {
                        console.log('All files downloaded successfully!');
                    })
                    .catch((error) => {
                        console.error('Error during download:', error);
                    });


                // let link = document.createElement("a")
                // link.href = "/api/multiframe" + build_query_parameter({id: job.id})
                // link.setAttribute('download', job.name.substr(0, job.name.lastIndexOf(".blend")) + ".zip")
                // link.click()
            },

            job_save_enabled: function(job) {
                job.enabled = !job.enabled
                ajax({
                    type: "POST",
                    dataType: "application/json",
                    url: "/api/jobmod" + build_query_parameter({id: job.id, enable: job.enabled}),
                    success: (data) => {
                        this.reload_job(job.id);
                        this.reload_jobs();
                    },
                })
            },

            job_save_priority: function(job, delta) {
                job.priority = job.priority + delta
                ajax({
                    type: "POST",
                    dataType: "application/json",
                    url: "/api/jobmod" + build_query_parameter({id: job.id, priority: job.priority}),
                    success: (data) => {
                        this.reload_job(job.id);
                        this.reload_jobs();
                    },
                })
            },

            action_job_click: function(job) {
                if (this.job.id !== job.id) {
                    this.active_job = true
                    this.reload_job(job.id)
                } else {
                    this.job = false;
                    this.active_job = false
                }
            },

            check_form: function(e) {
                if (!this.upload.is_animation) {
                    this.upload.endframe = this.upload.startframe
                }
                console.log(e)
                let formdata = new FormData(e.srcElement)
                console.log(formdata)
                if (this.dropped_file != null) {
                    formdata.append("upload", this.dropped_file)
                }
                this.upload.error = ""
                this.upload.info = "uploading.. please wait."
                fetch('/api/upload', {method: "POST", body: formdata}).then(response => response.json()).then((json) => {
                    this.upload.info = ""
                    console.log(json)
                    if (json.exception != undefined) {
                        this.upload.error = json.exception
                    }
                    this.reload_jobs()
                })
                e.preventDefault(); //always prevent default, because we make everything here in Js!
                //return true
                this.dropped_file = null //clear the dropped file for next time
                document.getElementById("myFile").value = ""
            },

            get_progress: function(job) {
                let total = job.count_pending + job.count_rendering + job.count_done
                if (total == 0) {
                    return 0
                }
                return Math.round(job.count_done / total * 1000) / 10
            },

            setup_drag_drop_listeners: function() {
                const id = "upload_form"
                // const dashclass = "upload_form"
                let ele = document.getElementById(id)

                // Event listener for the dragenter event
                ele.addEventListener("dragenter", (event) => {
                    event.preventDefault()
                    // ele.classList.add(dashclass)
                    // console.log("dragenter")
                    this.dragging = true;
                });
                // Event listener for the dragleave event
                ele.addEventListener("dragleave", (event) => {
                    event.preventDefault()
                    // ele.classList.remove(dashclass)
                    // console.log("dragleave")
                    this.dragging = false;
                });
                // Event listener for the dragover event
                ele.addEventListener("dragover", (event) => {
                    event.preventDefault()
                    // ele.classList.add(dashclass)
                    // console.log("dragover")
                    this.dragging = true;
                });
                // Event listener for the drop event
                ele.addEventListener("drop", (event) => {
                    event.preventDefault()
                    // Get the files that were dropped
                    var files = event.dataTransfer.files
                    console.log(files)
                    // Upload the files to the server
                    // ...
                    console.log("drop")
                    this.dragging = false;
                    this.dropped_file = event.dataTransfer.files[0]
                });
            },

            viewer_start: function(job, frame) {
                this.job = job //should not be needed at most instances, because the job is already set
                this.active_viewer = true
                this.viewer_frame = frame
                document.getElementsByTagName('html')[0].style.scrollbarGutter = "initial"
            },

            viewer_exit: function() {
                this.active_viewer = false
                document.getElementsByTagName('html')[0].style.scrollbarGutter = "stable"
            },

            viewer_nav: function(increment) {
                var index = this.job.frames.indexOf(this.viewer_frame) + increment;
                var new_frame = this.job.frames[index]
                if (new_frame != undefined) {
                    this.viewer_frame = new_frame
                }
            },

            viewer_wheel: function(event) {
                this.viewer_nav(event.deltaY > 0 ? 1 : -1)
            }
        },
        filters: {
            eval_frameset: function(job) {
                if (job.framestart == job.frameend) {
                    return "#" + job.framestart
                } else {
                    return job.framestart  + "-" + job.frameend
                }
            },
            eval_progress: function(job) {
                let total = job.count_pending + job.count_rendering + job.count_done
                if (total == 0) {
                    return "disabled"
                }
                let progress = Math.round(job.count_done / total * 1000) / 10
                if (progress == 100) {
                    return "done"
                }
                if (job.enabled == false) {
                    return "disabled"
                }
                if (progress == 0 && job.count_rendering == 0) {
                    return "waiting"
                }
                if (job.count_rendering > 0) {
                    return progress + "% (" + job.count_rendering + " active)"
                }
                return progress + "%"
            },
            eval_status: function(statusnumber) {
                switch (statusnumber) {
                    case 0: return "new"
                    case 1: return "rendering"
                    case 2: return "done"
                    case 3: return "skip"
                }
                return "" + statusnumber
            },
            eval_rendertime: function(frame) {
                if (frame.starttime == 0) {
                    return "---"
                }
                let starttime = frame.starttime
                let endtime = frame.endtime
                let running = ""
                if (endtime == 0) {
                    endtime = new Date().getTime()
                    running = "+"
                }
                let seconds = (endtime - starttime) / 1000
                if (seconds < 0) {
                    return "---"
                }
                if (seconds < 60) {
                    return Math.round(seconds) + "s" + running
                }
                let minutes = seconds / 60;
                return Math.round(minutes) + "min" + running
            },
            eval_dateformat: function(millis) {
                millis = millis - new Date().getTimezoneOffset()*60*1000
                return new Date(millis).toISOString().replace("T", " ").slice(0, -8).replaceAll("-", "/")
            },
            eval_filesize: function(bytes) {
                if (bytes < 512) {
                    return ""+bytes + "B"
                }
                kb = bytes / 1024
                if (kb < 512) {
                    return kb.toFixed(1) + "kB"
                }
                mb = kb / 1024
                if (mb < 512) {
                    return mb.toFixed(1) + "MB"
                }
                gb = mb / 1024
                if (gb < 10) {
                    return gb.toFixed(2) + "GB"
                }
                return gb.toFixed(1) + "GB"
            }
        }
    })


}


/*
ajax({
	    type: "GET",
	    url: "/something",
		success: (data) => {
	    },
	    dataType: "application/json"
	})
*/
function ajax(setting) {
	if (typeof(shutdown) !== 'undefined') return
	var request = new XMLHttpRequest();
	request.open(setting.type, setting.url, true);
	request.setRequestHeader('Content-Type', setting.dataType)
	request.onload = function(data) {
		if (typeof(shutdown) !== 'undefined') return
		if (this.status >= 200 && this.status < 400) {
			if (setting.success) {
				setting.success(this.response)
			}
		} else {
			if (setting.error) {
				setting.error(this.response)
			}
		}
	}
	request.onerror = function(data) {
		if (typeof(shutdown) !== 'undefined') return
		if (setting.error) {
			setting.error(data)
		}
	}
	if (setting.data) {
		request.send(setting.data)
	} else {
		request.send()
	}
}


function build_query_parameter(obj) {
    let esc = encodeURIComponent;
    if (Object.keys(obj).length == 0) {
        return ""
    }
    return "?" + Object.keys(obj)
        .map(k => esc(k) + '=' + esc(obj[k]))
        .join('&');
}


function pad(num, size) {
    num = num.toString();
    while (num.length < size) num = "0" + num;
    return num;
}

function downloadFilesSequentially(job, nrs) {
    var nr = nrs.shift()
    return fetch("/api/frame" + build_query_parameter({id: job.id, nr: nr}))
        .then(response => response.blob())
        .then(blob => {
            const fileName = job.name.replace(".blend", "_" + formatNumber(nr) + ".png")
            downloadBlob(blob, fileName);
            if (nrs.length) {
                return downloadFilesSequentially(job, nrs)
            }
        });
}

function downloadBlob(blob, fileName) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = fileName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(a.href);
    document.body.removeChild(a);
}

function formatNumber(number) {
    // Convert the number to a string.
    let strNumber = String(number);
    // Calculate the number of leading zeros needed.
    let leadingZeros = 4 - strNumber.length;
    // Pad the string with leading zeros.
    let formattedNumber = "0".repeat(leadingZeros) + strNumber;
    return formattedNumber;
}