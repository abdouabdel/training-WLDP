# Using Openshift Configmap and Secret

## Overview
Many applications require configuration using some combination of configuration files, command line arguments, and environment variables. These configuration artifacts should be decoupled from image content in order to keep containerized applications portable.

This step describe how to used the `configmap` object which provides mechanisms to inject containers with configuration data while keeping containers agnostic of OpenShift Origin. We describe how the configuration data can be consumed in pods. 

ConfigMap is similar to secrets, but designed to more conveniently support working with strings that do not contain sensitive information. The Secret object type provides a mechanism to hold sensitive information such as passwords, OpenShift client config files, dockercfg files, private source repository credentials, etc

To demonstrate the `configmap` utility, we modify the services `names` from step2 to used a `configmap` name `name-config` for:
* Populate configuration files in a volume.
* Populate the value of environment variables.

To demonstrate the `secret` utility, we modify the services `names` from step2 to used a `secret` name `secret-config` for:
* Populate the value of environment variables (user and password).

## Services `names` evolution

`names` service has been modified from step2 to step6 to:
* read from a file name `config.ini` a properties (actor name) and display it when the user call the uri `/bestactor`. The key of the property to display in the `config.ini` file is defined by the environment variable `PROPERTY_KEY` defined in the templates.
* A new uri `/private` which takes 2 parameters: `pwd` and `usr` is added to demonstrate how to store authentication informations in a `secret`, when you call the url `/private?usr=root&pwd=root` the service return the value of the property `fact` defined into `config.ini file`. 

A new folder `config` is adding which contains the `config.ini` properties file.

```
├── hello
├── names
│   ├── Dockerfile
│   ├── config
│       └── config.ini
│   ├── run.sh
│   └── src
│       └── app.py
├── resources
│   ├── names-secrets.yml
│   └── names-templates.yml
└── README.md
```

**contains of the new app.py**
```
class HelloServerRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

	def do_GET(self):
		self.protocol_version = 'HTTP/1.1'

		status = 200
		
		# retrieve path and query params from url
		print "url=%s" % (self.path)
		from urlparse import urlparse
		url_path = urlparse(self.path).path
		print "path=%s" % (url_path)
		url_query = urlparse(self.path).query
		print "query=%s" % (url_query)
		
		# Read the property file 
		config = ConfigParser.ConfigParser()
		config.read('config/config.ini')
		
		if (url_path == '/'):
			response = names.get_full_name()
		elif (url_path == '/male'):
			response = names.get_full_name(gender='male')
		elif (url_path == '/female'):
			response = names.get_full_name(gender='female')
		elif (url_path == '/bestactor'):
		
			# retrieve the env var key
			key = os.environ['PROPERTY_KEY']
			print "This is the value of the key present in your `config.ini` into your configmap `name-config`: %s" % (key)
			response = config.get('BESTACTOR',key)
		
		elif (url_path == '/private'):
		
			# split query param to get the user and pwd params
			query_components = dict(qc.split("=") for qc in url_query.split("&"))
			usr = query_components["usr"]
			pwd = query_components["pwd"]
			print "query usr=%s" % (usr)
			print "query pwd=%s" % (pwd)
			
			# retrieve the username and password secret env var
			username = os.environ['USERNAME']
			password = os.environ['PASSWORD']
			print "configmap username=%s" % (username)
			print "configmap password=%s" % (password)

			if(password == pwd and username == usr):
				response = config.get('PRIVATE','fact')
			else:
				status = 401
				response = 'Unauthorized to access to this resource'
		...
```

The `config.ini` file contains a list of 3 `[BESTACTOR]` properties, and a properties name `fact`.

```properties
[BESTACTOR]
name-0 = Chuck Norris
name-1 = Arnold Schwarzenegger
name-2 = Sylvester Stallone
[PRIVATE]
fact = One day, Chuck Norris lost his alliance. Since it is the brothel in the middle lands ...
```

The docker image, add the `config.ini` file into a `config` folder.

```
ADD src/app.py run.sh ${HOME}/
ADD config/config.ini ${HOME}/config/
```

## Build/Tag/Push image `names` into the registry

The first step of this tutorial is to build, tag and deploy the image `names` in your openshift cluster, go to step 1 for more information.


```shell
docker build --no-cache -t wldp-dev-training/names .
docker tag wldp-dev-training/names <your-registry>:443/<your-namespace>/names
docker push <your-registry>:443/<your-namespace>/names
```

## Create `configmap` name `name-config`

Before to start a pod with the images `names:latest` on your openshift cluster, you should create the `configmap` which contains the `config.ini` file and a value for the key `property.key`

The `configmap` should:
* contains the `config.ini` file.
* defined a value for the key `property.key` (we choose to set `name-0`) that will be use after to defined the value of the environment variable `PROPERTY_KEY` defined in the yml template.

To create the `configmap` execute this command:

```shell
oc create configmap name-config --from-file=config/config.ini --from-literal=property.key=name-0
```

