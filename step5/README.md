# Dealing with Openshift API objects

In this step we will have a closer look at how Openshift stores your project description and status.

Indeed, in the previous steps, we have talked about `DeploymentConfig`, `Pod`, `Service`, `Route`, `ImageStream`, and `ServiceAccount` objects. We have created and modified those objects with various `oc` commands.

We will now see:

- how those objects really look like
- how to deal with them: export/modify/apply/maintain
- how to take advantage of this: you have your full application architecture described as code

## Quick overview

As a starter, here are a few variants of `oc get ...` command. Just **play with them** to see how their (verbose) output looks like.

* To have a quick overview of the **different kinds of objects** that can live in Openshift:

```bash
oc get
```

* To have a quick overview of the **main objects** related to **your project** (some are filtered: default `Secret` objects, `ServiceAccount` objects,...)

```bash
oc get all
```
> Add ` -o wide` for a slightly more detailed overview

* To see the **full definition and state** of a given object:

```bash
oc get <object-kind>/<object-name> -o yaml
```

```bash
$ oc get route/hello -o yaml
```
## Dealing with the objects

There are 3 main different ways to interact with these objects.

### The command line: `oc`

This is the way we used in the previous steps. There is a bunch of `oc` commands to transparently create/interact with the various YAML objects.

Here are a few we have seen in the previous steps: 

* `oc new-project training-test`
* `oc new-app --image-stream hello:latest`
* `oc scale --replicas=2 dc/hello`
* `oc create route edge --insecure-policy=Redirect --service=hello`
* `oc annotate route hello haproxy.router.openshift.io/balance=roundrobin haproxy.router.openshift.io/disable_cookies=true`

Each one of these either created or modified a YAML object in the project

> See `oc -h` for an exhaustive list

### The web console

Openshift comes with a web console that also let you deal entirely with your project objects.

