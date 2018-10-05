# Hello World on Openshift

Before going any further, we will ensure that we have all the needed tools installed on the local computer.

## Software Requirements

First the main requirements

### Docker
See <https://www.docker.com>. For Linux or Mac, this can be easily installed with the packaged manager. For Windows, depending on the OS version, it might be more simple to setup a Linux virtual machine.

> This tutorial uses a CentOS VM (and not a `boot2docker` one so that you can install other tools)

### The Openshift command line tool: `oc`

You can download the latest release here: <https://github.com/openshift/origin/releases/latest>

It is available for Linux, Mac and Windows. It is a single static binary that you just have to drop in your `PATH`

> When working with a VM, just drop the Linux binary inside your VM `PATH`

### Python

To reduce size of code **to better highlight the Openshift-related concerns**, python has been chosen as a language for sample app. 

This is usually pre-installed on Mac and Linux, you can easily download install bundle for Windows on <https://www.python.org/> (choose version 2.7)


## Run the app locally

>The idea here is to use **your standard development environment**. So if you're used to develop on Windows, make the following run on Windows, not in a virtual machine.

Open a command line and run:

```bash
python hello/src/app.py
```

```bash
$ python hello/src/app.py
starting hello server (pid=10528)...
listening on 127.0.0.1:8080

```

The server listens on port `8080` (unless other one specified, see  `python hello/src/app.py -h`) until `CTRL+C` is pressed. Point your browser at <http://localhost:8080/> and you should see:

```
Hello World!
```

The server also logs the access, and stops on `CTRL-C`

```bash
$ python hello/src/app.py
starting hello server (pid=10528)...
listening on 127.0.0.1:8080
127.0.0.1 - - [15/Jun/2017 11:43:41] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [15/Jun/2017 11:43:41] "GET /favicon.ico HTTP/1.1" 404 -
^Cshutting down server...
server shut down.
```

## Package the app as a `docker` image

> For Windows users with `docker` installed inside vm, run this command in the vm

To build the `docker` image and tag it `wldp-dev-training/hello:latest`

```bash
docker build -t wldp-dev-training/hello .
```

> For the `yum` (or any package manager) to work you need to have internet access without proxy from inside your container. If your docker host has internet access through proxy, run a transparent proxy solution (redsocks, ...).

### Full log

```bash
~/wldp-dev-training/step1/hello $ docker build -t wldp-dev-training/hello .
Sending build context to Docker daemon 8.192 kB
Step 1 : FROM centos:7
 ---> 8140d0c64310
Step 2 : MAINTAINER WLDP Development <dl-fr-deepsky-moe@atos.net>
 ---> Using cache
 ---> f6858dab7791
Step 3 : EXPOSE 8080
 ---> Using cache
 ---> 9b960d489490
Step 4 : LABEL io.k8s.description "WLDP Traning - Step 1 - Hello" io.k8s.display-name "LDP Traning - Step 1 - Hello" io.openshift.expose-services "8080:http" io.openshift.tags "wldp,training"
 ---> Using cache
 ---> a4e4f2b1d972
Step 5 : RUN yum install -y python &&     yum clean all
 ---> Using cache
 ---> 477dfcaa3ff5
Step 6 : ENV HOME /opt/app-root/src PYTHONUNBUFFERED true
 ---> Using cache
 ---> 24e5b4528422
Step 7 : ADD src/app.py run.sh ${HOME}/
 ---> Using cache
 ---> 4097d07352b6
Step 8 : WORKDIR ${HOME}
 ---> Using cache
 ---> 14b6a3842b43
Step 9 : USER 1000
 ---> Using cache
 ---> ff6fabcac001
Step 10 : CMD sh /opt/app-root/src/run.sh
 ---> Using cache
 ---> eca98542c24a
Successfully built eca98542c24a
```

## Inside the `Dockerfile`

> A **very** good starting point, that collect a lot of best practices about writing `Dockerfile` in general and more specifically for images to be run on Openshift: <https://docs.openshift.org/{{book.osversion}}/creating_images/guidelines.html#openshift-specific-guidelines>

### A few explanations

_Some of the previous links patterns in action_

* Inherit a defined base image

```Dockerfile
FROM centos:7
```

* Define a mailing-list as a maintainer

