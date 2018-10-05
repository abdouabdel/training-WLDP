#!/usr/bin/env python

import os
import re
import subprocess
import sys
import yaml

INFO_ANNOTATIONS = ['openshift.io/generated-by', 'openshift.io/host.generated']
PVC_BINDING_ANNOTATIONS = ['pv.kubernetes.io/bound-by-controller', 'pv.kubernetes.io/bind-completed']

EMPTY_VALUES = {
	'activeDeadlineSeconds': 21600,
	'annotations': None,
	'creationTimestamp': None, # null become None when parsed
	'importPolicy': {},
	'resources': {},
	'securityContext': {}
}

DEFAULT_VALUES = {
	'dnsPolicy': 'ClusterFirst',
	'generation': any,
	'imagePullPolicy': any,
	'referencePolicy': {
		'type': ''
	},
	'restartPolicy': 'Always',
	'sessionAffinity': 'None', 
	'strategy': {
		'rollingParams': {
			'intervalSeconds': 1,
			'maxSurge': '25%',
			'maxUnavailable': '25%',
			'timeoutSeconds': 600,
			'updatePeriodSeconds': 1
		},
		'type': 'Rolling'
	},
	'terminationGracePeriodSeconds': 30,
	'terminationMessagePath': '/dev/termination-log',
 	'test': 'false',
	'weight': 100,
	'wildcardPolicy': 'None'
}

# generic way to walk the object tree (parsed from yaml)
def delegate_filter(obj, delegate):
	if isinstance(obj, dict):
		delegate(obj)
		# iterate over remaining ones
		for k, v in obj.iteritems():
			delegate_filter(v, delegate)
	if isinstance(obj, (list, tuple)):
		for item in obj:
			delegate_filter(item, delegate)

# remove default values for more clarity (list of default values is maintained in DEFAULT_VALUES)
def filter_default_values(obj):
	def delegate(obj):
		# todo check default values keys and remove
		for k, v in DEFAULT_VALUES.iteritems():
			if k in obj and (v == any or v == obj[k]):
				del obj[k]
	delegate_filter(obj, delegate)

# remove empty values for more clarity (list of empty value is maintained in EMPTY_VALUES)
def filter_empty_values(obj):
	def delegate(obj):
		# todo check empty values keys and remove
		for k, v in EMPTY_VALUES.iteritems():
			if k in obj and (v == None or v == obj[k]):
				del obj[k]
	delegate_filter(obj, delegate)	

# remove status field
def filter_status(obj):
	def delegate(obj):
		if 'status' in obj:
			del obj['status']
	delegate_filter(obj, delegate)	

# remove annotations based on a list of annotation keys
def filter_annotations(obj, keys = []):
	def delegate(obj):
		# check for annotations
		if 'annotations' in obj and obj['annotations'] is not None:
			for annot in keys:
				if annot in obj['annotations']:
					del obj['annotations'][annot]
			if len(obj['annotations']) == 0:
				del obj['annotations']
	delegate_filter(obj, delegate)

# remove informative annotations for better yaml clarity
def filter_info_annotations(obj):
	filter_annotations(obj, INFO_ANNOTATIONS)

# disconnect pvc (remove binding related annotations)
def filter_disconnect_pvc(obj):
	if obj['kind'] != 'PersistentVolumeClaim':
		return
	filter_annotations(obj, PVC_BINDING_ANNOTATIONS)

# remove default service accounts: in a case of a project duplication, those ones will be recreated
def filter_remove_default_sa(obj):
	if obj['kind'] != 'ServiceAccount':
		return False
	return obj['metadata']['name'] in ('builder', 'default', 'deployer')

# remove imagestream image sha256	
def filter_remove_image_sha(obj):
	def delegate(obj):
		if 'image' in obj:
			obj['image'] = re.sub(r'^([^@]+)@sha256.*$', r'\1', 	obj['image'])
	delegate_filter(obj, delegate)
	pass

# parametrize imagestream to be project/cluster independant
def filter_parametrize_is(obj, namespace):
	def delegate(obj):
		if 'image' in obj:
			if obj['image'].find('/' + namespace + '/') != -1:
				obj['image'] = re.sub('^[^/]+/' + namespace + '/(.*)$', r'${REGISTRY}/${NAMESPACE}/\1', obj['image'])
		if 'namespace' in obj and obj['namespace'] == namespace:
			obj['namespace'] = '${NAMESPACE}'
	delegate_filter(obj, delegate)
	pass	