Using the convention used in [step 1](../step1/README.md#push-image-to-openshift-integrated-registry), point your browser at `https://<openshift-server>/console` and use your credentials to login (`<openshift-login>` and `<openshift-pwd>`)

> Example: <https://master.wldp.fr/console>

### Raw YAML objects

Given you have (and maintain) all your project related YAML objects in files, you can easily keep track of them in SCM, modify them and apply those modifications with a single command:

```bash
oc apply -f <yaml-definition-file> 
```

Though more advanced, you can maintain this way all your **application architecture as code** and leverage it, e.g.:
* keep track of modification in **SCM**
* easily **duplicate** all your project components in another **project** or **cluster**
* **redeploy** a full project instance from code
* make **template** of your key components to later instantiate them in a row

## Leveraging the YAML

As everything is YAML, you can easily maintain all your application descriptors as you do with your applicative code.

### Export / Templates

You can easily export (with `oc export`) the current descriptors of your project. Exported YAML can:
* be a little **verbose** and deserves to be **filtered** for more readability (without losing relevant information)
* contain **project/cluster related informations** that can be easily set as **parameters** for future use.

To handle these two drawbacks, we will use `oc export --as-template` and `export-filter.py`

For `export-filter.py` to work, we will need to have the existing python `PyYAML` package installed: <https://pypi.python.org/pypi/PyYAML/>. You can install it locally with: `pip install PyYAML`

> `pip` is the standard python module installer. If not already installed as part of your python installation, install it. With `yum`, you can do `yum install PyYAML`. Else , you can have a look at: <https://pip.pypa.io/en/stable/installing/> 

* Check your selected project (`oc login` to the cluster if this is not the case)

```bash
$ oc project
Using project "training-test" on server "https://master.wldp.fr:443".
```

* For each service (`hello` and `names`), we will export `Service`, `DeploymentConfig` and `Route` objects in a dedicated file.
* To select service related resources, we will use label selection (`-l` | `--selector` option of `oc export`)

```
$ cd step5
$ oc export svc,dc,routes -l app=hello --as-template=hello | python export-filter.py > resources/hello-template.yml
$ oc export svc,dc,routes -l app=names --as-template=names | python export-filter.py > resources/names-template.yml
```

Have a look at both files:
* `resources/hello-template.yml` 
* `resources/names-template.yml` 

... and you will find a description of everything we have done in the previous steps with the various `oc` commands.


### Modify/apply

Any addition or modification you make to these files can easily be applied to the project.

As an example, let's scale the `names` service.

* Check you have a single instance of `names` running

```bash
$ oc get pods -l app=names
NAME            READY     STATUS    RESTARTS   AGE
names-1-n68dj   1/1       Running   0          22h
```

* Edit `resources/names-template.yml` to change the `replicas` field value of the `DeploymentConfig` from `1` to `2`

```yaml
- apiVersion: v1
  kind: DeploymentConfig
  metadata:
    labels:
      app: names
    name: names
  spec:
    replicas: 2 
```

* Apply the changes from standard input (`oc apply -f -`), after having processed the template with the current project/namespace (`oc process`)

```bash
$ oc project --short
training-test
$ oc process -f resources/names-template.yml NAMESPACE=training-test | oc apply -f -
service "names" configured
deploymentconfig "names" configured
```
* After a few seconds, check you have now **two** instances of `names` running:

```bash
$ oc get pods -l app=names
NAME            READY     STATUS    RESTARTS   AGE
names-1-ld5j6   1/1       Running   0          36s
names-1-n68dj   1/1       Running   0          22h
```

### Maintain

You have now a **powerful** way to **track and commit** the changes made to your application. 

Any way you use to modify your application (`oc`, web console, raw YAML), you can **periodically export** the running resources definitions and easily **track the changes**.

We have seen that we have exported our resource as `Template` objects. 

> More info: <https://docs.openshift.org/{{book.osversion}}/dev_guide/templates.html>

## Sample project duplication scenario

Now we have got our **application architecture as code**, we can imagine various scenarios related to duplication, automation, continuous deployment...

Let's have a taste of this through a sample project duplication scenario.

We will deploy here a second instance of our `training-test` project inside the same cluster: let's call it `training-test-staging`

### Create the new empty project

```bash
oc new-project <project-name>
```

```bash
$ oc new-project training-test-staging
Now using project "training-test-staging" on server "https://master.wldp.fr:443".

You can add applications to this project with the 'new-app' command. For example, try:

    oc new-app centos/ruby-22-centos7~https://github.com/openshift/ruby-ex.git

to build a new example application in Ruby.
```

### Promote your docker images 

We will easily promote docker images and related `ImageStream` (`hello` and `names`) to your new project with `oc tag` command

> More info: https://docs.openshift.org/{{book.osversion}}/dev_guide/managing_images.html#tagging-images

```
oc tag <initial-project>/<imagestream-name>:<imagestream-tag> <new-project>/<imagestream-name>:<imagestream-tag> 
```

```bash
$ oc tag training-test/hello:latest training-test-staging/hello:latest
Tag hello:latest set to training-test/hello@sha256:b36594f1f25112a0f0f4ecb7c113f11de653602f3d82af511c84079561716613.

$ oc tag training-test/names:latest training-test-staging/names:latest
Tag names:latest set to training-test/names@sha256:7ed20ee43b57559367573184a4ac962d50c1948343bf7df968af8c76021e9d0d.
```

We have now our two `ImageStream` objects

```bash
$ oc get is
NAME      DOCKER REPO                                     TAGS      UPDATED
hello     172.30.8.127:5000/training-test-staging/hello   latest    11 seconds ago
names     172.30.8.127:5000/training-test-staging/names   latest    5 seconds ago
```

> More info on application promotion: <https://docs.openshift.org/{{book.osversion}}/dev_guide/application_lifecycle/promoting_applications.html>

### Create all the resources from the templates

We will now create all the resources in the project using the `Template` previously exported:

```bash
$ oc process -f resources/names-template.yml NAMESPACE=training-test-staging | oc apply -f -
service "names" created
deploymentconfig "names" created

$ oc process -f resources/hello-template.yml NAMESPACE=training-test-staging | oc apply -f -
service "hello" created
deploymentconfig "hello" created
route "hello" created
```

After a few seconds/minutes, you can then browse your duplicated app at: `https://<route-name>-<new-project-name>.<openshift-cluster-domain>/`

* In our example: <https://hello-training-test-staging.wldp.fr>

That's it!

### Optionally delete your staging test project:

```
oc delete project <project-name>
```

```bash
$ oc delete project training-test-staging
project "training-test-staging" deleted
```

## Going further

Learn more: [Dealing with volumes](../step6/)

