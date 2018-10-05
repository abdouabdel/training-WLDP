# Using Deployment strategies

A deployment strategy is a way to change or upgrade an application. The aim is to make the change without downtime in a way that the user barely notices the improvements.

In this step we will show you different ways to update or test a version of an application based on the main strategies: rolling, bluegreen and a/b deployment. We will also show the modes of triggering a deployment.

To apply the strategies, it will be necessary to make changes on the applications `names` and `hello`. We will use throughout this step the versions of step 1 and 2 for the `hello` application, and on the version of step 2 for the `names` application.

> The strategies are independent from one another as for their demonstration in this step. So, to reproduce each example shown in this step, you should delete (if the contrary is not notified) all objects created previously to have a fresh openshift project.

## Rolling Deployment

The Rolling strategy is the **default** strategy used if no strategy is specified on a deployment configuration.

A rolling deployment **slowly replaces** instances of the previous version of an application with instances of the new version of the application. It means that both versions of the application running in the same time. So the new version of the application have to handle **N-1 compatibility**.

The rolling deployment strategy waits for pods to pass their **readiness** check before scaling down old components, and does not allow pods that do not pass their readiness check within a configurable timeout.
A readiness probe determines if a container is ready to handle requests.
If the pods do not become ready , the process will abort, and the deployment configuration will be rolled back to its previous version.

The **readiness** check is a part of container health checks implemented by Openshift to detect and handle unhealthy containers using probes.

### Container Health Checks Using Probes

A probe is a Kubernetes action that periodically performs diagnostics on a running container. Currently, two types of probes exist, each serving a different purpose:

* Readiness probe : determines if a container is ready to service requests.
* Liveness Probe : checks if the container in which it is configured is still running.

Both probes can be configured in three ways:

* HTTP Checks : the kubelet uses a web hook to determine the healthiness of the container.
* Container Execution Checks : the kubelet executes a command inside the container.
* TCP Socket Checks: The kubelet attempts to open a socket to the container.

We use the `HTTP checks` in our case.

#### Readiness probe

Lets implement the readiness probe of the application `hello` for both version of the step 1 and the step 2. To do so, we add a the path `/health` that returns 200 as http response if the application deployed within openshift is ready.

`hello` app step 1:

```python
...
def do_GET(self):
    self.protocol_version = 'HTTP/1.1'

    status = 404
    response = "Not Found"

    if (self.path == '/'):
      response = "Hello World!"
      status = 200

    # Add the health path

    if (self.path == '/health'):
      status = 200
      response = "OK"
...
```

`hello` app step 2:

```python
...
def do_GET(self):
    self.protocol_version = 'HTTP/1.1'

    status = 404
    response = "Not Found"

    if (self.path == '/'):
      status, name = self.get_url('http://names:8080/') 
      response = 'Hello ' + name + '!\n' 

    if status == 502:
      response = "Failed to contact 'names' service"

    if (self.path == '/health'):
      status = 200
      response = "OK"
...
```

Build the modified apps, tag `v1` and `v2` as version respectively from step 1 and the step 2 then push them to the openshift registry:

```bash
$ docker build -t wldp-dev-training/hello:v1 ./hello_v1/.
$ docker build -t wldp-dev-training/hello:v2 ./hello_v2/.
...
$ docker tag wldp-dev-training/hello:v1 docker-registry-default.wldp.fr:443/training-test/hello:v1
$ docker tag wldp-dev-training/hello:v2 docker-registry-default.wldp.fr:443/training-test/hello:v2
$ docker login -p $(oc whoami -t) -e unused -u unused docker-registry-default.wldp.fr:443
$ docker push docker-registry-default.wldp.fr:443/training-test/hello:v1
$ docker push docker-registry-default.wldp.fr:443/training-test/hello:v2
```

After the push of the images, tag the imagestream `hello:v1` with `latest` as version then create the application:

```bash
# tag hello:v1 to latest
$ oc tag training-test/hello:v1 hello:latest
# create the hello app
$ oc new-app training-test/hello
# create the route
$ oc expose svc/hello
# test
$ curl http://hello-training-test.wldp.fr/
Hello World!
$ curl http://hello-training-test.wldp.fr/health
OK
```

To set the **readiness** check, we edit the deploymentconfig to add configuration below under  `template.spec.containers.readinessprobe` :

```yaml
...
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 15
  timeoutSeconds: 1
...
```

A few explanation:

* `httpGet` indicates that is an http probe which have a path and a port.
* `initialDelaySeconds` that is a grace period from when the container is started to when health checks are performed

