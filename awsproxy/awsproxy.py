#!/usr/bin/python

import boto.ec2
import boto.vpc
from urllib import urlopen
import re
import collections
import logging

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
AWSProxyName = "AWS Proxy"

InstanceAMIID = "ami-864d84ee"
InstanceType = "t2.micro"

userData = "#!/bin/bash\
sudo apt-get install tinyproxy"

# Follow instruction at http://www.datastax.com/docs/1.0/install/install_ami
# to define the cluster security group rules and client security group rules.
SecurityGroupRule = collections.namedtuple("SecurityGroupRule", ["ip_protocol", "from_port", "to_port", "cidr_ip", "src_group_name"])

class AWSProxy:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())
        self.logger.debug("AWSProxy is here to help")
        
        self.ec2 = None
        self.vpc = None
        self.instance = None
        self.vpcInstance = None
        self.default_region = default_region
        self.CIDR = '10.0.0.0/24'
        self.proxyTag = AWSProxyKey + "-" + self.default_region
        self.connected = False
        
    def connect(self):
        if not self.connected:
            self.logger.debug("Connecting to AWS region %s" % self.default_region)
            self.ec2 = boto.ec2.connect_to_region(self.default_region)
            self.vpc = boto.vpc.connect_to_region(self.default_region)
            if self.ec2 is not None and self.vpc is not None:
                self.logger.debug("Successfully connected to AWS in region %s" % self.default_region)
                self.connected = True
            else:
                self.logger.error("Failed to connect to AWS in region %s" % self.default_region)
        
    def addTags(self, botoItem):    
        botoItem.add_tag("Name", AWSProxyName)
        botoItem.add_tag(AWSProxyKey, self.proxyTag)

###
## Instance Variables
### 
    def instanceIP(self):
        if self.instance is not None:
            return self.instance.public_dns_name
        return None
    
    def getPublicIp(self):
        data = str(urlopen('http://checkip.dyndns.com/').read())
        # data = '<html><head><title>Current IP Check</title></head><body>Current IP Address: 65.96.168.198</body></html>\r\n'
        return re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(data).group(1)
            
    def hostIP(self):
        if self.ip is None:
            self.ip = self.getPublicIp()
            self.logger.debug("Current IP is %s" % self.ip)
        return self.ip

###
## Finding Instances
### 

    def findProxyInstance(self, instances):
        retval = None
        if instances is not None:
            for instance in instances:
                proxyTag = instance.tags.get(AWSProxyKey)
                if proxyTag is not None and proxyTag == self.proxyTag:
                    retval = instance
                    break
        return retval
    
    def findExistingEC2Instance(self):
        return self.findProxyInstance(self.ec2.get_only_instances())
    
    def findExistingSecurityGroup(self):
        return self.findProxyInstance(self.vpc.get_all_security_groups())
    
    def findExistingInternetGateway(self):
        return self.findProxyInstance(self.vpc.get_all_internet_gateways())
    
    def findExistingVPCInstance(self):
        return self.findProxyInstance(self.vpc.get_all_vpcs())
    
    def findExistingSubnet(self):
        return self.self.findProxyInstance(self.vpc.get_all_subnets())

    def findExistingRouteTable(self):
        return self.findProxyInstance(self.vpc.get_all_route_tables())

    def findExistingNetworkACL(self):
        return self.findProxyInstance(self.vpc.get_all_network_acls())

###
## Creating Instances
###
    def findItemWithVPCID(self, items, vpc):
        item = None
        for i in items:
            if i.vpc_id == vpc.id:
                item = i
                break
        return item
    
    def getSubnetForVPC(self, vpc):
        return self.findItemWithVPCID(self.vpc.get_all_subnets(), vpc)
            
    def getNetworkACLForVPC(self, vpc):
        return self.findItemWithVPCID(self.vpc.get_all_network_acls(), vpc)
    
    def getRouteTableForVPC(self, vpc):
        return self.findItemWithVPCID(self.vpc.get_all_route_tables(), vpc)
        
    def getSecurityGroupForVPC(self, vpc):
        return self.findItemWithVPCID(self.vpc.get_all_security_groups(), vpc)

    def createVPCInstance(self):
        self.logger.info("Creating new VPC instance")
        vpc = self.vpc.create_vpc(self.CIDR)
        self.addTags(vpc)
        
        subnet = self.getSubnetForVPC(vpc)
        if subnet is None:
            subnet = self.vpc.create_subnet(vpc.id, self.CIDR)
        self.addTags(subnet)
        
        networkACL = self.getNetworkACLForVPC(vpc)
        if networkACL is None:
            networkACL = self.vpc.create_network_acl(vpc.id)
        
        self.addTags(networkACL)
        self.vpc.associate_network_acl(networkACL.id, subnet.id)
        
        igw = None
        for gateway in self.vpc.get_all_internet_gateways():
            if len(gateway.attachments) == 0:
                igw = gateway
                break
        if igw is None:
            igw = self.vpc.create_internet_gateway()
        
        self.addTags(igw)
        self.vpc.attach_internet_gateway(igw.id, vpc.id)
        
        routeTable = self.getRouteTableForVPC(vpc)
        if routeTable is None:
            routeTable = self.vpc.create_route_table(vpc.id)

        self.addTags(routeTable)
        self.vpc.create_route(routeTable.id, "0.0.0.0/0", gateway_id=igw.id)
        self.vpc.associate_route_table(routeTable.id, subnet.id)
        
        return vpc
    
    def createInstance(self):
        interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=self.getSubnetForVPC(self.getVPCInstance()).id,
                                                                            groups=self.getSecurityGroupForVPC(self.getVPCInstance()).id,
                                                                            associate_public_ip_address=True)
        interfaces = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)
