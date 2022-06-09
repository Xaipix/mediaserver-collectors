### How To Use ###
- Install and setup Telegraf, InfluxDB, and Grafana to work with eachother. 
- Use the provided mediaserver-collector.conf file.
- Restart Telegraf. 
- Import the dashboard by ID 16423, select your own InfluxDB database after clicking "Import".
- Enjoy!

### Description ###
Collected metrics:
1. Mediaserver summary
    * current time
    * mediaserver hostname
    * mediaserver version
    * mediaserver uptime
    * number of mediaserver restarts
    * OS version of host mediaserver is installed at
2. Memory usage
    * VmSize – size of available for use memory
    * VmRss –  size of used memory
3. Tasks usage
    * mediasvc – customer service streams
    * mediumsvc – streams capturing cameras
    * websvc – API\Cpanel
    * scheduler\vacuum\cluster – auxiliary
4. CPU usage
5. Sockets connections (incoming/outgoing)
    * RxQueue – number of unreceived data 
    * TxQueue – send queue
    * Sockets – total open sockets
    * Established – number of established connections
    * Close Wait – semi-closed connections
    * Slow Connection – slow connections, delivery takes more than 100 milliseconds
    

### Telegraf config file ###
Сreate a new file under /etc/telegraf/telegraf.d/mediaserver-collector.conf and add the next:
```
[[inputs.exec]]
commands = [
     "/etc/telegraf/telegraf.d/inputs/mediaserver.py io",
     "/etc/telegraf/telegraf.d/inputs/mediaserver.py memory",
     "/etc/telegraf/telegraf.d/inputs/mediaserver.py proc",
     "/etc/telegraf/telegraf.d/inputs/mediaserver.py tasks",
     "/etc/telegraf/telegraf.d/inputs/mediaserver.py sockets",
   ]
timeout = "10s"
interval = "60s"
data_format = "influx"
```
