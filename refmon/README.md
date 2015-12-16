# RefMon - Reference Monitor

The reference monitor (refmon.py) is a ryu module and requires [Ryu](http://osrg.github.io/ryu/) to be installed.

__Install Ryu__

Clone Ryu  

    $ cd ~  
    $ git clone git://github.com/osrg/ryu.git  

Before installing it, replace flags.py with the provided file

    $ cp ~/supercharged_sdx/refmon/flags.py ~/ryu/ryu/flags.py
    $ cd ~/ryu
    $ sudo python ./setup.py install

## Run RefMon

```bash
$ ryu-manager ~/supercharged_sdx/refmon/refmon.py --refmon-config <path of config file>
```

To log all received flow mods to a file just run it like this:

```bash
$ ryu-manager ~/supercharged_sdx/refmon/refmon.py --refmon-config <path of config file> --refmon-flowmodlog <path of log file>
```
