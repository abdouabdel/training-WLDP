# Service discovery and proxy concerns

## Service discovery

When you want to call `names` service from `hello` service, `hello` needs to know where the different running instances of `names` are running, so that traffic can be, for example,  load-balanced between them. That's what is called **_service discovery_**

Openshift offers three mechanisms for service discovery: [by name](#by-name), [by environment variables](#by-environment-variables), and  [DIY](#service-discovery-do-it-yourself)

### By name

> This is the **recommended way** over [the environment variables way](#by-environment-variables)

Openshift provides a handy private DNS service in the cluster. 

>More info at: <https://docs.openshift.org/{{book.osversion}}/architecture/additional_concepts/networking.html#architecture-additional-concepts-openshift-dns>

Let's make it short with our example

We have two `Service` objects declared in the `training-test` project (`hello` and `names`):

```bash
$ oc get svc
NAME             CLUSTER-IP       EXTERNAL-IP     PORT(S)    AGE
hello            172.30.218.227   <none>          8080/TCP   2d
names            172.30.74.92     <none>          8080/TCP   2d
```

From the `hello` service you can call the `names` service the following ways:

* `http://`**`names`**:`8080`
* `http://`**`names.training-test`**:`8080`
* `http://`**`names.training-test.svc`**:`8080`
* `http://`**`names.training-test.svc.cluster.local`**:`8080`

You can try it by querying `names` service from an `hello` pod, and understand how this work having a look at `/etc/resolv.conf`: 

<pre>
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-13-1btf5   1/1       Running   0          1d
hello-13-bqn1k   1/1       Running   0          1d
names-5-ncssv    1/1       Running   0          1d
$ oc rsh hello-13-1btf5
sh-4.2$ <b>curl http://names:8080</b>
Connie Sayco
sh-4.2$ <b>cat /etc/resolv.conf</b>
search <b>training-test.svc.cluster.local svc.cluster.local cluster.local</b>
nameserver 10.42.186.41
nameserver 10.42.186.41
options ndots:5
sh-4.2$
</pre>

Under the hood, `names` is resolved to the cluster IP `172.30.74.92`, then all traffic sent to this virtual IP is load-balanced between the running service backing pods (only one in this example).

[`ocd`](README.md#the-ocd-tool) emulates this behavior on the development machine by declaring these aliases in the local `/etc/hosts` file (removing them at shutdown)

```bash
127.1.1.1        hello hello.training-test hello.training-test.svc hello.training-test.svc.cluster hello.training-test.svc.cluster.local # WLDP
127.1.1.2        names names.training-test names.training-test.svc names.training-test.svc.cluster names.training-test.svc.cluster.local # WLDP
```

> Only using **the shortest one** (`http://names:8080`) keeps your source code independent from the project in which it is deployed (e.g. `training-test`)

#### A variant: headless services
If the service cluster IP behind the DNS name resolution does not suit your use case, you can still create **headless services**. That means that no more cluster IP will be assigned and  querying the DNS will return you multiple A records, one for each running pod of the service. 

Headless services are created by setting the `ClusterIP` field of the `Service` object to `None` at creation time. 

> More info: <https://kubernetes.io/docs/concepts/services-networking/service/#headless-services>

##### Querying `hello` (_ClusterIP service_) from a `names` pod: return the cluster IP
```bash
$ oc rsh names-6-jb7pr getent hosts hello
172.30.218.227  hello.training-test.svc.cluster.local
```
##### Querying `hello` (_Headless service_) from a `names` pod: returns the running pods IPs
```bash
$ oc rsh names-6-jb7pr getent hosts hello
10.128.2.64     hello.training-test.svc.cluster.local
10.131.4.44     hello.training-test.svc.cluster.local
```

### By environment variables

Using the environment variables is an **alternative**, but is not (and cannot be) emulated by [`ocd`](README.md#the-ocd-tool)

> This is the **NOT** the recommended way and is here for documentation purpose only

Services informations are published in the pods as environment variables. Let's see how the `names` service informations are published in an `hello` pod:

```bash
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-13-1btf5   1/1       Running   0          1d
hello-13-bqn1k   1/1       Running   0          1d
names-5-ncssv    1/1       Running   0          1d
$ oc rsh hello-13-1btf5
sh-4.2$ env | grep NAMES | sort
NAMES_PORT=tcp://172.30.74.92:8080
NAMES_PORT_8080_TCP=tcp://172.30.74.92:8080
NAMES_PORT_8080_TCP_ADDR=172.30.74.92
NAMES_PORT_8080_TCP_PORT=8080
NAMES_PORT_8080_TCP_PROTO=tcp
NAMES_SERVICE_HOST=172.30.74.92
NAMES_SERVICE_PORT=8080
NAMES_SERVICE_PORT_8080_TCP=8080
sh-4.2$
```

#### Using the `docker`-style variables in the code

The code in `hello` service `app.py` would be:

```python
names_svc_ip = os.environ.get('NAMES_PORT_8080_TCP_ADDR')
names_svc_port = os.environ.get('NAMES_PORT_8080_TCP_PORT')
url = 'http://%s:%s/' % (names_svc_ip, names_svc_port)
```
> When developing locally, be sure to define these variables (or make sure you have a safe fallback value)

#### Using the `kubernetes`-style variables in the code

The code in `hello` service `app.py` would be:

```python
names_svc_ip = os.environ.get('NAMES_SERVICE_HOST')
names_svc_port = os.environ.get('NAMES_SERVICE_PORT')
url = 'http://%s:%s/' % (names_svc_ip, names_svc_port)
```
> When developing locally, be sure to define these variables (or make sure you have a safe fallback value)

### Service discovery: Do It Yourself

If the previous means are not enough for you, it is still a good thing to know how they work.

However, you can just deploy the service discovery solution of your choice inside your project (consul, eureka, ...)

> These solutions often work in cluster, make sure to make their configuration robust in a Openshift environment (a pod is ephemeral, you may want to look at beta `StatefulSet` objects: <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/>)

## Proxy concerns

Now, let's add to the `hello` service an endpoint that both needs to call the **private** `names` service and a **public service** available on **internet** to build its response.

### Let's see the code...

`hello` service from _step 2_ has been modified in _step 3_ (`step3/hello/src/app.py`) to call an external public service. See below the difference:

#### step 2 code

As a recall, here is the relevant **step2** code that handles `GET` requests on `/` and that returns `Hello <random-firstname> <random-lastname>!`

Not specifying a second parameter to `get_url`, uses the default url opener that we have configured to bypass any proxy configuration.

```python
# way in python to disable proxy auto-detection to make direct connections 
NOPROXY_OPENER = urllib2.build_opener(urllib2.ProxyHandler({})) 

# way in python to rely on system proxy config (env var, ...) 
SYSTEMPROXY_OPENER = urllib2.build_opener(urllib2.ProxyHandler()) 

def get_url(self, url, opener=None): 
  if (opener == None): 
    opener = HelloServerRequestHandler.NOPROXY_OPENER 
...
```

> You can usually do the same in any situation. The way to do it depends on **the language used** and **the HTTP client library used**. When proxy may be needed, take care of condition its use **with environment variables** to keep your docker image configurable. You can use either standard ones (`http(s)_proxy`, `no_proxy`) or language-specific ones (in Java: `http(s).proxyHosts`, `http(s).nonProxyHosts`). 


```python
if (self.path == '/'):
  status, name = self.get_url('http://names:8080/') 
  response = 'Hello ' + name + '!\n' 
  
if status == 502:
  response = "Failed to contact 'names' service"

```

#### step 3 code

In **step 3**, we add the endpoint `GET /learn` that will call:
* the `names` service **explicitly without proxy** 
* a public service **honouring system proxy** configuration (e.g. environment variables).

> We have made the use of `NOPROXY_OPENER` and `SYSTEMPROXY_OPENER` more explicit

```python
import json
```

```python
if (self.path == '/'):
  svc = 'names'
  status, name = self.get_url('http://names:8080/', self.NOPROXY_OPENER) 
  response = 'Hello ' + name + '!\n'
elif (self.path == '/learn'): 
  name_url = 'http://names:8080/'
  quote_url = 'http://quotes.stormconsultancy.co.uk/random.json' 

  svc = 'names'
  status, name = self.get_url(name_url, self.NOPROXY_OPENER)
  if status == 200:
    svc = 'quotes'
    status, json_quote = self.get_url(quote_url, self.SYSTEMPROXY_OPENER) 
    if status == 200:
      quote = json.loads(json_quote)
      response = "Hello " + name + "!\n\n\"" + quote["quote"] + "\"\n\n  -- " + quote['author'] + " --"
  
if status == 502:
  response = "Failed to contact '%s' service" % svc

```
### Launch the app locally

Before that, make sure your have [`ocd`](README.md#the-ocd-tool) running (to access `names` service) and check your environment proxy configuration (`HTTP_PROXY` on Windows, `http_proxy` on unix/mac) regarding your needs

```bash
$ python hello\src\app.py
starting hello server (pid=14376)...
listening on 127.0.0.1:8080
```

* Point your browser at <http://localhost:8080/learn> and you should see something similar to:

```
Hello Charles Toledo!

"Linux is only free if your time has no value."

  -- Jamie Zawinski --
```
* The name (Charles Toledo) comes from the **internal private call** to the `names` service whereas the quote's details comes from a **public call** to `quotes.stormconsultancy.co.uk`

* Misconfiguring your proxy could have produce:

```
Failed to contact 'quotes' service
```

and in the service logs:

```
starting hello server (pid=6444)...
listening on 127.0.0.1:8080
[error] Failed to get 'http://quotes.stormconsultancy.co.uk/random.json': <urlopen error [Errno 11004] getaddrinfo failed>
127.0.0.1 - - [26/Jun/2017 13:16:27] "GET /learn HTTP/1.1" 502 -
```
* or a `504 Gateway Timeout` error from the Openshift router when deployed


## Deploy it to Openshift

You now should be used to it, deploy this newly modified version of `hello` to openshift.

### Configure proxy settings
Ask your Openshift cluster administrator the proxy settings you should apply to access internet from within a pod, and configure the `DeploymentConfiguration` accordingly.

In the example below, we will use `http://proxy-wldp.svc.meshcore.net:3128`.

Modify the `DeploymentConfiguration` object `hello` to add the `http_proxy` environment variable: 

``` bash
oc set env dc/hello http_proxy=<proxy-spec>
```
Applying this configuration update will update the two running `hello` pods to reflect this change.

```bash
$ oc set env dc/hello --overwrite http_proxy=http://proxy-wldp.svc.meshcore.net:3128
deploymentconfig "hello" updated
$ oc set env dc/hello --list
# deploymentconfigs hello, container hello
http_proxy=http://proxy-wldp.svc.meshcore.net:3128
```

> More info on environment variables: <https://docs.openshift.org/{{book.osversion}}/dev_guide/environment_variables.html#setting-and-unsetting-environment-variables>

### Test the service
Test your service by pointing your browser at the public `hello` url (e.g. <https://hello-training-test.wldp.fr/learn>)


### Inside the `hello` pods

You can see the new `http_proxy` environment variable in the `hello` pods:

<pre>
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
<b>hello-18-cvfwt</b>   1/1       Running   0          2h
hello-18-td9ch   1/1       Running   0          2h
names-6-jb7pr    1/1       Running   0          3d
$ <b>oc rsh hello-18-cvfwt</b>
sh-4.2$ <b>env | grep http</b>
<b>http_proxy=http://proxy-wldp.svc.meshcore.net:3128</b>
sh-4.2$ 
</pre>

## Going further

Learn more on [Continuous integration (CI)](../step4/)