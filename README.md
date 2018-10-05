# WLDP for developers

We will see through a series of simple examples a way to become familiar with [Openshift](https://docs.openshift.org/{{book.osversion}}/welcome/index.html) and the Worldline Digital Platform.

The project [wldp-dev-training](https://gitlab.kazan.priv.atos.fr/deepskyproject/wldp-dev-training) will contain all the resources referenced in these few tutorials.

## Hello World

As a first step we will make a very simple service and deploy it to an Openshift platform instance. This will help us to approach some basic concepts and to install the required tools to go further.

* [Hello World on Openshift](step1/)

## Developing with Openshift as a back-end

Then we will see how we can make our life easier by developing with Openshift as a back-end. We will reuse what we've learned in the previous step and introduce some new tools.

* [Developing with Openshift as a back-end](step2/)

## Service discovery and proxy concerns

Here we'll have a closer look at Openshift built-in service discovery mechanisms as well as proxy concerns when it comes to query both private services and public ones.

* [Service discovery and proxy concerns](step3/)

## Continuous integration (CI)

We will how to configure continuous integration to push images to Openshift integrated registry.

* [Continuous integration (CI)](step4/)

## Dealing with Openshift API objects

In this step we will have a closer look at how to deal with Openshift API objects that describe your application architecture.

* [Dealing with Openshift API objects](step5/)