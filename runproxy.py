#!/usr/bin/python

from AWSProxy import AWSProxy
import logging

logger = logging.getLogger("AWSProxy.AWSProxy")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

proxy = AWSProxy.AWSProxy()
proxy.connect()
vpc = proxy.getVPCInstance()
proxy.updateSecurityGroupForVPC(vpc)