###
## Updating Security Groups
###    

    # Thanks to https://gist.github.com/steder/1498451 for the following code
    def modify_sg(self, group, rule, authorize=False, revoke=False):
        src_group = None
        if rule.src_group_name:
            src_group = self.ec2.get_all_security_groups([rule.src_group_name,])[0]

        if authorize and not revoke:
            group.authorize(ip_protocol=rule.ip_protocol,
                            from_port=rule.from_port,
                            to_port=rule.to_port,
                            cidr_ip=rule.cidr_ip,
                            src_group=src_group)
        elif not authorize and revoke:
            group.revoke(ip_protocol=rule.ip_protocol,
                         from_port=rule.from_port,
                         to_port=rule.to_port,
                         cidr_ip=rule.cidr_ip,
                         src_group=src_group)


    def authorizeGroupRule(self, group, rule):
        """Authorize `rule` on `group`."""
        return self.modify_sg(group, rule, authorize=True)


    def revokeGroupRule(self, group, rule):
        """Revoke `rule` on `group`."""
        return self.modify_sg(group, rule, revoke=True)


    def update_security_group(self, group, expected_rules):
        current_rules = []
        for rule in group.rules:
            if not rule.grants[0].cidr_ip:
                current_rule = SecurityGroupRule(rule.ip_protocol,
                                  rule.from_port,
                                  rule.to_port,
                                  "0.0.0.0/0",
                                  rule.grants[0].name)
            else:
                current_rule = SecurityGroupRule(rule.ip_protocol,
                                  rule.from_port,
                                  rule.to_port,
                                  rule.grants[0].cidr_ip,
                                  None)

            if current_rule not in expected_rules:
                self.revokeGroupRule(group, current_rule)
            else:
                current_rules.append(current_rule)

        for rule in expected_rules:
            if rule not in current_rules:
                self.authorizeGroupRule(group, rule)
    
    def updateSecurityGroupForVPC(self, vpc):
        secGroup = self.getSecurityGroupForVPC(vpc)
        self.addTags(secGroup)
        
        if secGroup is not None:
            rules = [
                SecurityGroupRule('-1', None, None, self.hostIP() + "/32", None)
            ]
        
            self.update_security_group(secGroup, rules)
    
###
## Fetching Instances
###
    def getSecurityGroupFromInstance(self, instance):
        attributes = self.ec2.get_instance_attribute(instances[0].id, "groupSet")
        securityGroupId = attributes.get("groupSet")[0].id
        retval = None
        for securityGroup in self.ec2.get_all_security_groups():
            if securityGroup.id == securityGroupId:
                retval = securityGroup
                break
        return retval
    
    def getVPCInstance(self):
        if self.vpcInstance is None:
            self.vpcInstance = self.findExistingVPCInstance()
            if self.vpcInstance is None:
                self.vpcInstance = self.createVPCInstance()
            self.logger.debug("Using VPC instance: %s" % self.vpcInstance)
            
        return self.vpcInstance
    
    def getEC2Instance(self):
        instance = self.findExistingEC2Instance()
    
        if instance is None:
            # TODO: Create an instance
            pass

        if instance is not None:
            securityGroup = self.getSecurityGroupFromInstance(instance)
            if securityGroup is not None:
                self.updateSecurityGroup(securityGroup)
    
        return instance

###
## Starting Instances
###

    #returns:
    # ec2ImageWait if the image is transitioning between states. The state should be checked again in a couple seconds.
    # ec2ImageReady if the image is running and ready to be used
    # ec2ImageNotRunning if the image needs to be started
    def getInstanceState(self, instance):
        if instance is None:
            return ec2ImageNotFound
        if (instance.state_code == ec2StatePending or instance.state_code == ec2StateShuttingDown or instance.state_code == ec2StateStopping):
            return ec2ImageWait
        if instance.state_code == ec2StateRunning:
            return ec2ImageReady
        return ec2ImageNotFound

    def startInstance(self, instance):
        self.logger.debug("Found EC2 instance: "+str(instance)+", state is "+instance.state)
        waitTime = 0
        didStart = False
        while waitTime < 30:
            status = self.getInstanceState(instance)
            if status == ec2ImageReady:
                break
            elif status == ec2ImageNotRunning and not didStart:
                self.logger.info("Starting instance "+instance.id)
                #self.ec2.start_instances(instance.id)
                didStart = True
            elif status == ec2ImageNotFound:
                break;
            time.sleep(1)
            waitTime = waitTime + 1
        if waitTime == 30:
            self.logger.error("Timed out waiting for instance "+str(instance)+" to start. Current state is "+instance.state)
    
    def startImageAndGetIP(self):
        self.connect()
        instance = self.getEC2Instance()

        if instance is not None:
            startInstance(instance)
            return instance.public_dns_name

        return None