```Dockerfile
MAINTAINER WLDP Development <dl-fr-deepsky-moe@atos.net>
```

* Define the exposed port(s) and avoid privileged ports to target openshift (i.e. chose a port greater than `1024`)

```Dockerfile
EXPOSE 8080
```

* Add label for better UI integration

> More on image metadata: <https://docs.openshift.org/{{book.osversion}}/creating_images/metadata.html>

```Dockerfile
LABEL io.k8s.description="WLDP Traning - Step 1 - Hello" \
  io.k8s.display-name="LDP Traning - Step 1 - Hello" \
  io.openshift.expose-services="8080:http" \
  io.openshift.tags="wldp,training"
```

* Install required packages in a single package manager transaction and clean up just after to reduce image size

```Dockerfile
RUN INSTALL_PKGS="python" && \ 
  yum install -y $INSTALL_PKGS && \
  rpm -V $INSTALL_PKGS && \
  yum clean all
```

* Define required environment variable(s)

```Dockerfile
ENV HOME=/opt/app-root/src PYTHONUNBUFFERED=true
```

* Add you application artifact(s) and entrypoint script. For interpreted languages like python, there is no build step and artifact is the source code itself

```Dockerfile
ADD src/app.py run.sh ${HOME}/
```
* Set the image working directory

```Dockerfile
WORKDIR ${HOME}
```

* Set a user other than `root`/`0`. User id `1001` is a common choice, to test image in non privileged mode. When run on a standard Openshift installation, your image will be run with a random non-root user id. The only thing you can rely on, is that your runtime user will be part of the `root` group (`0`). Keep it in mind when configuring file access

> More explanations and samples here: <https://docs.openshift.org/{{book.osversion}}/creating_images/guidelines.html#use-uid>

```Dockerfile
USER 1001
```

* Define the starting command: calling `sh run.sh` instead of `run.sh` is a good habit that prevent you from setting `x` right to run.sh

```Dockerfile
CMD ["sh", "/opt/app-root/src/run.sh"]
```


> Make sure your application is outputing logs on standard output/error and not on files


## A focus on `run.sh` and `app.py`

*  Set common bash option to have a kind of `bash` _strict mode_  (fails and exit on first command failure, first command in a pipe, fails on undefined variables, ...). In `run.sh`:

```bash
set -euo pipefail
```
* Use `exec` so that your binary (here `python`) replaces the shell process itself so that it can safely receive signals from `docker`.  In `run.sh`:

```bash
exec python app.py -a 0.0.0.0
```

* Because of the previous point, the following code can work in your app. Whatever your language is, always handle graceful shutdown on `SIGTERM`, or else, your process will be killed after a predefined grace period. In `app.py`:

```python
signal.signal(signal.SIGTERM, graceful_shutdown)
```

## Run the app as a `docker` container

### In the foreground

We will then test that the app is starting as expected.

```bash
docker run --name hello -p 8080:8080 --rm wldp-dev-training/hello
```
This command will:
* run the previously built image `wldp-dev-training/hello`
* give the container a name: `hello`
* bind the `8080` port on the docker host to the `8080` port in the container
* configure the container to clean itself on shutdown (`--rm`)
* run the server in the foreground
* Shut it down with `<CTRL+C>`

```bash
$ docker run --name hello -p 8080:8080 --rm wldp-dev-training/hello
starting hello server (pid=1)...
listening on 0.0.0.0:8080
10.0.2.2 - - [16/Jun/2017 11:33:34] "GET / HTTP/1.1" 200 -
10.0.2.2 - - [16/Jun/2017 11:33:34] "GET / HTTP/1.1" 200 -
^Cshutting down server...
server shut down.
```


### As a daemon

The following command does the same as the previous one except it starts the container as a daemon (the `-d` option).

```bash
docker run --name hello -p 8080:8080 -d wldp-dev-training/hello
```

```bash
$ docker run --name hello -p 8080:8080 -d wldp-dev-training/hello
7892e0fc695843717677d92c3339cf0a87752e2a59fb5b251791bf818cfee731
```

* **Query** the service:

```bash
$ curl http://localhost:8080
Hello World!
```

* Show the **logs** (we should see the previous request logged, add `-f` option to follow the logs)