To add it, we can edit the deploymentconfig using this command `oc edit dc/<DC_NAMES>` :

```bash
# Add health checks
$ oc edit dc/hello
deploymentconfig "hello" edited
```

Running this will open the configuration file of your deploymentconfig in your default file editor.

#### Liveness probe

To set the **liveness** check, we edit the deploymentconfig to add configuration below under `template.spec.containers.livenessprobe` :

```yaml
...
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 15
  timeoutSeconds: 1
...
```

Add it by editing the deploymentconfig using this command `oc edit dc/<DC_NAMES>` :

```bash
# Add health checks
$ oc edit dc/hello
deploymentconfig "hello" edited
```

For more information : <https://docs.openshift.com/container-platform/latest/dev_guide/application_health.html#dev-guide-application-health>

Now that the first version of the `hello` app is deployed and his **readiness** probe setted, we can configure the rolling deployment strategy.

### Configure deployment strategy

To set the rolling strategy, we edit the `hello` deploymentconfig as below:

```yaml
...
strategy:
  type: Rolling
  rollingParams:
    updatePeriodSeconds: 1
    intervalSeconds: 1
    timeoutSeconds: 600
    maxSurge: 2
    maxUnavailable: 0
    pre: {}
    post: {}
...
```

A few explanation:

* `updatePeriodSeconds`: The time to wait between individual pod updates. (default value = 1)
* `intervalSeconds`: The time to wait between polling the deployment status after update. (default value = 1)
* `timeoutSeconds`: The time to wait for a scaling event before giving up (means automatically rolling back to the previous complete deployment.). (default value = 600)
* `maxSurge`: it is the maximum number of pods that can be scheduled above the original number of pods.
* `maxUnavailable`: it is the maximum number of pods that can be unavailable during the update.
  > Both parameters, `maxSurge` & `maxUnavailable`, can be set to either a percentage (e.g., 10%) or an absolute value (e.g., 2). The default value for both is 25%.
* `pre` and `post` are both lifecycle hooks.

The Rolling strategy will:

1. Execute any pre lifecycle hook.

1. Scale up the new replication controller **based on the `surge` count**.

1. Scale down the old replication controller **based on the `max unavailable` count**.

1. Repeat this scaling until the new replication controller has reached the desired replica count and the old replication controller has been scaled to zero.

1. Execute any post lifecycle hook.

> The rolling stragegy is based on the `maxSurge` and `maxUnavailable` that can be tuned for availability and speed. But be aware that the use of `maxSurge` will involve the consumption of additional resources and the use of `maxUnavailable` may result in a partial unavailability.

To see how the deployment is performed, we scale the deployment configuration up to 3 pods:

```bash
oc scale dc/hello --replicas=3
```

We identify the 3 pods of `hello:v1` :

```bash
 oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-14-7kmzc   1/1       Running   0          1m
hello-14-m5bct   1/1       Running   0          1m
hello-14-mc72l   1/1       Running   0          1m
```

Now, we trigger a new deployment automatically by tagging `v2` of the application `hello` as the `latest`:

```bash
oc tag hello:v2 hello:latest
```

> For `hello:v2` to work, you must deploy the application `names`.

Then, using the `oc` tool, we get the list of pods to see how old pods are replaced by new ones:

```bash
# we see the 2 new pods created as indicated in maxSurge
$ oc get pods
NAME              READY     STATUS              RESTARTS   AGE
hello-14-7kmzc    1/1       Running             0          11m
hello-14-m5bct    1/1       Running             0          11m
hello-14-mc72l    1/1       Running             0          11m
hello-15-deploy   1/1       Running             0          11s
hello-15-nl8vh    0/1       ContainerCreating   0          4s
hello-15-z5frd    0/1       Running             0          4s
# we see that old pods are scaled down as long as the readiness check of new pods is passed
$  oc get pods
NAME              READY     STATUS              RESTARTS   AGE
hello-14-m5bct    1/1       Running             0          12m
hello-14-mc72l    1/1       Running             0          12m
hello-15-deploy   1/1       Running             0          32s
hello-15-nl8vh    0/1       Running             0          25s
hello-15-x35kv    0/1       ContainerCreating   0          4s
hello-15-z5frd    1/1       Running             0          25s
# New pods of hello:v2 deployed
$ oc get pods
NAME             READY     STATUS    RESTARTS   AGE
hello-15-nl8vh   1/1       Running   0          58s
hello-15-x35kv   1/1       Running   0          37s
hello-15-z5frd   1/1       Running   0          58s
```

