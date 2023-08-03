# blendirendi
Blendirendi is a distributed Blender render farm. It features a Server with a web based GUI for management and multiple Clients which do the rendering. The clients can run on multiple machines on the same network.

Features:

* single frame or animation mode
* CPU and GPU rendering, based on what is set on Scene
* Use any version of Blender.
* Any number of render client
* Max memory to set for weak clients
* Job priority management
* Job enable/disable
* Image download as *.zip or single files
* Blend file download
* Drag and drop upload
* Built in image viewer
* Reset/skip frames feature


limitations:

* Output format must be .png.
* Limited error handling if a client can't render the scene for any reason (might get stuck)
* Denoising breaks clients running in some VM
* Each frame is rendered in full by a client. No image stacking.
* *.zip file download might break server if archive gets too big
* No client management from web gui
* No user login
* Manual config needed in *.json file
* No Serverside disk usage monitoring

under the hood:

* written in python
* Bottle webserver with Tornado
* SQLite database
* single page web frontent with Vue

---

![GUI Screenshot](media/gui.png)
![Server Screenshot](media/server.png)
![Client Screenshot](media/client.png)