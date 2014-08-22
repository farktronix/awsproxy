#!/usr/bin/python

import boto.ec2

# Configuration
default_region="us-east-1"

# Config stuff you probably don't need to change
awsPublicKeyPath="~/.awsProxy.pub"
awsPrivateKeyPath="~/.awsProxy"

# Code happens here
ec2StatePending = 0
ec2StateRunning = 16
ec2StateShuttingDown = 32
ec2StateTerminated = 48
ec2StateStopping = 64
ec2StateStopped = 80

ec2ImageWait = 0
ec2ImageReady = 1
ec2ImageNotRunning = 2
ec2ImageNotFound = 3

AWSProxyKey = "AWSProxy"

userData = "#!/bin/bash\
sudo apt-get install tinyproxy"

def getProxyInstance(ec2):
    instances = ec2.get_only_instances()
    retval = None
    for instance in instances:
        if instance.tags.get(AWSProxyKey) is not None:
            retval = instance
            break
    return retval

#returns:
# ec2ImageWait if the image is transitioning between states. The state should be checked again in a couple seconds.
# ec2ImageReady if the image is running and ready to be used
# ec2ImageNotRunning if the image needs to be started
def getInstanceState(ec2, instance):
    if instance is None:
        return ec2ImageNotFound
    if (instance.state_code == ec2StatePending or instance.state_code == ec2StateShuttingDown or instance.state_code == ec2StateStopping):
        return ec2ImageWait
    if instance.state_code == ec2StateRunning:
        return ec2ImageReady
    return ec2ImageNotFound

def startInstance(ec2, instance):
    print "Found instance: "+str(instance)+", state is "+instance.state
    waitTime = 0
    didStart = False
    while waitTime < 30:
        status = getInstanceState(ec2, instance)
        if status == ec2ImageReady:
            break
        elif status == ec2ImageNotRunning and not didStart:
            print "Starting instance "+str(instance)
            #ec2.start_instances(instance.id)
            didStart = True
        elif status == ec2ImageNotFound:
            break;
        time.sleep(1)
        waitTime = waitTime + 1
    if waitTime == 30:
        print "Timed out waiting for instance "+str(instance)+" to start. Current state is "+instance.state
        
def startImageAndGetIP():
    ip = None
    ec2 = boto.ec2.connect_to_region(default_region)
    instance = getProxyInstance(ec2)
    if instance is None:
        print "Couldn't find AWSProxy instance. Creating a new one"
        # TODO: Create a new instance
    
    if instance is not None:
        startInstance(ec2, instance)
    
    return instance.public_dns_name
    
ip = startImageAndGetIP()
if ip is not None:
    print "Proxy IP is "+ip