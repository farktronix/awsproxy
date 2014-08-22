AWSProxy
========

On-demand AWS proxy

This script initializes an Amazon EC2 instance running as a proxy, then sets up a SSH tunnel to the proxy.

Because some clients can't easily change their proxy settings, this also keeps a Squid proxy running and dynamically changes it between being a transparent proxy and forwarding traffic to the EC2 instance, depending on whether the EC2 instance is active.

The EC2 instance is configured to automatically shut down when less than 64KB of traffic has been transferred in the last 15 minutes.

Here's an ASCII diagram of the setup:

```
+--------+      +--------+      +--------+               
|        |      |        |      |        |               
| Client +----->+AWSProxy+----->+   EC2  |-----> Internet
|        |      |        |      |        |               
+--------+      +----+---+      +--------+               
                     |                                   
                     |
                    \ /
                  Internet                               
```

Setup
-----
1. Install [Boto](https://boto.readthedocs.org/en/latest/getting_started.html#installing-boto)
2. Install [Squid](http://www.squid-cache.org/Download/)
3. Configure your AWS credentials in ~/.aws/credentials
