## Examples

### Tests 

The examples with the prefix *test_* are here to test SIDR without the dataplane. The BGP routes can be specified in a file and are fed into the route server.

* test_basic - testing basic functionality of SIDR: loop detection, reaction to topology changes

* test_forward - testing of the message processing and propagation, and reaction to topology changes

* test_loops1 - tests how SIDR handles multiple overlapping loops

* test_loops2 - tests how SIDR handles multiple overlapping loops

#### Usage

To change BGP routes, just modify the files in the folder example/<test_name>/bgp/<sdx_id>.log. The file has the following format:

<time>|<type>|<sender IP>|<sender ASN>|<receiver IP>|<receiver ASN>|<AS Path>|<prefix>

This triggers a route advertisement from the border router of 200 to route server of SDX1 for 100.0.0.0/24 after 60 seconds:
60|announce|172.1.0.2|200|172.1.255.254|65000|200,500,400,800,600|100.0.0.0/24

This triggers the border router of 200 to withdraw the route for 100.0.0.0/24 after 90 seconds:
90|withdraw|172.1.0.2|200|172.1.255.254|65000||100.0.0.0/24

### Examples

These are full SIDR-SDX samples.

* simple - standard SDX setup. Consists of only one SDX, hence SIDR is not necessary.

* multi_sdx - example with two SDXes.