You can also request the `hello` app to see the result that prove the continuous replacement and no downtime of the application:

```bash
$ for i in `seq 1 20`; do curl http://hello-training-test.wldp.fr/; done
# Before the deploy process
Hello World!
Hello World!
Hello World!
Hello World!
# During the deploy process
Hello World!
Hello Joseph Solinski!
Hello World!
Hello Charlie Stokes!
Hello Vickie Schusterman!
Hello World!
Hello Addie Brodsky!
Hello John Liggins!
Hello World!
# After the deploy process
Hello Robert Williams!
Hello Bridget Joeckel!
Hello Lori Robinson!
```

For more information: <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/deployment_strategies.html#rolling-strategy>

As we see in this deployment strategy, Openshift will have to stop pod that containing the application.
Before doing that, we must be sure that any request is not currently treated and any new request will not be processed by the application even if Openshift give time to shut down the application before removing it from load balancing rotations.The application must be **gracefully terminated**

### Graceful Termination

On shutdown, OpenShift Container Platform will send a `TERM` signal to the processes in the container. Application code, on receiving `SIGTERM`, should stop accepting new connections. This will ensure that load balancers route traffic to other active instances. The application code should then wait until all open connections are closed (or gracefully terminate individual connections at the next opportunity) before exiting.

It is managed in our applications (`hello` and `names`) as below :

```python
...
  def trigger_graceful_shutdown(signum, stack):
    # trigger shutdown from another thread to avoid deadlock
    t = threading.Thread(target=graceful_shutdown, args=(signum, stack))
    t.start()

  # handle graceful shutdown in a function we can easily bind on signals
  def graceful_shutdown(signum, stack):
    print "shutting down server..."
    try:
      server.shutdown();
    finally:
      print "server shut down."

  signal.signal(signal.SIGTERM, trigger_graceful_shutdown)
  signal.signal(signal.SIGINT, trigger_graceful_shutdown)
...
```

You may have noticed that changing the image tag automatically triggers a new deployment of the application: this is caused by the `ImageChange` trigger one of the **deployment triggers**.

### Deployment Triggers

The deploymentconfig contains triggers if setted, create a new deployment process in response to an event. Two kind of event can trigger a new deployment: a change in the deployment configuration, named `configChange` trigger, or a change of the image stream tag named `imageChange` trigger.

1. `configChange` trigger

    If `configChange` trigger is defined on the deployment configuration (defined by default), a new deployment process will begin whenever configuration change are made.
    See below how it is defined in the deploymentconfig:

      ```yaml
      spec:
        ...
        triggers:
          - type: ConfigChange
      ```

    We can set it using the `oc` tool by running this:  `oc set triggers dc/<DC_NAME> --from-config`

      ```bash
      $ oc set triggers dc/hello --from-config
      deploymentconfig "hello" updated
      ```
    To remove it:

      ```bash
      $ oc set triggers dc/hello --from-config --remove
      deploymentconfig "hello" updated
      ```

1. `imageChange` trigger

    If `imagegChange` trigger is defined, with `imageChangeParams.automatic = true`, on the deployment configuration, a new deployment process will begin whenever a new version of the image is pushed.
    See below how it is defined in the deploymentconfig:

      ```yaml
      spec:
        ...
        triggers:
          - type: ImageChange
            imageChangeParams:
              automatic: true
              containerNames:
                - hello
              from:
                kind: ImageStreamTag
                namespace: training-test
                name: 'hello:latest'
      ```

    This configuration defines which image the trigger will be based on.

    >  If the `imageChangeParams.automatic` field is set to `false`, the trigger is disabled.

    Using the `oc` tool we set the `imageChange` trigger by running this: `oc set triggers dc/<DC_NAME> --from-image=<NAMESPACE>/<IMG_NAME>:<IMG_TAG> -c <CONTAINER_NAME>`:

      ```bash
      $ oc set triggers dc/hello --from-image=training-test/hello:latest -c hello
      deploymentconfig "hello" updated
      ```

    To remove it :

      ```bash
      $ oc set triggers dc/hello --from-image=training-test/hello:latest --remove
      deploymentconfig "hello" updated
      ```
For more information: <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/basic_deployment_operations.html#triggers>

## Blue-Green Deployment

Blue-Green strategy is used to test a new version of an application (called the blue version) while the stable version (green version), recently used, will always be available but not exposed anymore.

