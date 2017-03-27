# SDX with SIDR

## Installation: Vagrant Setup

#### Prerequisite

To get started install these softwares on your ```host``` machine:

1. Install ***Vagrant***, it is a wrapper around virtualization softwares like VirtualBox, VMWare etc.: http://www.vagrantup.com/downloads

2. Install ***VirtualBox***, this would be your VM provider: https://www.virtualbox.org/wiki/Downloads

3. Install ***Git***, it is a distributed version control system: https://git-scm.com/downloads

4. Install X Server and SSH capable terminal
    * For Windows install [Xming](http://sourceforge.net/project/downloading.php?group_id=156984&filename=Xming-6-9-0-31-setup.exe) and [Putty](http://the.earth.li/~sgtatham/putty/latest/x86/putty.exe).
    * For MAC OS install [XQuartz](http://xquartz.macosforge.org/trac/wiki) and Terminal.app (builtin)
    * Linux comes pre-installed with X server and Gnome terminal + SSH (buitlin)   

#### Basics

* Clone this repository from Github and enter its directory.


* Now run the vagrant up command. This will read the Vagrantfile from the current directory and provision the VM accordingly:
```bash
$ vagrant up
```

* Access the VM through ssh - user: vagrant, password: vagrant

* Clone the ```supercharged_sdx``` repository from Github into the VM:
```bash
$ git clone https://github.com/sdn-ixp/supercharged_sdx.git
$ chmod 755 ~/supercharged_sdx/xrs/client.py ~/supercharged_sdx/xrs/route_server.py ~/supercharged_sdx/examples/simple/mininet/sdx_mininext.py
$ mkdir ~/supercharged_sdx/xrs/ribs
```

The provisioning scripts will install all the required software (and their dependencies) to run the SDX demo. Specifically it will install:
* [Ryu](http://osrg.github.io/ryu/)
* [Quagga](http://www.nongnu.org/quagga/)
* [MiniNExT](https://github.com/USC-NSL/miniNExT.git miniNExT/)
* [Exabgp](https://github.com/Exa-Networks/exabgp)


#### Important

* Make sure that the following two directories exist: xctrl/loop_detection/cibs and xctrl/route_server/ribs.

## Examples

There are multiple examples in the examples directory.
