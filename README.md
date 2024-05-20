# Measuring change in ICS

## Repository contents
* mapping: mappings of object properties to change types
  * aggregate.py: script to identify unmapped change types
* probe: probing script with auxilliary files
  * probe.py: current version of the probing script
     Configuration  
    * probe_ip: IP of the probe within the BAS network
    * ip_whitelist: list of IPs to probe
    * property_delay: delay between requests to different object properties within the device
    * device_delay: delay between requests to different devices within the cycle, in seconds
    * discovery_delay: delay between device discovery requests, in seconds
    * db_file: file containing database to write collected data to
    * output_filename: file to write collected data to, if database is inaccessible
    * log_level: logging level, one of 'debug', 'info', 'warning', 'error'
  * probe_shell.py: a REPL shell to interactively query object properties
* mwe: minimal working example of the probing script
  * See mwe/README.md for more information