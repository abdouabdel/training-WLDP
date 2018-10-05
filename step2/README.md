# Developing with Openshift as a back-end

In this step, we will develop a `names` service that generates random names. We will then modify the `hello` service to call this new service.

It will give us the opportunity to see how to develop efficiently with Openshift, and introduce you the `ocd` tool.

## The `names` service

To generate random names, we will use the existing python `names` package: <https://pypi.python.org/pypi/names/>. You can install it locally with: `pip install names`

> `pip` is the standard python module installer. If not already installed as part of your python installation, install it. With `yum`, you can do `yum install python2-pip`. Else , you can have a look at: <https://pip.pypa.io/en/stable/installing/>

## Run the app locally

Same as the previous `hello` app, open a command line shell and run:

```bash
python names/src/app.py
```

```bash
$ python names/src/app.py
starting names server (pid=10528)...
listening on 127.0.0.1:8080
```
Point your browser at <http://localhost:8080/> and refresh a few times, you should see different generated name, e.g.

```
William Howell
```

## Deploy it to Openshift

Now, let's deploy it to Openshift, beside the previous `hello` service. This service is an internal one, so will will not expose it publicly. After the [step1](../step1/), you should be able to do it yourself as an exercise. Here is the output all in a row:

```bash
$ docker build -t wldp-dev-training/names .
...
Successfully built bcf4aea85d87
$ docker tag wldp-dev-training/names docker-registry-default.wldp.fr:443/training-test/names:latest
$ docker login -u unused -p $(oc whoami -t) docker-registry-default.wldp.fr:443
Login Succeeded
$ docker push docker-registry-default.wldp.fr:443/training-test/names:latest
...
$ oc get imagestreams
NAME      DOCKER REPO                             TAGS      UPDATED
hello     172.30.8.127:5000/training-test/hello   latest    42 minutes ago
names     172.30.8.127:5000/training-test/names   latest    39 seconds ago
$ oc new-app --image-stream names:latest
--> Found image bcf4aea (23 minutes old) in image stream "training-test/names" under tag "latest" for "names:latest"

    LDP Traning - Step 1 - Hello
    ----------------------------
    WLDP Traning - Step 1 - Hello

    Tags: wldp, training

    * This image will be deployed in deployment config "names"
    * Port 8080/tcp will be load balanced by service "names"
      * Other containers can access this service through the hostname "names"

--> Creating resources ...
    deploymentconfig "names" created
    service "names" created
--> Success
    Run 'oc status' to view your app.

```

Here we are:

```bash
$ oc get dc,pods,svc
NAME       REVISION   DESIRED   CURRENT   TRIGGERED BY
dc/hello   1          2         2         config,image(hello:latest)
dc/names   1          1         1         config,image(names:latest)

NAME               READY     STATUS    RESTARTS   AGE
po/hello-1-2pl5l   1/1       Running   0          45m
po/hello-1-q9q7s   1/1       Running   0          45m
po/names-1-dtk80   1/1       Running   0          1m

NAME        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
svc/hello   172.30.218.227   <none>        8080/TCP   46m
svc/names   172.30.74.92     <none>        8080/TCP   1m
```

## `oc rsh` and service name resolution in the cluster

Let's introduce `oc rsh` that let's you open a shell in a pod. We will open a shell in one of the `hello` pods, then call the `names` service:

```bash
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-12-m1l05   1/1       Running   0          20s
hello-12-xcrf8   1/1       Running   0          19m
names-4-j2cn7    1/1       Running   0          13m
$ oc rsh hello-12-m1l05
sh-4.2$  curl http://names:8080
William Henderson
```
We see that we can query the `names` service with the short url <http://names:8080>. This is thanks to the built-in DNS service inside Openshift.

> More info at: <https://docs.openshift.org/{{book.osversion}}/architecture/additional_concepts/networking.html#architecture-additional-concepts-openshift-dns>

