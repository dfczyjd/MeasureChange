# Measuring change in ICS

## Repository contents
* mapping: mappings of object properties to change types
  * aggregate.py: script to identify unmapped change types
* probe: probing script with auxilliary files
  * probe.py: current version of the probing script
  * probe_shell.py: a REPL shell to interactively query object properties and files. Target IP address is specified in variable `target`
    Commands:
    * `read object_type object_id properties` - read property or properties (separated by space) from a given object. Uses readProperty service if only one property is provided and readPropertyMultiple otherwise.
    * `file file_id out_file [chunk_size]` - read file from the device and write the contents to `out_file`. Optional parameter `chunk_size` allows to configure size of a chunk requested in a single request (default 1 MB)
    * `target [ip]` - set target device IP address to `ip`. With no argument given, displays current target
  * patch.py: patched versions of several BAC0 methods
  * config.py: configuration variables
    * probe_ip: IP of the probe within the BAS network
    * ip_whitelist: list of IPs to probe
    * property_delay: delay between requests to different object properties within the device
    * device_delay: delay between requests to different devices within the cycle, in seconds
    * discovery_delay: delay between device discovery requests, in seconds
    * db_file: file containing database to write collected data to
    * output_filename: file to write collected data to, if database is inaccessible
    * log_level: logging level, one of 'debug', 'info', 'warning', 'error'
    * property_batch_size: maximum number of properties to query in a single readMultiple request
    * stream_batch_size: maximum number of bytes to read in a single ReadFile request to a File object with StreamAccess file access method
    * record_batch_size: maximum number of records to read in a single ReadFile request to a File object with RecordAccess file access method
  * database.sqlite3: empty database containing all necessary tables
  * file_reader.py: script to read files from devices (requires config.py and data from database specified in it)
* mwe: minimal working example of the probing script
  * See mwe/README.md for more information