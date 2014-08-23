#!/usr/bin/python

import boto.ec2
import boto.vpc

###
## User Configuration
###
default_region="us-east-1"

###
## Config stuff you probably don't need to change
###
awsPublicKeyPath="~/.awsProxy.pub"
awsPrivateKeyPath="~/.awsProxy"

###
## Code happens here. You shouldn't need to change anything below here
###

###
## Constants
###
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

###
## Finding Instances
### 

def findProxyInstance(instances):
    retval = None
    if instances is not None:
        for instance in instances:
            if instance.tags.get(AWSProxyKey) is not None:
                retval = instance
                break
    return retval
    
def findExistingEC2Instance(ec2):
    return findProxyInstance(ec2.get_only_instances())
    
def findExistingSecurityGroup(ec2):
    return findProxyInstance(vpc.get_all_security_groups())
    
def findExistingInternetGateway(vpc):
    return findProxyInstance(vpc.get_all_internet_gateways())
    
def findExistingVPCInstance(vpc):
    return findProxyInstance(vpc.get_all_vpcs())
    
def findExistingSubnet(vpc):
    return findProxyInstance(vpc.get_all_subnets())

def findExistingRouteTable(vpc):
    return findProxyInstance(vpc.get_all_route_tables())

def findExistingNetworkACL(vpc):
    return findProxyInstance(vpc.get_all_network_acls())

###
## Creating Instances
###
def createVPCInstance(vpc):
    pass
    
###
## Updating Instances
###    
def updateSecurityGroup(securityGroup):
    # TODO: Add the current IP address to the security group
    pass
    
###
## Fetching Instances
###
def getSecurityGroupFromInstance(ec2, instance):
    attributes = ec2.get_instance_attribute(instances[0].id, "groupSet")
    securityGroupId = attributes.get("groupSet")[0].id
    retval = None
    for securityGroup in ec2.get_all_security_groups()
        if securityGroup.id == securityGroupId
            retval = securityGroup
            break
    return retval
    
def getVPCInstance():
    vpc = boto.vpc.connect_to_region(default_region)
    instance = findExistingVPCInstance(vpc)
    if instance is None:
        instance = createVPCInstance(vpc)
    
    return instance
    
def getEC2Instance(ec2):
    instance = findExistingEC2Instance(ec2)
    
    if instance is None:
        # TODO: Create an instance
        pass

    if instance is not None:
        securityGroup = getSecurityGroupFromInstance(ec2, instance)
        updateSecurityGroup(securityGroup)
    
    return instance

###
## Starting Instances
###

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
    instance = getEC2Instance(ec2)
    
    if instance is not None:
        startInstance(ec2, instance)
        return instance.public_dns_name

    return None
    
ip = startImageAndGetIP()
if ip is not None:
    print "Proxy IP is "+ip