We would like then to modify our `hello` service to query the `names` service the same way (<http://names:8080>). As this short url will resolve **only from inside the cluster** and because **we do not want** to deploy the `hello` service every time whe change a line of code, we will then introduce the `ocd` tool.

## The `ocd` tool

The `ocd` tool will allow you top transparently connect your local computer to the deployed services in your project. That means that, with the help of `ocd`, we will be able to modify the local running instance of the `hello` service to query the deployed private instance of the `names` service.

We could do the same for any service deployed in the project (database, message broker, ...)

That way, you can just focus on the service you're developing locally without running the full architecture (which could be resource consuming in the case of microservice architectures).

### Get the tool

* You can find it here: [ocd.zip](https://gitlab.kazan.atosworldline.com/deepskyproject/wldp-dev-tools/builds/artifacts/master/download?job=build-command-line-release)

* The archive contains the `ocd` tool binary compiled for **Mac**, **Windows** and **Linux** (32bits and 64bits)

```bash
$ unzip -l ocd.zip
Archive:  ocd.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  06-20-2017 10:20   artifacts/
  6463817  06-20-2017 10:20   artifacts/ocd-master-6d40eeb-linux-32bit
  7524997  06-20-2017 10:20   artifacts/ocd-master-6d40eeb-linux-64bit
  7419808  06-20-2017 10:20   artifacts/ocd-master-6d40eeb-mac
  7386112  06-20-2017 10:20   artifacts/ocd-master-6d40eeb-windows.exe
---------                     -------
```

* Pick the binary that suits you, rename it `ocd` (or `ocd.exe` for Windows), and move it somewhere in your `PATH`

* Check installation

```bash
$ ocd -version
openshift developer tools by WLDP
branch: develop
commit: 0bb555c
```

* The `ocd` tool **will use your current `oc` context**. So you need to log in to the Openshift cluster, and choose your project using `oc`.
* The `ocd` tools will start a routing pod (named `<local-machine-hostname>.route`) in your project, will discover the declared `Service` objects in your project, then will configure the required ssh tunnels so that those services are exposed locally.
  * the services' names are added to you local `/etc/hosts` file for shortname resolution
  * tunnels are picking free local ip addresses in `127.0.0.0/8` address range
* The `ocd` tool maintains those tunnels until `CTRL+C` is pressed. It then destroys the remote pod and cleanup the `/etc/hosts` file. In the case of `ocd` crash or if has not been stopped properly, you can still clean-up both the router pod and the `/etc/hosts` file with `ocd -clean`

> `ocd` **needs administrative rights** to be able to write the `/etc/hosts` file

> Check that your local firewall authorizes connections to the local `127.0.0.0/8` address range

> Connection to the router pod is done through `oc port-forward` command and rely though on Openshift credentials and security (more info at: <https://docs.openshift.org/{{book.osversion}}/dev_guide/port_forwarding.html>)


## Easy development with `ocd`

On your local development machine, launch `ocd`:

<pre>
λ ocd
Openshift Developer Tools by WLDP
Checking oc credentials: <b>wldptraining</b>
Retrieving current project: <b>training-test</b>
Starting routing pod: <b>efr00418.route</b>
Waiting routing pod to be ready...
Forwarding ssh daemon port: 53892
Requesting services list using oc...
Exposing 3 remote service(s) locally: 
-> 127.1.1.1:8080  <b>hello:8080</b>
-> 127.1.1.2:8080  <b>hello-external:8080</b>
-> 127.1.1.3:8080  <b>names:8080</b>
Updating local /etc/hosts...
Press CTRL+C to stop and clean...
</pre>

We can now query (with `curl` or your favorite browser) the private `names` service deployed on the cluster, with its shortname (`names`) as if we were in a pod deployed in the same project:

```bash
$ curl http://names:8080 
Isaac Fleetwood
```

**Great!** We can modify our `hello` service locally relying on the private `names` service deployed on the cluster!

### Let's see the code...

`hello` service from step1 has been modified in step2 (`step2/hello/src/app.py`) to call the `names` service. See below the difference:

#### step1 code

Here is the relevant **step1** code that handle `GET` requests on `/` and that returns `Hello World!`

```python
  def do_GET(self):
    self.protocol_version = 'HTTP/1.1'

    status = 404
    response = "Not Found"

    if (self.path == '/'):
      response = "Hello World!"
      status = 200
```
#### step2 code

In **step2**, we want to call the `names` service from the `hello` service.
* We define two openers to handle requests that need proxy and those which don't (`NOPROXY_OPENER` and `SYSTEMPROXY_OPENER`)
* We define a `get_url` function that return a tuple `(<http_status>, <response>)`. By default it ignores proxy settings (use the `NOPROXY_OPENER`)
* In `do_GET`, we call the `names` service without proxy (`http://names` is only resolvable without proxy): `self.get_url('http://names:8080/')`

```python
import urllib2
```

```python
class HelloServerRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

  # way in python to disable proxy auto-detection to make direct connections 
  NOPROXY_OPENER = urllib2.build_opener(urllib2.ProxyHandler({})) 

  # way in python to rely on system proxy config (env var, ...) 
  SYSTEMPROXY_OPENER = urllib2.build_opener(urllib2.ProxyHandler()) 

  def get_url(self, url, opener=None): 
    if (opener == None): 
      opener = HelloServerRequestHandler.NOPROXY_OPENER 
    try: 
      response = opener.open(url) 
      status = response.getcode(); 
      res = response.read() 
      return (200, res) 
    except urllib2.HTTPError as e: 
      print "[error] Failed to get '%s': %d %s" % (url, e.code, e.reason) 
    except: 
      print "[error] Failed to get '%s':" % (url, sys.exc_info()[0]) 
    return (502, 'Gateway Timeout') 

  def do_GET(self):
    self.protocol_version = 'HTTP/1.1'

    status = 404
    response = "Not Found"
    
    if (self.path == '/'):
      status, name = self.get_url('http://names:8080/') 
      response = 'Hello ' + name + '!\n' 
      
    if status == 502:
      response = "Failed to contact 'names' service"
```

Launch the app locally

```bash
$ python hello/src/app.py
starting hello server (pid=18568)...
listening on 127.0.0.1:8080
```

Point your browser at <http://localhost:8080/>. You should not have `Hello World! `anymore as a response, but something like: and you should see:
```
Hello Richard Curtis!
```

The dynamic name comes from the **private** (not exposed publicly) remote instance of the `names` service deployed on the cluster! 

Once satisfied with the development, you can **build the docker image** of the new version of the `hello` service and https://hello-training-test.wldp.fr. The image push will **trigger the service update**. Do it as an exercise. 

Once done, point your browser at the **publicly** exposed URL of the `hello` service (e.g. <https://hello-training-test.wldp.fr/>). You should not have `Hello World! ` anymore as a response, but something like:

```bash
Hello Mary Kuipers!
```

## Advanced `ocd` : _handle with care_

At the moment, we have 2 `hello` pods running on the cluster. So, when calling <https://hello-training-test.wldp.fr/>, requests are load-balanced between those two pods.

```bash
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-15-4qqgq   1/1       Running   0          1h
hello-15-6m9f4   1/1       Running   0          1h
names-6-jb7pr    1/1       Running   0          4h
```

`ocd` _has another feature, i'll let you judge of its usefulness..._

It can spawn another pod on the cluster redirecting a part of the cluster traffic to your local development machine running instance...

### Setup

* Launch local `hello` instance

```bash
$ python hello/src/app.py
starting hello server (pid=30256)...
listening on 127.0.0.1:8080
```

* In another terminal, launch `ocd` telling it to expose this local instance remotely:

<pre>
$ ocd <b>-s 8080:hello:8080</b>
Openshift Developer Tools by WLDP
release: 0.4.0
Retrieving oc context:
-> cluster: <b>https://master.wldp.fr:443</b>
->    user: <b>wldptraining</b>
-> project: <b>training-test</b>
Starting routing pod: <b>efr00418.route</b>
Waiting routing pod to be ready...
Forwarding ssh daemon port: 45511
Requesting services list using oc...
Exposing 3 remote service(s) locally:
-> 127.1.1.1:8080  <b>hello:8080</b>
-> 127.1.1.3:8080  <b>names:8080</b>
Updating local /etc/hosts...
Exposing local services remotely:
Deploying pods to map local services...
-> mapping service <b>hello</b> through pod <b>efr00418.hello</b>
   -> <b>8080</b> to <b>127.0.0.1:8080</b>
Press CTRL+C to stop and clean...
</pre>

> `ocd` can accept multiple `-s` options

> Syntax: `-s [<local_service_ip>:]<local_service_port>:<service_name>:<service_port>`

* Let's have a look at `hello` service and related pods:

<pre>
$ oc get svc hello -o wide
NAME      CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE       SELECTOR
hello     172.30.218.227   <none>        8080/TCP   3d        <b>app=hello,deploymentconfig=hello</b>
$ oc get pods <b>--selector app=hello,deploymentconfig=hello</b>
NAME                          READY     STATUS    RESTARTS   AGE
hello-15-4qqgq                1/1       Running   0          1h
hello-15-6m9f4                1/1       Running   0          1h
<b>efr00418.hello</b>                1/1       Running   0          16m
</pre>

> `efr00418.hello` is the one spawned by `ocd` that injects your local `hello` instance in the cluster

### Test

* `hello` route has been configured in [step 1](../step1/README.md#expose-the-app-on-internet) to make dumb load-balancing
* We have just seen that we have got **3** pods load balanced by the hello service
* Let's make **3** calls to <https://hello-training-test.wldp.fr>, one of these should be load-balanced to your local instance. Check it on you local instance service logs:

```bash
starting hello server (pid=30256)...
listening on 127.0.0.1:8080
127.0.0.1 - - [23/Jun/2017 16:55:06] "GET / HTTP/1.1" 200 -
```

## Going further

Learn more: [Service discovery and proxy concerns](../step3/)

