# Continuous integration (CI)

This step is about **automating** the build and push of docker images to Openshift integrated registry. 

In the previous steps, we have manually built and pushed `hello` and `names` docker images using a local `docker` engine and pushed them to Openshift with your personal credentials.

Doing this step we will:
* create a git repository
* explain how to get authentication token to act as a `ServiceAccount` instead of using your personal credentials
* show you how to configure a CI job using these credentials to trigger the build and push of the docker images

> We will use Gitlab and Gitlab CI (<https://gitlab.com/> and <https://docs.gitlab.com/ee/ci/>) but concepts are applicable to any source control and CI engine.

## Create a new empty `git` repository on <https://gitlab.com>

### Prerequisites
* Create an account on <https://gitlab.com>
* Configure it at least with a password access to use `git` in `https`
* Have `git` installed (command-line)

> Optionnaly configure your proxy environment variables depending on your environment if necessary (`HTTP_PROXY`, `HTTPS_PROXY` / `http_proxy`, `https_proxy`) so `git` can access _gitlab.com_

### Create the remote repository

* Go and sign-in to <https://gitlab.com>
* Create a new private project: `wldp-dev-training-step4`
*  You have now a brand new remote `git` repository at: [https://gitlab.com/\<gitlab-username\>/wldp-dev-training-step4](https://gitlab.com/<gitlab-username>/wldp-dev-training-step4)

### Init your local repository

In a first hand, we will just push to this new repository `hello` and `names` sources. This will allow us to check the `git` and _gitlab.com_ configuration

* Init the git repository locally

```bash
$ cd step4
$ git init
Initialized empty Git repository in ~/wldp-dev-training/step4/.git/
$ git add hello names .gitattributes README.md
$ git commit -m "chore(app): initial commit"
```

### Push to the remote

* Link your local repository to the remote one on _gitlab.com_ (put your `<gitlab-username>`)

<pre>
$ git remote add origin https://gitlab.com/<b>&lt;gitlab-username&gt;</b>/wldp-dev-training-step4.git
</pre>

* Push the code to the _gitlab.com_ remote

> You should be asked your _gitlab.com_ credentials (login/password)

```bash
$ git push -u origin master
```


## `ServiceAccounts` and related `Secrets`

As shown in [step1](../step1/), to push a docker image, you need to log in to the Openshift integrated docker registry using the **token** based on your personal user credentials:

```bash
docker login -u unused -p $(oc whoami -t) <integrated-registry-server>
```

However it is common to make API calls independently **without a regular user's credentials**, like external applications making API calls for monitoring or integration purposes.

### The default `ServiceAccounts`

Openshift `ServiceAccounts` provide a flexible way to control Openshift API access without sharing a regular user’s credentials.
Three `ServiceAccounts` are automatically created in every project: `builder`, `deployer` and `default`.

By default, all `ServiceAccounts` in a project have right to pull any image in the same project (`system:image-puller` role). Only the **`builder`** `ServiceAccount` has right to **push** any image in the same project (`system:image-builder` role).

To view the list of existing `ServiceAccounts` in the current project, run the following command:

``` bash
$ oc get sa
NAME       SECRETS   AGE
builder    2         2d
default    2         2d
deployer   2         2d
```

As soon as a `ServiceAccount` is created, two `Secrets` are automatically added to it:
* `<service-account-name>-`**`token`**`-<uid>`: contains a **token** to authenticate to the Openshift API (and integrated docker registry)
* `<service-account-name>-`**`dockercfg`**`-<uid>`: contains a `.dockercfg` file with credentials for the Openshift integrated registry

Both of them can be revoked by deleting the `Secret` object. When the `Secret` is deleted, a new one is automatically generated to take its place.

To have more information about a `ServiceAccount`, run following command:

```bash
oc describe sa <service-account-name>
```

<pre>
$ oc describe sa builder
Name:           builder
Namespace:      training-test
Labels:         <none>

Image pull secrets:     builder-dockercfg-qgs6q

Mountable secrets:      <b>builder-token-5j2tn</b>
                        <b>builder-dockercfg-qgs6q</b>

Tokens:                 builder-token-5j2tn
                        builder-token-w0f2z

</pre>

> More on `ServiceAccounts`: <https://docs.openshift.org/{{book.osversion}}/dev_guide/service_accounts.html>

> More on `Roles`: <https://docs.openshift.org/{{book.osversion}}/admin_guide/manage_authorization_policy.html#viewing-cluster-policy>


### Where is the token?

* `builder-`**`dockercfg`**`-xxxxx` kind of `Secret` contains credentials to access the the registry from **inside** the Openshift cluster (aims to be mounted inside build `Pods`,for example).

* `builder-`**`token`**`-xxxxx` kind of `Secret` easily exposes the token to both access the Openshift API and authenticate to the integrated registry (in fact, there is two `Secrets` of this kind but they are equivalent)

We will find the wanted token from the latter:

```bash
oc describe secret <builder-token-xxxxx> 
```

<pre>
$ oc describe secrets <b>builder-token-5j2tn</b>
Name:           <b>builder-token-5j2tn</b>
Namespace:      training-test
Labels:         <none>
Annotations:    kubernetes.io/service-account.name=builder
                kubernetes.io/service-account.uid=9c4029b9-7785-11e7-b338-00505695486b

Type:   kubernetes.io/service-account-token

Data
====
ca.crt:         6696 bytes
namespace:      13 bytes
service-ca.crt: 7812 bytes
<b>token</b>:          <b>eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3Nlcn...</b>
</pre>

### One-liner in a Unix shell
In an Unix shell, you can also get the value of the token by running the command below.

```bash
oc get sa/builder --template='{{range .secrets}}{{ .name }} {{end}}' | xargs -n 1 oc get secret --template='{{ if .data.token }}{{ .data.token }}{{end}}' | head -n 1 | base64 -d -
```

## Configuring Gitlab CI

### Set the token as a secret CI variable

To keep our CI job definition (`.gitlab-ci.yml` file) cluster-independent, we will define both docker **registry** and **token** as job variables.

* Let's go back to the _gitlab.com_ project page ([https://gitlab.com/\<gitlab-username\>/wldp-dev-training-step4](https://gitlab.com/<gitlab-username>/wldp-dev-training-step4))
* Project-level secret variables can be added by going to your project's _Settings_ ➔ _Pipelines_, then finding the section called _Secret variables_.
* Define the following three variables


Variable          | Description | Example value
-----------------|----------|---------
`NAMESPACE`      | The Openshift project name | `training-test`
`REGISTRY`       | The Openshift integrated registry public URL | `docker-registry-default.wldp.fr:443`
`REGISTRY_TOKEN` | The token you have extracted just before (from `builder-`**`token`**`-xxxxx`)  | `eyJhbGciOiJSUzI1NiIs...`
 

> More Gitlab CI secret variables: <https://docs.gitlab.com/ee/ci/variables/#secret-variables>

### The `.gitlab-ci.yml` file

This file defines your CI jobs. The one included just does three things for each image (`hello` and `names`):

* It builds the docker images (`docker build...`)
* It log in (`docker login...`) to the configured docker registry (`REGISTRY`) using the configured token (`REGISTRY_TOKEN`)
* It pushes the images to this registry (`docker push...`) in the correct namespace (`training-test`)

```yaml
# NAMESPACE, REGISTRY and REGISTRY_TOKEN have to be defined in Gitlab CI pipeline secret variables

# Definition of the anchor named build-image-definition that have the main properties for job that will build and push
.build-image: &build-image-job
  image: docker
  tags: 
    - docker
  script:
    - docker build -t $REGISTRY/$NAMESPACE/$IMAGE_NAME $IMAGE_NAME
    - docker login -u unused -p $REGISTRY_TOKEN $REGISTRY
    - docker push $REGISTRY/$NAMESPACE/$IMAGE_NAME

# The jobs that based on the anchor build-image-job with IMAGE_NAME as additional variables
build-hello:
  <<: *build-image-job
  variables:
    IMAGE_NAME: hello

build-names:
  <<: *build-image-job
  variables:
    IMAGE_NAME: names

# declare docker:dind (Docker IN Docker) as a service, so that docker command can work on gitlab.com shared runners
services:
  - docker:dind    		
```

> More info on `gitlab-ci.yml`: <https://docs.gitlab.com/ee/ci/yaml>, on job templates: <https://docs.gitlab.com/ee/ci/yaml/#special-yaml-features>

### Trigger the CI jobs

* Check the `ImageStreams` state:

<pre>
$ oc get is
NAME      DOCKER REPO                             TAGS      UPDATED
hello     172.30.8.127:5000/training-test/hello   latest    <b>3 days ago</b>
names     172.30.8.127:5000/training-test/names   latest    <b>2 days ago</b>
</pre>

* Trigger the CI job on _gitlab.com_ by commiting and pushing this `.gitlab-ci.yml` file.

```bash
$ git add .gitlab-ci.yml
$ git commit -m "chore(build): configure CI job"
$ git push
```
* Go to the _Pipelines_ page of your project ([https://gitlab.com/\<gitlab-username\>/wldp-dev-training-step4](https://gitlab.com/<gitlab-username>/wldp-dev-training-step4/pipelines)), you should see your _running_ pipeline
* You can have a look at the pipelines jobs logs
* Once the pipeline is in _passed_ state, your `ImageStreams` should have been updated with freshly built versions of your images:

<pre>
$ oc get is
NAME      DOCKER REPO                             TAGS      UPDATED
hello     172.30.8.127:5000/training-test/hello   latest    <b>2 minutes ago</b>
names     172.30.8.127:5000/training-test/names   latest    <b>2 minutes ago</b>
</pre>
> From that moment, any future push on the git repository would trigger a new CI pipeline

## Clean up and go further

Go to your project settings page ([https://gitlab.com/\<gitlab-username\>/wldp-dev-training-step4](https://gitlab.com/<gitlab-username>/wldp-dev-training-step4/edit)) and remove your project now you're done.


Now, learn more about how to [deal with Openshift API objects](../step5/)

 