```bash
$ docker logs -f hello
starting hello server (pid=1)...
listening on 0.0.0.0:8080
172.17.0.1 - - [22/Jun/2017 09:30:06] "GET / HTTP/1.1" 200 -
```

* **Stop** the container

```bash
$ docker stop hello
hello
```

* **Remove** it (with its volumes), so that you can restart another one with the same name

```bash
$ docker rm -v hello
hello
```

## Push image to Openshift integrated registry

This section assumes you have an account on an Openshift instance:

|                    |Description   |Example
---------------------|--------------|---------
|`<openshift-server>`| The openshift master server url|<https://master.wldp.fr>
|`<openshift-login>` | Your personal openshift login| `wldptraining`
|`<openshift-pwd>` | Your personal openshift password| `wldptr@1n1ng`
|`<project-name>` | The project name you chose to test| `training-test`

> Check you have installed [the Openshift command line tool `oc`](#the-openshift-command-line-tool-oc)


### Login to your Openshift instance

```bash
oc login <openshift-server>
```

```bash
$ oc login https://master.wldp.fr
Authentication required for https://master.wldp.fr:443 (openshift)
Username: wldptraining
Password:
Login successful.

You have access to the following projects and can switch between them with 'oc project <projectname>':

  * wldp-apps
    wldp-templates

Using project "wldp-apps".
```

### Create/use a project

A project is a dedicated space on the cluster where you will be able to deploy applications. Moreover, attached to the project, you have a dedicated space on the cluster integrated docker registry so that you can push docker images. You need a project different from `wldp-templates` and `wldp-apps` to go further in this tutorial (these two project have specific rights)

> More on projects: <https://docs.openshift.org/{{book.osversion}}/dev_guide/projects.html>

* Use a project created for you...

```bash
oc project <project-name>
```

```bash 
$ oc project training-test
Using project "training-test" on server "https://master.wldp.fr:443".
```

* ... or if you have enough rights to do so, create your own one

```bash
oc new-project <project-name>
```

```bash
oc new-project training-test
Now using project "training-test" on server "https://master.wldp.fr:443".

You can add applications to this project with the 'new-app' command. For example, try:

    oc new-app centos/ruby-22-centos7~https://github.com/openshift/ruby-ex.git

to build a new example application in Ruby.
```

> You might need to chose another name if a project with the same name already exists on the cluster

### Push your docker image to Openshift

> Due to <https://github.com/openshift/origin/issues/14249>, we have to specify the port (`443`) in registry URL

Now you have got a project, you have a dedicated space on the cluster integrated docker registry.

|                    |Description   |Example
---------------------|--------------|---------
|`<integrated-registry-server>`| The openshift registry server, default: `docker-registry-default.<openshift-cluster-domain>`| `docker-registry-default.wldp.fr`

To push your image to that space, you will have to :
* **Tag** the image : `<integrated-registry-server>:443/<project-name>/<image-name>:<tag>` with:

```bash
docker tag <your-image> <integrated-registry-server>:443/<project-name>/<image-name>:<tag>
```

* **Log in** to the registry (for this you need your openshift token which you can get with: `oc whoami -t`)

```bash
docker login -u unused -p $(oc whoami -t) <integrated-registry-server>
```

* **Push** the image

```bash
docker push <integrated-registry-server>:443/<project-name>/<image-name>:<tag>
```

```bash
$ docker tag wldp-dev-training/hello docker-registry-default.wldp.fr:443/training-test/hello:latest
$ docker login -u unused -p $(oc whoami -t) docker-registry-default.wldp.fr:443
Login Succeeded
$ docker push docker-registry-default.wldp.fr:443/training-test/hello:latest
29a9460d3d59: Pushed
b6f9a525e2a7: Pushed
b51149973e6a: Pushed
latest: digest: sha256:57981d3952d6c82af8f2688ec585155d95085095b98e75f8ffa6274981d0a381 size: 947
```
> More on image tagging: <https://docs.openshift.org/{{book.osversion}}/dev_guide/managing_images.html#tagging-images>


By pushing your image to that space, you implicitly create an `ImageStream` object, you should see your freshly pushed image renamed with the Openshift registry internal ip address and port

```bash
$ oc get imagestreams
NAME      DOCKER REPO                             TAGS      UPDATED
hello     172.30.8.127:5000/training-test/hello   latest    29 minutes ago
```

> More on `ImageStream` objects: <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/builds_and_image_streams.html#image-streams>


## Deploy your app on the cluster

The simplest way to deploy your freshly pushed image as an app on the cluster is:

```bash
oc new-app --image-stream <imagestream-name>[:<imagestreamtag>]
```

It will both create for you a standard `DeploymentConfiguration` object and the related `Service` object.

```bash
$ oc new-app --image-stream hello:latest
--> Found image 5ef3336 (3 days old) in image stream "training-test/hello" under tag "latest" for "hello:latest"

    LDP Traning - Step 1 - Hello
    ----------------------------
    WLDP Traning - Step 1 - Hello

    Tags: wldp, training

    * This image will be deployed in deployment config "hello"
    * Port 8080/tcp will be load balanced by service "hello"
      * Other containers can access this service through the hostname "hello"

--> Creating resources ...
    deploymentconfig "hello" created
    service "hello" created
--> Success
    Run 'oc status' to view your app.
```

Once deployed and started, you should see something similar to that (the command list the `DeploymentConfiguration` objects, the `Pod` objects and the `Service` objects:

```bash
$ oc get dc,pods,svc
NAME       REVISION   DESIRED   CURRENT   TRIGGERED BY
dc/hello   1          1         1         config,image(hello:latest)

NAME               READY     STATUS    RESTARTS   AGE
po/hello-1-c7hc9   1/1       Running   0          3m

NAME        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
svc/hello   172.30.199.169   <none>        8080/TCP   3m
```

You can view its logs (and follow them with `-f` options)

```bash
$ oc logs -f hello-1-c7hc9
starting hello server (pid=1)...
listening on 0.0.0.0:8080

```

You can easily scale your app to `2` instances. The following command updates the previously created `DeploymentConfiguration` to set its `replicas` field to `2`

```bash
$ oc scale --replicas=2 dc/hello
```

```bash
$ oc get pods
NAME            READY     STATUS    RESTARTS   AGE
hello-1-c7hc9   1/1       Running   0          1m
hello-1-7d870   1/1       Running   0          19m
```

You've got now **2** instances (`Pod`) of your app running on the cluster.


> More info on `DeploymentConfiguration` objects: <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/deployments.html#deployments-and-deployment-configurations>

> More infos on `Pod` objects: <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/pods_and_services.html#pods>

> More infos on `Service` objects: <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/pods_and_services.html#services>



## Expose the app on internet

Now that you've got your app deployed on the cluster, you still need to expose it online. 

This is done by creating a `Route` object. In this tutorial, we will:
* expose our app in `https`, delegating certificate handling to Openshift (route termination set to `edge`)
* redirect insecure traffic (e.g. `http://hello-training-test.wldp.fr`) to secure one (`https://`) (option `--insecure-policy=Redirect`)
* configure load-balancing algorithm to be dumb `roundrobin`: no session stickiness (done with annotations)

This can be done with the following commands (it will create a `Route` with same name as the service one):

```
oc create route edge --insecure-policy=Redirect --service=<service-name>
```

```
oc annotate route <name> haproxy.router.openshift.io/balance=roundrobin haproxy.router.openshift.io/disable_cookies=true
``` 

```bash
$ oc create route edge --insecure-policy=Redirect --service=hello
route "hello" created
$ oc annotate route hello haproxy.router.openshift.io/balance=roundrobin haproxy.router.openshift.io/disable_cookies=true
route "hello" annotated
$  oc get route hello
NAME      HOST/PORT                     PATH      SERVICES   PORT       TERMINATION   WILDCARD
hello     hello-training-test.wldp.fr             hello      8080-tcp   edge          None
```

You can then browse your app at: `https://<route-name>-<project-name>.<openshift-cluster-domain>/`

* In our example: <https://hello-training-test.wldp.fr>


### More on `Route` objects

* General purpose documentation: <https://docs.openshift.org/{{book.osversion}}/dev_guide/routes.html>

* `Route` types : <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/routes.html#route-types>


* `Route` customization: <https://docs.openshift.org/{{book.osversion}}/architecture/core_concepts/routes.html#route-specific-annotations>

## Going further

Learn more: [Developing with Openshift as a back-end](../step2/)