* When the `--from-file` option points to a directory, each file directly in that directory is used to populate a key in the ConfigMap, where the name of the key is the file name, and the value of the key is the content of the file. You can also pass the `--from-file` option with a specific file, and pass it multiple times to the CLI
* You can also supply literal values for a ConfigMap. The `--from-literal` option takes a key=value syntax that allows literal values to be supplied directly on the command line:

To verify than the `configmap` is created, you can execute this command:

```shell
oc describe configmaps name-config
```

the output of oc describe only shows the names of the keys and their sizes.

```shell
[root@localhost names]# oc describe configmaps name-config
Name:           name-config
Namespace:      a175290
Labels:         <none>
Annotations:    <none>

Data
====
config.ini:             34 bytes
property.key:       6 bytes
```

If you want to display the values of the keys, you can execute `oc get configmaps` with the -o option:

```shell
oc get configmaps name-config -o yaml
```

```shell
[root@localhost names]# oc get configmaps name-config -o yaml
apiVersion: v1
data:
  config.ini: |-
    [BESTACTOR]
    name-0 = Chuck Norris
    name-1 = Arnold Schwarzenegger
    name-2 = Sylvester Stallone
    [PRIVATE]
    fact = One day, Chuck Norris lost his alliance. Since it is the brothel in the middle lands ...
  property.key: name-2
kind: ConfigMap
metadata:
  creationTimestamp: 2017-08-18T12:51:25Z
  name: name-config
  namespace: a175290
  resourceVersion: "354385"
  selfLink: /api/v1/namespaces/a175290/configmaps/name-config
  uid: f2081015-8413-11e7-8d87-02000dca0001
```

If you go to master console and select your `namespace`, on the left menu, select: `/Resources/Config Maps` to access to yours `configmaps`.

## Create `secret` name `secret-config`

Now than the `configmap is create`, we should to create the `secret` which contains the username and password properties. To deploy the secret on the openshift cluster, we used a secret template `names-secret.yml` present into `/resources` folder:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: secret-config
data:
  username: cm9vdA==
  password: cm9vdA==
```

To create the `secret`, go to `/resources` folder and execute this command:

```shell
oc create -f names-secret.yml
```

To verify than the `secret` is created, you can execute this command:

```shell
oc describe secret secret-config
```

the output of `oc describe` only shows the names of the keys and their sizes.

```shell
[root@localhost resources]# oc describe secret secret-config
Name:           secret-config
Namespace:      a175290
Labels:         <none>
Annotations:    <none>

Type:   Opaque

Data
====
password:       4 bytes
username:       4 bytes
```

If you want to display the values of the keys, you can execute `oc get secret` with the -o option:

```shell
[root@localhost resources]# oc get secret secret-config -o yaml
apiVersion: v1
data:
  password: cm9vdA==
  username: cm9vdA==
kind: Secret
metadata:
  creationTimestamp: 2017-08-18T12:27:18Z
  name: secret-config
  namespace: a175290
  resourceVersion: "353246"
  selfLink: /api/v1/namespaces/a175290/secrets/secret-config
  uid: 935c47fa-8410-11e7-8d87-02000dca0001
type: Opaque
```

> **WARNING:** The value associated with keys in the the data map must be base64 encoded (base64: `cm9vdA==` = `root`).

If you go to master console and select your `namespace`, on the left menu, select: `/Resources/Secrets` to access to yours `secrets`.

## Deploy and process the template `names-templates.yml`

After to have push the image into the registry and create the `configmap` and `secret`, you could use the template `names-templates.yml` present into `/step7/names/resources` to deploy the service `names` on the openshift cluster. 

The template `names-templates.yml` is updated to:

* contents an environment variable `PROPERTY_KEY` which is get from the `configmap` and is Literal Values : `--from-literal=property.key=name-0`

```yaml
env:
- name: PROPERTY_KEY
  valueFrom:
    configMapKeyRef:
	  name: name-config
	  key: property.key
```

* contents 2 environments variables `USERNAME` and `PASSWORD` which is get from the `secret`

```yml
- name: USERNAME
  valueFrom:
    secretKeyRef:
	  name: secret-config
	  key: username
- name: PASSWORD
  valueFrom:
    secretKeyRef:
	  name: secret-config
	  key: password
```

* use a volume of type `configmap` which contents the `config.ini` file create previously by the parameter: `--from-file=config/config.ini`, and a volume of type `secret` (not use in this tutorial, just implemented)

```yaml
volumes:
- name: config-volume
  configMap:
	name: name-config
- name: secret-volume
  secret:
	secretName: secret-config
```

* Mount the volume `config-volume` in: `/opt/app-root/src/config` where the file `config.ini` is write, and mount the volume `secret-volume` in: `/opt/app-root/src/secret` where the `username` and `password` value are write (not use in this tutorial, just implemented)

```yaml
volumeMounts:
- name: config-volume
  mountPath: /opt/app-root/src/config
- name: secret-volume
  mountPath: /opt/app-root/src/secret-volume
  readOnly: true