Exposing an application means pointing a route to his service. So here, we will keep the route created earlier to expose the green version but we will modify it to point to the blue version.
And, as the green version is still deployed and available, we will be able to quickly switch back to it if a problem arises on the blue version.

To do so we need 2 deployments configuration, one for the stable version (the green version) and the other for the newer version (the blue version). We will take `hello:v1` as the green version and `hello:v2` as the blue version.

We deploy both `v1` and  `v2` version of `hello` as respectively `hello-green` and `hello-blue`:

```bash
$ oc new-app training-test/hello:v1 --name=hello-green
$ oc new-app training-test/hello:v2 --name=hello-blue
```

And through a `route` that points to a service, we will modify it to point to a different service: we will modify a route, which pointed to the service of the green version, so that it points to the service of the blue version

We create a `route` named `bluegreen-hello` that points to `hello-green` service:

```bash
$ oc expose svc/hello-green --name=bluegreen-hello
route "bluegreen-hello" exposed
```

Browse the application to confirm that the route points to the green version:

```bash
$ curl http://bluegreen-hello-training-test.wldp.fr/
Hello World!
```

Now we patch the route `bluegreen-hello` to point to `hello-blue` service:

```bash
$ oc patch route/bluegreen-hello -p '{"spec":{"to":{"name":"hello-blue"}}}'
"bluegreen-hello" patched
```

And then we browse the application to verify if the route points to the `blue` version:

```bash
$ curl http://bluegreen-hello-training-test.wldp.fr/
Failed to contact 'names' service
```

We can see above that the route points to the `blue` version but an error occurs. So we need to switch back to the `green` version before diagnosing and correcting the error:

```bash
$ oc patch route/bluegreen-hello -p '{"spec":{"to":{"name":"hello-green"}}}'
"bluegreen-hello" patched
# We request the application to see that the green version has replaced the blue version
$ curl http://bluegreen-hello-training-test.wldp.fr/
Hello World!
```

Now, knowing that the users are using the stable version, we can search solution for the error.

The error occurs because the `blue` version, that is `hello:v2`, requires the application `names`. So we need to deploy the application `names` before pointing the route `bluegreen-hello` to `hello-blue` service. See below:

```bash
# we deploy the application names
$ oc new-app training-test/names:latest
# After the finish of the deploy process of names
# we can point back the route bluegreen-hello to hello-blue service
$ oc patch route/bluegreen-hello -p '{"spec":{"to":{"name":"hello-blue"}}}'
"bluegreen-hello" patched
# And TADA!!! it's working
$ curl http://bluegreen-hello-training-test.wldp.fr/
Hello Raymond Pasey!
```

For more information: <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/advanced_deployment_strategies.html#advanced-deployment-strategies-blue-green-deployments>

## A/B Deployment

The `A/B` deployment strategy is used to test new version of the application alongside the old.
It is different from `bluegreen` because instead of having only one active version (`green` or `blue`), both versions are active at the same time.

Openshift offers two ways to do A/B testing:

* using one route for multiple services
* using one service for multiple deployment configurations

### One route, Multiple services

Instead of the `Blue-Green` deployment strategy, where the `route` points to only one `service`, the `A/B` deployment strategy has a `route` that points to multiple `services`.
As the `route` exposes several `services`, openshift offers us a way to control the portion of requests to each `service`. So we can specify that the stable version (`green` or `A`) gets most of the user requests while a limited fraction of requests go to the new version (`blue` or `B`).
To do so, we assign and tune , in the `route` configuration, for each `service` pointed, the `weight` parameter.

Lets set up the `A/B` deployment strategy for the two versions (`v1` and `v2`) of the application `hello` using one route:

We deploy both `v1` and  `v2` version of `hello` as respectively `hello-a` and `hello-b`:

```bash
$ oc new-app training-test/hello:v1 --name=hello-a
$ oc new-app training-test/hello:v2 --name=hello-b
```

We create the `route` named `hello` by exposing the service `hello-a` :

```bash
$ oc expose svc/hello-a --name=hello
route "hello" exposed
```

Then we test it to check that it is `hello:v1`:

```bash
$ curl http://hello-training-test.wldp.fr/
Hello World!
```

At this point there is a single service with default weight=100 so all requests go to it.

```yaml
$ oc get route/hello -o yaml
apiVersion: v1
kind: Route
...
spec:
  host: hello-training-test.wldp.fr
  port:
    targetPort: 8080-tcp
  to:
    kind: Service
    name: hello-a
    weight: 100
  wildcardPolicy: None
```

