# Measuring change in ICS

## Repository contents
* mapping: mappings of object properties to change types
  * aggregate.py: script to identify unmapped change types
* probe: probing script with auxilliary files
  * probe.py: current version of the probing script
     Configuration  
    * probe_ip: IP of the probe within the BAS network
    * ip_whitelist: list of IPs to probe
    * device_delay: delay between requests to different devices within the cycle, in seconds
    * cycle_delay: delay between different cycles, in seconds
  * probe_shell.py: a REPL shell to interactively query object properties
* mwe: minimal working example of the probing script
  * See mwe/README.md for more information