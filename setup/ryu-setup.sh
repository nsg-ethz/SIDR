#!/usr/bin/env bash

RYU_VERSION="v3.30"

cd ~

#  Dependencies for ryu
sudo apt-get install -y python-routes python-dev

sudo pip install eventlet==0.18.4
sudo pip install msgpack-python==0.4.7
sudo pip install oslo.config==3.8.0

#  Ryu install
cd ~
git clone -b $RYU_VERSION git://github.com/osrg/ryu.git
sudo cp ~/supercharged_sdx/refmon/flags.py ~/ryu/ryu/flags.py
cd ryu

# Below should be temporary until ryu's pip-requires file is fixed
sed -i "s/python_version < '2.7'/(python_version != '2.7' and python_version != '3.0')/" tools/pip-requires
sed -i "s/python_version >= '2.7'/(python_version == '2.7' or python_version == '3.0')/" tools/pip-requires

sudo python ./setup.py install