Adding the other service as an alternateBackends and adjusting the weights will bring the A/B setup to life. This can be done by the `oc` tool or by editing the route.

Using the `oc` tool we run this command `oc set route-backends <ROUTE_NAME> <SERVICE_A_NAME>=<WEIGHT_SERVICE_A> <SERVICE_B_NAME>=<WEIGHT_SERVICE_B>` :

```bash
$ oc set route-backends hello hello-a=100 hello-b=100
route "hello" updated
```

```bash
# Here we see the pourcentage of weight between the two services exposed by this route
$ oc get route
NAME      HOST/PORT                     PATH      SERVICES                   PORT       TERMINATION
hello     hello-training-test.wldp.fr             hello-a(50%),hello-b(50%)   8080-tcp
# This is the config file of the route after adding hello-b as an alternateBackends
$ oc get route/hello -o yaml
apiVersion: v1
kind: Route
..
spec:
  alternateBackends:
  - kind: Service
    name: hello-b
    weight: 100
  host: hello-training-test.wldp.fr
  port:
    targetPort: 8080-tcp
  to:
    kind: Service
    name: hello-a
    weight: 100
  wildcardPolicy: None
...
```

Below, we can see that when requesting `hello-training-test.wldp.fr`, we can get response from both services:

```bash
$ for i in `seq 1 20`; do curl http://hello-training-test.wldp.fr/; done
Hello World!
Hello World!
Hello Lillian Bien!
Hello World!
Hello Diane Parker!
Hello Paul Reeder!
Hello World!
Hello Dorothy Joyce!
Hello World!
Hello Garry Lee!
Hello World!
Hello Barbara Stone!
Hello World!
Hello Beatrice Lancaster!
Hello World!
Hello World!
Hello Susanne Pybus!
Hello Rodney Mallon!
Hello World!
Hello World!
```

More information : <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/advanced_deployment_strategies.html#routes-load-balancing-for-AB-testing>

### One Service, Multiple Deployment Configurations

Imagine that the application on which we would like to apply the `A/B` testing is not intended to be exposed via a route. It would be impossible with the `one route, multiple services` method.

This is where the `one service, multiple deployment configurations` comes in, because OpenShift, through labels and deployment configurations, supports multiple simultaneous shards being exposed through the same service.

To highlight its usefulness, we will modify the `names` application, which is not exposed via a `route`, to have two versions deployed in `A/B` strategy: one providing only men's names and another version providing only women's names.

#### Editing the applications

Based on the application names of step 2 which is version `v1` in this step, we will modify it to have a `v2` providing men names and a `v3` providing only women names:

* `v2` version:

  ```python
  def do_GET(self):
      self.protocol_version = 'HTTP/1.1'

      status = 200

      if (self.path == '/'):
        response = names.get_full_name(gender='male')
      elif (self.path == '/health'):
        response = "OK"
      else:
        status = 404
        response = "Not Found"
  ```

* `v3` version:

  ```python
  def do_GET(self):
      self.protocol_version = 'HTTP/1.1'

      status = 200

      if (self.path == '/'):
        response = names.get_full_name(gender='female')
      elif (self.path == '/health'):
        response = "OK"
      else:
        status = 404
        response = "Not Found"
  ```

After this modification for each version, build and push the images with correct tags :

```bash
$ docker build -t docker-registry-default.wldp.fr:443/training-test/names:v2 ./names_v2/.
$ docker build -t docker-registry-default.wldp.fr:443/training-test/names:v3 ./names_v3/.
$ docker login -p $(oc whoami -t) -e unused -u unused docker-registry-default.wldp.fr:443
Login Succeeded
$ docker push docker-registry-default.wldp.fr:443/training-test/names:v2
$ docker push docker-registry-default.wldp.fr:443/training-test/names:v3
```

Now the imagestreams available lets begin the `A/B` deployment.

#### Implementation of `A/B` deployment

Based on the state of the project at the end of the `A/B` deployment method `one route, multiple services`, we will:

1. tag the `names:v2` as `names:latest`
1. edit the current deploymentconfig `names` to set the common label (deploy manually if needed)
1. create a service that uses the common label
1. deploy `names:v3` with common label

Lets see the current state of the project:

```bash
$ oc get pods
NAME              READY     STATUS    RESTARTS   AGE
hello-a-1-qwq5h   1/1       Running   0          12m
hello-b-1-st5dn   1/1       Running   0          12m
names-1-27p05     1/1       Running   0          8m
$ oc get route/hello
NAME      HOST/PORT                     PATH      SERVICES                    PORT       TERMINATION
hello     hello-training-test.wldp.fr             hello-a(50%),hello-b(50%)   8080-tcp
```