```

> *WARNING:* When you process the template, don't forget to replace these paramaters by yours:
> * Image namespace: your namespace where the application is deploy
> * Image registry: your registry ip of your cluster (could be found in the registry service deploy in `default` namespace)

To verify than the service `names` run and the `configmap` and `secret` is used:
* open the `route` defined for the `names` service, and add this path to the uri: http://yourroute/bestactor, you shoud see the value defined for `name-0` present in the `config.ini` file ("Chuck Norris").
* open the `route` defined for the `names` service, and add this path to the uri: http://yourroute/private?usr=root&pwd=root, you shoud see the value defined for the properties `fact` present in the `config.ini` file ("One day, Chuck Norris lost his alliance. Since it is the brothel in the middle lands ...").
* open the `names` pod terminal from the openshift console, and display files to see your configuration and volume mount into the pod:

At the root path execute `ls -la` to display the volumes mounts `secret` and `config`

```shell
sh-4.2$ ls -la                                                                                                                                                             
total 12                                                                                                                                                                   
drwxr-xr-x 4 root root         69 Aug 21 09:41 .                                                                                                                           
drwxr-xr-x 3 root root         17 Aug 18 13:46 ..                                                                                                                          
-rwxrwxrwx 1 root root       3884 Aug 18 13:13 app.py                                                                                                                      
drwxrwsrwx 3 root 1000100000 4096 Aug 21 09:41 config                                                                                                                      
-rwxrwxrwx 1 root root         61 Jul 26 09:39 run.sh                                                                                                                      
drwxrwsrwt 3 root 1000100000  120 Aug 21 09:41 secret
```

go to `config` folder to display `config.ini ` and `property.key`

```shell
sh-4.2$ ls -la                                                                                                                                                             
total 8                                                                                                                                                                    
drwxrwsrwx 3 root 1000100000 4096 Aug 21 09:41 .                                                                                                                           
drwxr-xr-x 4 root root         69 Aug 21 09:41 ..                                                                                                                          
drwxr-sr-x 2 root 1000100000 4096 Aug 21 09:41 ..8988_21_08_11_41_45.259935835                                                                                             
lrwxrwxrwx 1 root root         31 Aug 21 09:41 ..data -> ..8988_21_08_11_41_45.259935835                                                                                   
lrwxrwxrwx 1 root root         17 Aug 21 09:41 config.ini -> ..data/config.ini                                                                                             
lrwxrwxrwx 1 root root         19 Aug 21 09:41 property.key -> ..data/property.key
```

go to `secret` folder to display `username` and `password`

```shell
sh-4.2$ ls -la                                                                                                                                                       
total 0                                                                                                                                                                    
drwxrwsrwt 3 root 1000100000 120 Aug 21 09:41 .                                                                                                                            
drwxr-xr-x 4 root root        69 Aug 21 09:41 ..                                                                                                                           
drwxr-sr-x 2 root 1000100000  80 Aug 21 09:41 ..8988_21_08_11_41_45.833726462                                                                                              
lrwxrwxrwx 1 root root        31 Aug 21 09:41 ..data -> ..8988_21_08_11_41_45.833726462                                                                                    
lrwxrwxrwx 1 root root        15 Aug 21 09:41 password -> ..data/password                                                                                                  
lrwxrwxrwx 1 root root        15 Aug 21 09:41 username -> ..data/username    
```

## Update the `configmap`

In this step, we want to update the environment variable `PROPERTY_KEY` defined by the value of the key `property.key` into the `config.ini` file present in the `configmap`.

* Delete the actual `configmap`: `name-config`:
```shell
oc delete configmap name-config
```

* Update the value of `property.key` (name-0) into `config.ini` file (`/step7/names/config/`)
```shell
[DEFAULT]
name-0 = Will Smith
name-1 = Arnold Schwarzenegger
name-2 = Sylvester Stallone
[PRIVATE]
fact = One day, Chuck Norris lost his alliance. Since it is the brothel in the middle lands ...
```

* Re-create the `name-config` `configmap` with the new `config.ini` and a new value for the key `property.key`:
```shell
oc create configmap name-config --from-file=config/config.ini --from-literal=property.key=name-0
```

* Re deploy the pod to apply the new configmap
```shell
oc deploy --latest dc/names
```

Now if you access to the `/bestactor` path you should see: `Will Smith`. 

> *WARNING*: By default when a `configmap` change the pod is not re-deploy. A feature is in works: https://github.com/kubernetes/kubernetes/issues/22368 about this subject.

## Update the `secret`

In this step, we want to update the environment variable `PASSWORD` and `USERNAME` of the pod which are get from the `secret`.

* Delete the actual `secret`: `secret-config`
```shell
oc delete secret secret-config
```

* Update into `names-secret.yml` the value defined for `username` and `password` key (don't forget than the value should be in base64 encoded, you can use this web site to convert your selected value: https://www.base64encode.org/)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: secret-config
data:
  username: YmFyYmll
  password: YmFyYmll
```

* Re-create the `secret-config` `secret`
```shell
oc create -f names-secret.yml
```

* Re deploy the pod to apply the new secret
```shell
oc deploy --latest dc/names
```

Now if you want top access to the `/private` path used these parameters : ?usr=barbie&pwd=barbie

> *WARNING*: By default when a `secret` change the pod is not re-deploy. A feature is in works: https://github.com/kubernetes/kubernetes/issues/22368 about this subject.