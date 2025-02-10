## Minimal working example
This directory holds files to set up the environment for and run a minimal working example of the probing script.
### Enviroment description
The MWE environment consists of two virtual devices located within the same network. Both devices contain one object of each of *Device*, *Analog Value* and *Binary Value* object types. All objects initially have their *Description* property set to "<object_type> initial description" and after a delay of 20 to 30 seconds from the startup, chosen at random, one of the objects changes the property value to "Object description was updated at <update_timestamp>". The object to have the change would be *Analog Value* object for one device and *Binary Value* object for the other
### Configuration
Required steps to configure the environment:
1. Replace the IP address at line 3 of BACpypes1.ini with IP address to be assigned to the first device, in CIDR notation.
2. Replace the IP address at line 3 of BACpypes2.ini with IP address to be assigned to the second device, in CIDR notation.
3. Replace the IP addresses in the variable ``ip_whitelist`` at lines 8-9 of probe.py with the device addresses from steps 1-2.
4. Replace the IP address in the variable ``probe_ip`` at line 6 of probe.py with IP address to be assigned to the probing device.  

Optional configuration steps:
1. Set the desired value in seconds of the delay between consequent device probing within one cycle in variable ``device_delay`` at line 11 of probe.py
2. Set the desired value in seconds of the delay between probing cycles in variable ``cycle_delay`` at line 12 of probe.py

### Running the script
The probing script and two devices should run in parallel, with devices started before the script in any order. The commands to start the components are:
* First device: ``python3 device.py --ini BACpypes1.ini``
* Second device: ``python3 device.py --ini BACpypes2.ini``
* Probing script: ``python3 probe.py``

A shell script run.sh is present in the repository to automatically start all three components in correct order.