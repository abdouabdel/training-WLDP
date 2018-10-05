# Promote services between environments on a cluster

This step explain how to handle service's development using PS registries. 
During the lifetime of a project, you'll have to update your services and manage differents environments (dev, staging, production, ...) and their corresponding version of your services. In this document, we'll describe a way to handle that, using PS registries (testing and production).

## Introduction 

## An exemple of a WorkFlow

First, create two project on your Openshift platform. For exemple, a development namespace and a second who represent a production environment. 

### Hello World in dev environment

Using the [official documentation](https://kazan.atosworldline.com/share/data/docker/documentation/registry/presentation/), publish the version '1.0' of your service on the 'testing' registry.

For information, in this exemple we used the directory "hello_1.0" of the dev-training repository : step 8.
We also use our deepsky section to push on PS registries. So if you want to reproduce the following commands make sur you have access rights to the section where you want to push your images. 

```bash
dock_add -d <dockerfile_dir> -B <git_branch> <git_repo_url> <your_code>/awl-<your_code>-<app-name>:1.0
```
```bash
dock_add -d step8/hello_v1.0 -B develop https://gitlab.kazan.priv.atos.fr/deepskyproject/wldp-dev-training.git deepsky/awl-deepsky-hello:1.0
```

These commands will clone your git repo, build the image and push it to the testing registry. (You need to be connected to ydpds03s from the bastion using your DAS : ssh $DAS@ydpds03s)

When done, you will be able to create an imageStreamTag 'hello-app:dev' based on the newly published '1.0' of your service, and deploy it.

From a terminal where oc-cli is installed, connect to your development environment (Your dev namespace for this exemple) and reproduce the following commands.

```bash
oc tag <testing_registry_url>/<code_object>/<image_name>:<version> <tag_name>:<version>
oc new-app <tag_name>:<version>
```

```bash
oc tag registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.0 hello-app:dev
oc new-app hello-app:dev
```

If you create a Route on the port 8080 and follow the link, you will see a beautiful website showing : "Hello World! I'm using the version 1.0".

### Let's go to production 

After some validation, you may decide to publish your service on production cluster. First, follow the [documentation](https://kazan.atosworldline.com/share/data/docker/documentation/registry/presentation/) to promote your service to the production registry.

> Execute this command from the ydpds03s machine from bastion.

```bash
dock_promote <object_code>/<image_name>:<version>
```

```bash
dock_promote deepsky/awl-deepsky-hello:1.0
```

Then create an imageStreamTag 'hello-app:prod' and deploy it.

Like before, when done, you will be able to create an imageStreamTag 'hello-app:prod' based on the newly published '1.0' of your service, and deploy it. Don't forget to switch to your production namespace and run theses commands from a terminale where oc-cli is installed.


```bash
oc tag <registry_url>/<code_object>/<image_name>:<version> <tag_name>:<version>
oc new-app <tag_name>:<version>
```

```bash
oc tag registry.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.0 hello-app:prod
oc new-app hello-app:prod
```

If you've correctly done these steps, you will see by following the route the same message as the dev service because you're using the same version.


### Evolution of application

What's happen if your application evolve? It's time to discover it by doing a version 1.1 of your service. 
When developments are done, publish the '1.1' of your service on the 'testing' registry. You can also use the directory "hello_1.1" of this section. 

Reproduce the same procedure as before and update the imageStreamTag 'dev' to this new version.

```bash
dock_add -d step8/hello_v1.1 -B develop https://gitlab.kazan.priv.atos.fr/deepskyproject/wldp-dev-training.git deepsky/awl-deepsky-hello:1.1
```

```bash
oc tag registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.1 hello-app:dev
```

> As the imageStreamTag change, the deploymentConfig based on it is automatically redeployed and you will see another message on the website : "Hello World! I'm using version 1.1." if you've used the gived sample "hello_1.1".

As previously, when you want to upgrade your production cluster, you can promote version '1.1' and update the imageStreamTag 'prod'.


```bash
dock_promote deepsky/awl-deepsky-hello:1.1
```

```bash
oc tag registry.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.1 hello-app:prod
```

### Patch application

Sometimes your service has a bug and you need to patch it. 
As before, make your modifications then publish the patch version to the 'testing' registry.

As there already is an imageStreamTag referencing this image tag, their is two alternatives...

> If you don't know wich case to use, please contact your cluster administrator to know if the cluster's policy include imageStream scheduling.

#### Case 1 : imageStream scheduling is active on the cluster

In that case, during the next scheduled check, Openshift will detected that the referenced image tag has changed (using sha256 fingerprint), and download new layers to update is local repository.
Depending on your deploymentConfig configuration, your DC may automatically redeploy.

#### Case 2 : imageStream scheduling is not active on the cluster

This time, you have to notify Openshift manually, so it updates his tag to the new image tag layers.

```bash
oc tag registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.1 hello-app:dev
```

> To patch the production application, reproduce the same as before, except you are working on imageStreamTag 'prod', not 'dev'. If you decide to use the same image name, use --force to promote your image (Be careful, this option will erase the previous version and it can't be undone). 

```bash
dock_promote deepsky/awl-deepsky-hello:1.1 --force
```

### Retrieving tag informations

After few weeks, months or years... it's possible that's you have forgot on wich  version of image you've choose in your ImageStreamTag. 
To retrieve this data on the development environment for exemple, you can use this command from the dev namespace: 

```bash
oc describe is <tagName>
```

```bash
oc describe is hello-app
```

You can see on the result below, that the tag corresponding to the version selected before : **registry.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.1** 

```bash
Name:                   hello-app
Namespace:              step8-dev
Created:                5 hours ago
Labels:                 <none>
Annotations:            openshift.io/image.dockerRepositoryCheck=2017-09-20T11:54:34Z
Docker Pull Spec:       172.30.32.33:5000/step8-dev/hello-app
Unique Images:          2
Tags:                   1

dev
  tagged from registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello:1.1

  * registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello@sha256:4ddcfe339dcd83f9c7617cb180c9cd1cdadc48962af076731a4e8d75ce80d87c
      3 minutes ago
    registry-testing.kazan.atosworldline.com:443/deepsky/awl-deepsky-hello@sha256:0e0cf4c8bb274194d0a5524d37f1874ecfda99b3ca64ecf059b07de43c801f7e
      5 hours ago
```

If you want more informations about this content, follow the Openshift official  [documentation](https://docs.openshift.com/enterprise/3.2/dev_guide/managing_images.html).