# enforce default route host mechanism by removing 'host' field
# will be recreated with the default convention: <route-name>-<project-name>.<cluster-suffix>
def filter_update_route_host(obj):
	if obj['kind'] != 'Route':
		return
	if 'host' in obj['spec']:
		del obj['spec']['host']

# apply filters based on the given options
def filter_all(obj, options, is_template, namespace):
	if is_template:
		objects = obj['objects']
	else:
		objects = obj['items']
	
	if is_template and not args.skip_ns_param:
		filter_add_template_param(obj, 'NAMESPACE', description='The namespace where ImageStreams reside')
		filter_add_template_param(obj, 'REGISTRY',  description='The internal docker registry', required=False, value='<integrated-docker-registry>')
		filter_parametrize_is(obj, namespace)

	if not options.keep_empty:
		filter_empty_values(obj)
	if not options.keep_defaults:
		filter_default_values(obj)
	if not options.keep_status:
		filter_status(obj)

	if not options.keep_info_annotations:
		filter_info_annotations(obj)
	if not options.keep_is_refs:
		filter_remove_image_sha(obj)

	for item in objects[:]:
		if not options.keep_pvc_connections:
			filter_disconnect_pvc(item)
			if filter_remove_default_sa(item):
				objects.remove(item)
		if not options.keep_route_host:
			filter_update_route_host(item)

def filter_add_template_param(obj, name, required=True, value=None, description=None, displayName=None):
	if not 'parameters' in obj:
		obj['parameters'] = []
	param = {'name': name}
	param['required'] = required
	if value != None:
		param['value'] = value
	if description != None:
		param['description'] = description
	if displayName != None:
		param['displayName'] = displayName
	obj['parameters'].append(param)


def get_current_project():
	DEVNULL = open(os.devnull, 'w')
	return subprocess.check_output(['oc', 'project', '--short'], stderr=DEVNULL).strip()

# read openshift objects yaml export and filter it
def main(args):
	export = yaml.load(args.file)
	if export == None:
		return

	namespace = None
	if not args.skip_ns_param:
		is_template = export['kind'] == 'Template'
		if is_template:
			try:
				namespace = get_current_project()
			except:
				sys.stderr.write('error: failed to get current project with oc\n')
				sys.exit(1)
	
	filter_all(export, args, is_template, namespace)
	yaml.dump(export, stream=sys.stdout, default_flow_style=False)

	

if __name__ == '__main__':
	# following ensures unix line ending in output yaml even on windows
	if sys.platform == "win32":
		import os, msvcrt
		msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

	# define command arguments
	import argparse

	desc = '''Filter openshift exported yaml

By default:
  - remove status to have a shorter output
  - remove empty values to have a shorter output
  - remove default values to have a shorter output
  - remove informational annotations to have a shorter output
  - remove Route host to have the default cluster behavior
  - remove the default service accounts ('builder', 'default', 'deployer')
  - disconnect the PersistentVolumeClaims (by removing related annotations)
	- if yaml is a Template, add NAMESPACE parameter and configure ImageStream accordingly, else remove ImageStream image reference (sha256)
  
'''

	parser = argparse.ArgumentParser(description = desc,
	formatter_class=argparse.RawDescriptionHelpFormatter)

	parser.add_argument('file', metavar = '<openshift-export-yml-file>', nargs = '?', type = argparse.FileType('r'), default = sys.stdin, help='defaults to stdin')
	parser.add_argument('--keep-status',             dest = 'keep_status', help = 'keep status field', action = "store_true")
	parser.add_argument('--keep-empty',              dest = 'keep_empty', help = 'keep empty values', action = "store_true")
	parser.add_argument('--keep-defaults',           dest = 'keep_defaults', help = 'keep default values', action = "store_true")
	parser.add_argument('--keep-info-annotations',   dest = 'keep_info_annotations', help = 'keep info annotations', action = "store_true")
	parser.add_argument('--keep-is-refs',            dest = 'keep_is_refs', help = 'keep ImageStream references', action = "store_true")
	parser.add_argument('--keep-route-host',         dest = 'keep_route_host', help = 'keep Route host', action = "store_true")
	parser.add_argument('--keep-default-sa',         dest = 'keep_default_sa', help = 'keep default ServiceAccounts', action = "store_true")
	parser.add_argument('--keep-pcv-connections',    dest = 'keep_pvc_connections', help = 'keep PersistentVolumeClaim connections', action = "store_true")
	parser.add_argument('--skip-ns-parametrization', dest = 'skip_ns_param', help = 'skip NAMESPACE parameter', action = "store_true")

	args = parser.parse_args()
	main(args)


	