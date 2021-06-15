# pymon

System monitor

It's written for my WD MyBook Live Duo NAS monitoring. 

This device is based on Power CPU (32-bit). It has very python 2.5 only by default and python 3.7 may be installed bu ipkg. 
So, it doesn't have any hardware monitoring software, excluding smartctl.
It seems, that it is impossible to install something like zabbix (at least zabbix-agent), prometheus+grafana, etc. That's why I used to write something to monitor its health.
