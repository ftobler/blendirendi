function start() {

    var app = new Vue({
        el: '#app',
        data: {
            active_upload: true,
            active_jobs: true,
            active_job: true,
            jobs: [],
            upload: {
                is_animation: false,
                framestart: 1,
                frameend: 1,
                enable: true,
                priority: 0,
                valid: false,
                error: "",
                memory: 4,
            },
            job: false
        },
        created() {
            this.reload_jobs()
            setInterval(() => {
                this.reload_jobs()
            }, 60*1000)
        },
        methods: {
            reload_jobs: function() {
                ajax({
                    type: "GET",
                    dataType: "application/json",
                    url: "/api/jobs",
                    success: (data) => {
                        this.jobs = JSON.parse(data).jobs
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
                this.active_job = true
                this.reload_job(job.id)
            },

            check_form: function(e) {
                if (!this.upload.is_animation) {
                    this.upload.endframe = this.upload.startframe
                }
                console.log(e)
                let formdata = new FormData(e.srcElement)
                this.upload.error = ""
                fetch('/api/upload', {method: "POST", body: formdata}).then(data => {
                    console.log(data)
                    let decoded = data.json()
                    if (decoded.exception != undefined) {
                        this.upload.error = decoded.exception
                    }
                    this.reload_jobs()
                });
                e.preventDefault(); //always prevent default, because we make everything here in Js!
                //return true
            },
            get_progress: function(job) {
                let total = job.count_pending + job.count_rendering + job.count_done
                if (total == 0) {
                    return 0
                }
                return Math.round(job.count_done / total * 1000) / 10
            }
        },
        filters: {
            eval_frameset: function(job) {
                if (job.framestart == job.frameend) {
                    return "single " + job.framestart
                } else {
                    return job.framestart  + "-" + job.frameend + " (" + (job.frameend - job.framestart) + "pcs)"
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
                return progress + "% (" + job.count_rendering + " rendering)"
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