We see above that our current state is that we have a pod for each version (`v1` and `v2`) of `hello` application with a route that serving each service, and a pod of `names` with `v1` as version.

We can start the deployment:

* tag the `names:v2` as `names:latest`:
  ```bash
  $ oc tag names:v2 names:latest
  ```
  (deploy the deployment configuration if not done automatically)

  If we request `hello` application we see that all names generated are men names.

  ```bash
  $ for i in `seq 1 10`; do curl http://hello-training-test.wldp.fr/; done
  Hello World!
  Hello Anthony Carleton!
  Hello World!
  Hello Cody Beirne!
  Hello Barry Gazzo!
  Hello World!
  Hello John Mcdaniel!
  Hello World!
  Hello World!
  Hello Demetrius Alonzo!
  ```

  But we have response from `hello:v1` (result of `A/B` testing applied on `hello`), to remove it we redirect all the traffic to `hello:v2` by running this command:
  ```bash
  $ oc set route-backends hello hello-a=0 hello-b=200
  route "hello" updated
  ```

  ```bash
  $ for i in `seq 1 10`; do curl http://hello-training-test.wldp.fr/; done
  Hello Benjamin Ladd!
  Hello Joe Turner!
  Hello Brian Mccalla!
  Hello David Gregory!
  Hello Richard Follick!
  Hello Tommie Bridges!
  Hello Eric Kelly!
  Hello Marcus Powell!
  Hello Charles Curtis!
  Hello Leroy Toland!
  ```

* Edit the current deploymentconfig `names` to set the label `hello: "true"`  that will be common to all shards:
  ```bash
  $ oc patch dc/names -p '{ "metadata": { "labels": { "names": "true" } }, "spec": { "selector": { "names": "true" }, "template": { "metadata": { "labels": { "names": "true" } } }  } }'
  "names" patched
  ```

* Create a service that uses the common label by running this command `oc expose dc/<DC_NAME> --name=<NAME_FOR_SERVICE> --selector=<COMMON_LABEL>`
  As we know the `v2` of `hello` application accede to `names` application through `http:\\names:8080\`.
  So if we create another service with a different name, `hello` app will no longer have access to `names`.
  Then we have to create a service called "names" but since there is a service that already has that name, we have to delete it.

  ```bash
  $ oc delete svc/names
  service "names" deleted
  ```

  ```bash
  $ oc expose dc/names --name=names --selector=names=true
  service "names" exposed
  ```

* deploy `names:v3` with common label
  ```bash
  $ oc new-app training-test/names:v3 --name=names-b --labels=names=true
  ```

At the end, when we request the application `hello`, we got data from each shard of `names`:

```bash
$ for i in `seq 1 10`; do curl http://hello-training-test.wldp.fr/; done
Hello Robert Wren!
Hello Lindsey Hannan!
Hello James Coleman!
Hello Kenneth Eckert!
Hello Emma Bender!
Hello Ronald Carr!
Hello Ashley Goodwin!
Hello Michael Osterhout!
Hello Roy Torres!
Hello Bryce Warren!
```

To get data only from a specific shard, you have to scale down the replicas of the other shard to 0. For example, to have women names only, we scale down the shard based on `names:v2` to 0 :

```bash
oc scale dc/names --replicas=0
deploymentconfig "names" scaled
```

Request the `hello` application to see that we have only women names:

```bash
$ for i in `seq 1 5`; do curl http://hello-training-test.wldp.fr/; done
Hello Jane Kreidel!
Hello Margaret Acuff!
Hello Hilda Hoefer!
Hello Dana Barnes!
Hello Ruth Henson!
```

The traffic portion assigned to each shard is not managed by a parameter `weight` as in the `A/B` testing method `one route, multiple services`. When dealing with large numbers of instances, you can use the relative scale of individual shards to implement percentage based traffic.
For example:

* having 1 pod based on `names:v2` and 1 pod based on `names:v3` is equivalent to 50%  shard A and 50 % on shard B
* having 4 pods of `names:v2` and 1 pod of `names:v3` is equivalent to 80% on shard A and 20% on shard B

For more informations: <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/advanced_deployment_strategies.html#advanced-deployment-one-service-multiple-deployment-configs>

More informations about deployment strategies :

* <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/deployment_strategies.html>
* <https://docs.openshift.com/container-platform/latest/dev_guide/deployments/advanced_deployment_strategies.html>