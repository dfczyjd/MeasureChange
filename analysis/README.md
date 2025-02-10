## Repository contents
* data: folder to keep unprocessed database files
  * unzip.py: script to decompress databases
  * merge.py: script to merge two databases together
* server: visualization tool server-side components
  **Valid URLs**:
  * /all: produce a diagram of all changes of types other than *list*, *array* and changes in *presentValue* and *relinquishDefault* properties
  * /array: produce a diagram for a given *array* property
  * /bool: produce a diagram of all changes in *bool* features
  * /diff: display all changes that happened between given timestamps
  * /fast_list: display changes in a list
  * /number: plot all *number* values satisfying a hardcoded criteria on the same plot
* **Scripts:**
  * autocorrelate.py: run periodicity detection algorithm for the given property
  * data_process.py: aggregate collected feature values from separate databases and process it into time series
  * device_ids: map IP addresses of devices to their BACnet IDs
  * files.py: aggregate collected files from separate databases
  * list_scan.py: search for persistent changes in *list* features
  * list_scan2.py: detect changes in *list* features
  * list_series: process *list* features into separate elements
  * process_final_step: needs to be executed to finalize data processing
  * segment.py: pick a segment of collected data based on time
  * series.py: load collected data into .pickle file
  * util.py: auxilliary functions used by multiple scripts
* **Jupiter Notebook files:**
  * Diagrams.ipynb: produces diagrams for the report
  * filtering.ipynb: computes the impact of separate steps of filtering phase
  * quickRevert.ipynb: computes the threshold for frequent quick reverts