## Table of contents
[[_TOC_]]

## Introduction

The 5GNSS (5G Network Slice Simulator) is a software to simulate an Edge Environment to execute Network Slices and SFCs 
(Service Function Chain), also known as NS (Network Services). We use SimPy, a process-based discrete-event simulation 
framework based on standard Python, as our simulation engine. Some critical aspects of our simulation environment are:

* The word "time" in this document is related to the "simulation time" and not the real-time. 
** The only situation where time means reaA Network Slice (slice) is a set of resources (network and computational) focussed in providing a set of services wil time is the time for execute the placement
* The CPU is configured in terms of IPT (Instruction Per Time Simulation). 
* In our simulation, the default time is milliseconds, which means that a node with 2000 CPU will process 20000 each ms.
 
Some limitations:

* The SFC must contain only one VNF of each type. For example. the VNF_1 can have (V_1, V_5, V_50) but never (V_1, V_1, V_5)
* There is at least one node that can host a VNF_Instance of any VNF

The image below represents the environment that we are simulating. The user requests the creation of an SFC. 
Each SFC is composed of multiples VNF that atotal_timere mapped into VNF_Instances. Some data source generates the packets and 
ingress in the first VNF of the SFC. After the processing time and transfer time to the packet arrive in the next VNF_Instance.
This process repeats until the packet be processed by the last VNF_instance and leaves the simulation.

![mapping](doc/img/diagrams-mapping2.png "Mapping")

## How to Install

```diff
- Requires Python +3.6*
```

Clone the project in your local folder:

```bash
git clone set-url origin git@https://gitlab2.battisti.com.br:8929/root/nss.git
```


Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

## Execute the Simulation

1. Configure the *specs files* 
2. Configure the simulation parameter files
3. Run: 
```bash
/bin/python3 path_to_file/main.py  --specs=./Specs/light_cpu_vnf_specs.json 
```

```diff
+ After the execution of the simulation, run the Analysis notebook to analyze the data.
```

There are some parameters available to run the simulation, they are:

* --debug: Print the debug option
* --save: Save the generated entities in a json
* --load: Load the saved entities from a json file and convert it in environment entities
* --list: Print all the entities generated
* --show: Show the first instance of each entity generated
* --specs: The specs file that will guide the simulation for generating the entities objects --specs ./specs.json.')
* --path_result_files: Path where the result files will be saved
* --simulation_parameters: file with the simulation parameters
* --random_seed:  The random seed used by Python to generate the same random values during sequential executions
* --only_placement: Execute only the placement and stops before starting the simulation "DEPRECATED"
* --user_mobility_file: Path to file with user mobility pattern

## Environmental Variables

### Debug

For print all the debug messages you need to export an environment variable named *nss_debug*. If you are using Linux 
execute the command below **before** run the simulation.

```bash
export NSS_DEBUG=1
```

For stop printing the debug messages just export again the debug variable with value 0.

```bash
export NSS_DEBUG=0
```

Define where the error message will be saved.

```bash
export NSS_ERROR_PATH="${path_program}/Experiment/Results/Placement/Error"
```

#### Placement Plan Images

The placement generate a placement plan. The images are saved inside the results folder for each round.  If you want to 
disable the image generation, define this variable as 0 (if activate it will consume a lot of time, use only for 
debug of for getting the image to your paper.

```bash
export NSS_SAVE_IMAGE_PLACEMENT=0
```

### Error Path

If the simulation crash during the experiment the files can be saved in the folder specified in the variable 
NSS_ERROR_PATH

```bash
export NSS_ERROR_PATH=path
```

### Restrict link bandwidth

Define if the placement algorithm will restrict the use of a link based on the previous VNF_Instances that was mapped
to use the link. The placement method must use this variable. Probably it was better if it was a placement variable 
parameter. For our purpose it is sufficient.

```bash
export NSS_ERROR_PATH=path
```

### Packets Flow

The packet flow can be generated using dynamic process (linear and poisson) or, it can define in a file. 
The environment variable that define where the file is located is:

```bash
export PATH_PACKET_FLOW_FILE=path
```

The csv file must have this structure:

```csv
user;sfc;time;packet_size
u_1;s_0;0;51
u_1;s_0;50;46
u_1;s_0;50;60
u_1;s_0;50;70
```

* **user**: User id
* **sfc**: SFC id
* **time**: The packet generation time is related to the simulation time when the SFC Request is placed. 
The value define how long the simulation must wait regarding the last packet generated. 
For example, if the SFC Request was placed in the simulation time 150 and the time of the first packet is 10, it means 
that in the simulation time the packet will be generated in the 160, if the time of the second packet is 20, 
thus, the simulation time when the packet will be generated is 180.  
* **packet_size**: define the size of the packet (workload)

## Git Change URL

Chage the remote URL

```bash
git clone set-url origin git@https://gitlab2.battisti.com.br:8929/root/nss.git
```

## How to run the Simulation

The simulation in a Python script, we recommend the use of the Python Virtual Environment *virtualenv*

```bash
pip install virtualenv
```    

Access the folder nss and create the virtual environemnt 

```bash
python3 -m venv venv
```

### Shell Script

The *run_experiment.sh* is already configured to execute the python script using the Python packages 
installed inside the virtual environment. 

If you will run the simulation without the virtualenv you need to remove the line 

```bash
source ./venv/bin/activate
```

from the begging of the .sh file

The variable inside the run_experiment.sh that must be configured:

* exp_name: The folder inside the "Experiment" where the experiment config files are stored
* exp_description: The description of the experiment
* algs: The name of the config files with the simulation configuration that must be executed 
* arr: The environment config file
* k:  The number of the first experiment executed
* exp_num: The number of the last experiment executed

### Experiment Plan

To execute an experiment, we suggest following these steps:

1. Create the file to define the edge environment entities;
2. Create the files to configure the simulation;
3. Configure the run_experiment.sh for each variant of the experiment created;
4. Execute the run_experiment.sh;

## Project Folder Structure 

This project can be used as a framework for running new placement and scaling algorithms for SFCs and Network Slices. The folder structure is straightforward and can be modified for further research.

    .
    ├──  Edge_Entities              # The edge entities file Python Class
    ├──── Link.py                   # Class for the Link entity
    ├──── Node.py                   # Class for link Node entity
    ├──── SFC.py                    # Class for the SFC entity
    ├──── User.py                   # Class for the User entity
    ├──── VNF_Instance.py           # Class for the VNF_Instance entity
    ├──── VNF.py                    # Class for the VNF_Instance entity
    ├──  Experiment                 # Folder store the experiment files
    ├──── Results                   # Folder for storing the experiment result log files
    ├──── Specs                     # Folder for storing each experiment type specification files
    ├──  Placement                  # Folder for the placement strategies implemented (you will work here)
    ├──── Greedy.py                 # Greedy SFC Placement 
    ├──── Smart.py                  # Our heuristic for placement implementation
    ├──── ...
    ├──  Scaling                    # Folder for the scaling strategies implemented (you will work here too)    
    ├──── Smart.py                  # Our heuristic for scaling implementation
    ├──  Simulation_Entities        # Folder with the Python class for the entities generated during the simulation process
    ├──── Packet.py
    ├──── SFC_Instance.py
    ├──── SFC_Request.py
    ├──── VNF_Instance.py
    ├── Edge_Environment.py         # Generate the entities based on the specifications 
    ├── main.py                     # The main file of the simulation
    ├── Simulation_SDN_Controller.py # A SDN_Controller toy, only to calculate the next VNF_Instance of packet
    ├── Simulation_Monitor.py       # Class for monitoring the VNF_Instances, used by all scaling implementations
    ├── Simulation_Data.py          # Responsible for logging all the event generated during the simulation
    ├── run_experiment.sh           # Script for running the experiment multiple times for multiples environments
    └── Simulation.py               # Is the simulation engine using SimPy

## Network Slice 

A Network Slice (slice) is a set of resources (network and computational) focussed in providing a set of services with a determined QoS. Multiple slices can be running in the same infrastructure. The resources are isolated among them. For each slice the the weight of each parameter of the objective function in the placement algorithm can be different.

Each SFC Type is associated with a specific slice.

The slice must be created before some SFC_Instance and VNF_Instance be executed.

The slice is pre-configured by the infrastructure owner

## Simulation Parameters Configuration

It is required a JSON file with the parameters listed in the table below to configure the simulation. All of them are 
required. There is no default file, you must create a simulation config file. This files is responsible for defining
how the simulation will be executed. 

```json
{
  "simulation": {
    "packet_generation"                     : 1,
    "total_time"                            : 5000,
    "num_rounds"                            : 1,
    "random_seed"                           : 200,
    "time_window"                           : 500,
    "share_sfc_instance"                    : 0,
    "compute_loopback_time"                 : 1,
    "sfc_instance_monitor_interval"         : 100,
    "sfc_instance_monitor_window_size"      : 101,
    "max_sla_violation_sfc_instance_shared" : 2,
    "order_sfc_request_by_similarity"       : 1,
    "log_link_events"                       : 1,
    "log_vnf_instance_events"               : 1
  },

  "placement": {
    "heuristic" : "SmartPlacement"
  },

  "scaling": {
    "heuristic"        : "Smart_Scaling",
    "parameters": {
        "monitor_interval" : 100,
        "energy_weight"    : 0.33,
        "memory_weight"    : 0.33,
        "latency_weight"   : 0.34
    }
  }
}
```

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>  
        <tr>
            <td>simulation.packet_generation</td>
            <td>
                Define if packets will be generated during the simulation, if 0 than only placement plan will be executed.
            </td>
            <td>bool (0/1)</td>
        </tr>
        <tr>
            <td>simulation.time_limit_to_packet_generation</td>
            <td>
                Define the time limit for the packet generation. If this parameter was not defined thus the limit 
will be the total_time. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.execute_user_mobility</td>
            <td>
                Define if the file with the mobility pattern will be used to change the user location during the 
simulation or not. If 0, even if the pattern mobility file is informed the user will not move
            </td>
            <td>bool (0/1)</td>
        </tr>
        <tr>
            <td>simulation.total_time</td>
            <td>
                The total time that the simulation will be executed. It's not the time that the simulation will run, 
but the time that it will pass in the simulation. The time for executing the simulation is greater than the simulation 
time and will vary in function of the computational resources you had to execute the simulation.            
            </td>
            <td>Simulation Time (Simpy) (we consider this value as milliseconds)</td>
        </tr>
        <tr>
            <td>simulation.num_rounds</td>
            <td>
How many times the same simulation will be executed. As the simulation had random components, 
like the time between two consecutive packets be generated, or, the time interval between two SFCs requests, 
its important that the same simulation be executed multiples times to overcome this bias.
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.random_seed</td>
            <td>
                The Python Random seed that will be used to generate the entities. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.time_window</td>
            <td>
                The placement plan will be execute each time_window ms. For example, if the value is 500, the placement 
                plan will be executed at the time 500, 1000, 1500 ... until the time of the simulation. If the value
                were defined as 0, the placement plan will be executed only once, at the simulation time = 0 and all the
                SFC Requests will be placed in that time. The arrival time of all the SFC Requests also will be update 
                to 0.
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>simulation.share_sfc_instance</td>
            <td>
                If 1 the SFC Instance can be shared by multiple SFC Requests, and it is not sharable if 0.
            </td>
            <td>bool</td>
        </tr>
        <tr>
            <td>simulation.compute_loopback_time</td>
            <td>
                If 1 the time for the loopback link will be computed, if 0 the time will not be counted. The loopback 
link is used when two consecutive VNFs os a SFC are hosted in the same edge node.
            </td>
            <td>bool</td>
        </tr>
        <tr>
            <td>simulation.sfc_instance_monitor_interval</td>
            <td>
                Defines the interval for running the SFC Instance Monitor function 
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>simulation.sfc_instance_monitor_window_size</td>
            <td>
                Defines the interval used to select packets that will be available for finding SLA Violation.
If this value is defined as 100, for example, all the packets generated in each 100ms interval will be available. This 
monitor is global, and all the SFC Instances will be validated in the same interval.
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>simulation.max_sla_violation_sfc_instance_shared</td>
            <td>
                Define the limit of packets that can violate the SLA (max latency) without blocking the SFC Instance 
for being shared with new SFC Requests. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.order_sfc_request_by_similarity</td>
            <td>
                Defines if the SFC Similarity will be used or not before the placement phase. The default value is none.
The values for this variable 
                can be:
                <ul>
                  <li><strong>asc:</strong> The SFC Request in the same time window will be sorted from the most similar to the least similar.</li>
                  <li><strong>desc:</strong> The SFC Request in the same time window will be sorted from the least similar to the most similar.</li>
                  <li><strong>none:</strong> The SFC Request in the same time window will be placed in the arrival order|</li>
                </ul>
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.log_link_events</td>
            <td>
                Log in the CSV file the events in the link process (if activate consume a lot of resource)
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>simulation.log_vnf_instance_events</td>
            <td>
                Log in the CSV file the events in the VNF Instance process (if activate consume a lot of resource)
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>placement.heuristic</td>
            <td>
                Is the parameter that defines which heuristic that the simulation will use. The file and the class name must be the same. For example, the SmartPlacex.py  must have the class SmartPlacex and this string must be used in this configuration file.
            </td>
            <td>Heuristic Class Name</td>
        </tr>
        <tr>
            <td>placement.parameters</td>
            <td>
                It is a JSON object that can hold many parameters that are required by the constructor of the placement object. Each attribute must have the same name as the variable in the Python file constructor.
            </td>
        </tr>        
        <tr>
            <td>scaling.heuristic</td>
            <td>
                Is the parameter that defines which heuristic that the monitor will use for scaling the instances. The file and the class name must be the same. For example, the SmartScaling.py  must have the class SmartScaling and this string must be used in this configuration file.
            </td>
            <td>Scaling Class Name</td>
        </tr>
        <tr>
            <td>scaling.parameters.monitor_interval</td>
            <td>
                The time interval between monitoring the VNF_Instance 
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>scaling.parameters</td>
            <td>
                It is a json object that can hold many parameters that are required by the constructor of the scaling object. Each attribute must have the same name of the variable in the constructor.
            </td>
            <td>JSON</td>            
        </tr>        
    </tbody>
</table>

### SFC Instance Share 

For the simulation share an SFC Instance with multiples SFC Requests some facts must occour. 

1. The *share_sfc_instance* parameter in the simulation configuration file **must** be defined as 1.
2. The SFC Request must share the same ingress and egress node.

This implementations must be defined in the placement algorithm. The placement algorithm can define another rules for 
sharing or not the SFC Instance, for example, only allow a max number of request in the same SFC Instance, or, a 
time interval between new SFC Instance sharing.

In the above example all the SFC Instances si_1 and s2_6 were created from process packets for the SFC type s_0, 
but only the SFC Requests r_5 and r_7 sharing the same SFC Instance si_6 because they have the same ingress and egress node.

```
SFC Instances
+------+-----+---------+-----------+---------------------+--------+---------+---------+--------+------------------------------------------------------------+
| Name | SFC | Timeout | Net Slice | Accept New Requests | Active | SFC Req | Ingress | Egress |                           Links                            |
+------+-----+---------+-----------+---------------------+--------+---------+---------+--------+------------------------------------------------------------+
| si_1 | s_0 |  7510   |     1     |          1          |   1    |   r_0   |   n_0   |  n_4   | {'ingress': 'l_0_3_2', 'v_3': 'l_3_1_0', 'v_0': 'l_1_4_0'} |
+------+-----+---------+-----------+---------------------+--------+---------+---------+--------+------------------------------------------------------------+
| si_6 | s_0 |  9967   |     1     |          0          |   1    |   r_5   |   n_4   |  n_1   |    {'ingress': 'l_4_0_0', 'v_3': 'l_0_1_1', 'v_0': ''}     |
|      |     |         |           |                     |        |   r_7   |         |        |                                                            |
+------+-----+---------+-----------+---------------------+--------+---------+---------+--------+------------------------------------------------------------+

SFC Requests
+------+------+-----+----------+--------------+-------------+--------------+-------------+----------+--------+-------------------------+
| Name | User | SFC | Priority | Arrival Time | Data Source | Ingress Node | Egress Node | Duration | Placed | Associated SFC Instance |
+------+------+-----+----------+--------------+-------------+--------------+-------------+----------+--------+-------------------------+
| r_0  | u_1  | s_0 |    2     |      10      |    src_0    |     n_0      |     n_4     |   2000   |   1    |          si_1           |
+------+------+-----+----------+--------------+-------------+--------------+-------------+----------+--------+-------------------------+
| r_5  | u_9  | s_0 |    0     |     931      |    src_0    |     n_4      |     n_1     |   2000   |   1    |          si_6           |
+------+------+-----+----------+--------------+-------------+--------------+-------------+----------+--------+-------------------------+
| r_7  | u_2  | s_0 |    0     |     2677     |    src_0    |     n_4      |     n_1     |   2000   |   1    |          si_6           |
+------+------+-----+----------+--------------+-------------+--------------+-------------+----------+--------+-------------------------+
```

## Events Collected

The Simulation generate logs for many events, for example: When a VNF Instance is created, or when the placement 
algorithm is executed, or even when each packet is created. Each type of entity generate one or multiple log files. 
Each log file store multiples events for the entity monitored.  

All the log files of an execution is stored inside the "Round_n" folder. Some of them are:

```
links.csv             placement.csv              sfc_instance_vnf_mapping.csv  user_mobility.csv         vnf_instance_resources.csv
packets.csv           sfc_instance.csv           sfc_request.csv               vnf_instance.csv          vnf_instances_entities.csv
packets_entities.csv  sfc_instance_entities.csv  time_window.csv               vnf_instance_packets.csv
```

The event stored in each files are:

<table>
    <thead>
        <tr>
            <th scope="col">Event</th>
            <th scope="col">Entity</th>
            <th scope="col">Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>EVENT_USER_MOVED</td>
            <td>User</td>            
            <td>The time when the user moved from one node to another</td>
        </tr>
        <tr>
            <td>EVENT_TIME_WINDOW_STARTED</td>
            <td>Simulation</td>            
            <td>The time when the time window execute</td>
        </tr>
        <tr>
            <td>EVENT_TIME_WINDOW_PROCESSED</td>
            <td>Simulation</td>            
            <td>The time when the time window finish</td>
        </tr>
        <tr>
            <td>EVENT_PLACEMENT_STARTED</td>
            <td>Simulation</td>            
            <td>The time when the placement starts</td>
        </tr>
        <tr>
            <td>PLACEMENT_PROCESSED</td>
            <td>Simulation</td>            
            <td>The time when the placement finish</td>
        </tr>
        <tr>
            <td>PACKET_CREATED</td>
            <td>Packet</td>            
            <td>The time when the packet was created by the SFC Request</td>
        </tr>
        <tr>
            <td>PACKET_PROCESSED</td>
            <td>Packet</td>            
            <td>The time when the packet was processed by the last VNF</td>
        </tr>
        <tr>
            <td>EVENT_PACKET_ORPHAN</td>
            <td>Packet</td>            
            <td>The time when the packet became orphan. If the next VNF Instance that the packet must go was alredy removed
thus the packet became orphan</td>
        </tr>
        <tr>
            <td>EVENT_PACKET_DROPPED_VNF_INSTANCE_QUEUE</td>
            <td>Packet</td>            
            <td>The time when the packet is dropped because the VNF Queue is full</td>
        </tr>
        <tr>
            <td>VNF_PACKET_ARRIVED</td>
            <td>VNF</td>            
            <td>The time when the packet enter in the VNF_Instance Queue to be processed</td>
        </tr>
        <tr>
            <td>VNF_PACKET_PROCESS_STARTED</td>
            <td>VNF</td>            
            <td>The time when the packet get out the VNF_Instance Queue and start to be processed</td>
        </tr>
        <tr>
            <td>VNF_PACKET_PROCESSED</td>
            <td>VNF</td>            
            <td>The time when the packet is processed by the VNF_Instance</td>
        </tr>
        <tr>
            <td>VNF_REMOTE_DATA_RECEIVED</td>
            <td>VNF</td>            
            <td>The time spent by the VNF_Instance to collect a remote data</td>
        </tr>
        <tr>
            <td>EVENT_LINK_ARRIVED</td>
            <td>Link</td>            
            <td>The time when the packet entre in the Link's Queue</td>
        </tr>
        <tr>
            <td>LINK_PACKET_STARTED</td>
            <td>Link</td>            
            <td>The time when the packet get out the Link's Queue and start to be sending</td>
        </tr>
        <tr>
            <td>LINK_PACKET_SENT</td>
            <td>Link</td>            
            <td>The time when the link finish the packet process</td>
        </tr>
        <tr>
            <td>INSTANCE_CREATED</td>
            <td>VNF_Instance</td>            
            <td>```diff
                - YET NOT IMPLEMENTED
                ```
            </td>
        </tr>
        <tr>
            <td>CPU_INCREASE_AVAILABILITY</td>
            <td>VNF_Instance</td>            
            <td>The scaling increases the CPU availability in the VNF_Instance.</td>
        </tr>        
        <tr>
            <td>CPU_DECREASE_AVAILABILITY</td>
            <td>VNF_Instance</td>            
            <td>The scaling decreases the CPU availability in the VNF_Instance.</td>
        </tr>        
        <tr>
            <td>MEM_INCREASE_AVAILABILITY</td>
            <td>VNF_Instance</td>            
            <td>The scaling increases the Memory availability in the VNF_Instance.</td>
        </tr>        
        <tr>
            <td>MEM_DECREASE_AVAILABILITY</td>
            <td>VNF_Instance</td>            
            <td>The scaling decreases the CPU availability in the VNF_Instance.</td>
        </tr>
        <tr>
            <td>CPU_INCREASE_USAGE</td>
            <td>VNF_Instance</td>            
            <td>The time when the VNF_Instance has it's CPU Usage increased.</td>
        </tr>        
        <tr>
            <td>CPU_DECREASE_USAGE</td>
            <td>VNF_Instance</td>            
            <td>The time when the VNF_Instance has it's CPU Usage decreased.</td>
        </tr>        
        <tr>
            <td>MEM_INCREASE_USAGE</td>
            <td>VNF_Instance</td>            
            <td>The time when the VNF_Instance has it's Mem Usage increased.</td>
        </tr>        
        <tr>
            <td>MEM_DECREASE_USAGE</td>
            <td>VNF_Instance</td>            
            <td>The time when the VNF_Instance have it's Mem Usage decreased.</td>
        </tr>        
        <tr>
            <td>DISK_ACCESS</td>
            <td>VNF_Instance</td>            
            <td>The time when the VNF_Instance have to use the disk because of memory lack.</td>
        </tr>        
        <tr>
            <td>SCALING_UP</td>
            <td>Scaling</td>            
            <td>The scaling up was performed.</td>
        </tr>        
        <tr>
            <td>SCALING_DOWN</td>
            <td>Scaling</td>            
            <td>The scaling down was performed.</td>
        </tr>
    </tbody>
</table>    

## File Result Structure

After the execution of the simulation, you will get a file structure with all the information about the entities and events generated during the simulation. 
The structure is depicted below.

Env_0  Env_1  Images  Provenance

    .
    ├── Experiment                # Where files used in the experiment are stored
    ├──── Results                 # Where the result files by default are stored
    ├────── Exp_Name              # The name of the experiment 
    ├──────── Env_0               # The results for each enviroment
    ├────────── "Env_Name"        # The name of the variable that you are testing
    ├──────────── "Each Variation" # Each variation of the variable
    ├────────────── Entities      # The edge entitites used in this simulation
    ├──────────────── Exp_Round_0  
    ├────────────────── Images        # Where the placement plan images where stored
    ├────────────────── Log Files     # All the log files
    └────────────── Exp_Round_n

## Simulation Entities Specs File

The specs "Specifications" file that will guide the simulation for generating the entities objects is defined in the 
parameter  --specs ./specs.json. This file is a JSON composed of multiples objects. We will describe each attribute 
of this object
 
Another required file for the simulation is the entity specification file. This file must have the possible values that
each simulation entity attribute can have. We will discuss each attribute in a further section, but the general fields 
of this file are:

### Entities Number 

Will define how many elements of each entity will be generated. In the example above, we will create a simulation with 
20 edge nodes, 10 VNF Types, 10 SFCs and 4 users.

```json
{
  "entities_number": {
    "nodes": 20,
    "vnfs": 10,
    "sfcs": 10,
    "users": 4
  }
}
```

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
        </tr>
    </thead>
    <tbody>   
        <tr>
            <td>entities_number.nodes</td>
            <td>
                The number of Nodes that will be generated
            </td>
        </tr>
        <tr>
            <td>entities_number.users</td>
            <td>
                The number of Users that will be generated
            </td>
        </tr>
        <tr>
            <td>entities_number.vnfs</td>
            <td>
                The number of VNFs that will be generated
            </td>
        </tr>        
        <tr>
            <td>entities_number.sfcs</td>
            <td>
                The number of SFCs will be generated
            </td>
        </tr>
    </tbody>
</table>

### VNF

Define the aspects of each VNF in the simulation. In real world a VNF can be a firewall, DNS, Cache, CDN, LDAP, 
and many other things. This parameters can be used to defined how each VNF in the simulation will be. 
The attributes available for each VNF Type are:

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>cpu</td>
            <td>
                Is amount of IPT allocated to the VNF_instance when it is created. It will influence the process time of a packet.
            </td>
            <td>IPT</td>
        </tr>
        <tr>
            <td>mem</td>
            <td>
                Is the amount of memory allocated to the VNF_instance when it is created
            </td>
            <td>MB</td>
        </tr>
        <tr>
            <td>max_share</td>
            <td>
                Define the number of SFC Requests that can map its VNF requirements for the VNF Instance.
            </td>
            <td>int</td>
        </tr>        
        <tr>
            <td>min_bandwidth</td>
            <td>
                Is the minimum bandwidth required to send the data generated after the packet being processed in VNF instance
            </td>
            <td>Mbps</td>
        </tr>
        <tr>
            <td>packet_cpu_demand</td>
            <td>
                Is the mean of CPU demanded by a packet to be processed that this VNF receives. The value is in terms of IP (instructions). In other words, how much CPU instructions are required to execute the packet.
            </td>
            <td>IP</td>
        </tr>
        <tr>
            <td>packet_network_demand</td>
            <td>                
                After de packet being processed, this value represents the total of bits demanded to be transferred to the next VNF Instance. This value is used by the link to calculate the total delay time.
            </td>
            <td>Mbits</td>
        </tr>
        <tr>
            <td>packet_mem_demand</td>
            <td>
                For each IPS consumed by the packet, how much memory it will consume by the VNF Instance.
            </td>
            <td>MB</td>
        </tr>
        <tr>
            <td>remote_data_access_cost</td>
            <td>
                Sometimes, the VNF needs to collect data from entities outside the scope of the simulation, so, in that case, you can define a certain amount of time that will be consume if the data must be collected.
            </td>
            <td>ms</td>
        </tr>        
        <tr>
            <td>remote_data_access_prob</td>
            <td>
                How often the remote data must be collected. If 0 then the data will never be required, if 1 it is always required.
            </td>
            <td>between 0 and 1</td>
        </tr>        
        <tr>
            <td>startup_ipt</td>
            <td> 
                Number CPU instructions consumed to startup the VNF Instance
            </td>
            <td>int (IPT)</td>
        </tr>
        <tr>
            <td>shutdown_ipt</td>
            <td> 
              Number CPU instructions consumed to shutdown the VNF Instance
            </td>
            <td>int (IPT)</td>
        </tr>
        <tr>
            <td>timeout</td>
            <td> 
              For how long the VNF Instance will be available even with not being used by any SFC Request without be destroyed
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>max_packet_queue</td>
            <td> 
              This parameter defines the max number of packets that can wait in the queue to be processed. The queue 
              grows when a packet arrives in the VNF Instance and, it decreases when a packet starts being processed. 
              If the packet arrives and the number of packets waiting in the queue are higher than the max_packet_queue, 
              it will be dropped. A log will be created for each packet dropped. If -1 the queue will be consider 
              unlimited.
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>resource_intensive</td>
            <td> 
                Define the type of resource that this VNF Type is intensive. The types can be: "CPU", "Memory", "Network".
                This value can be used in the scaling and migration components to decide what to do with a VNF Instance
                based on its resource consumption patterns. It is an optional attribute, by default all VNF Type
                are CPU intensive.
            </td>
            <td>String</td>
        </tr>
    </tbody>
</table>

### SFC 

The SFC is the chaining of one or multiples VNFs. Each mapped VNF_Instance for an SFC can be allocated in the same or 
different edge nodes. The data processed by the VNF is sent to the next VNF_Instance mapped with the next VNF of the SFC. 

Independently if the packets that will be processed are produced inside ou outside the edge environment, this packet 
will always have **an** "ingress node" or, in others **words**, the first edge node that arrives the packet. 
The ingress and egress node can be different among the users, for example, the ingress\ node of SFC_0 from the User_1 can be the Node_2 and the SFC_0 from the User_2 can ingress by the Node_4. The ingress and egress node can be equal to the edge node that the user is connected or not, in this situation the data is produced by the user, travel across the SFC and returns to the user.

The ingress and egress node are not listed in the SFC specs because it is generated after the creation of the nodes 
in the edge_environment. To find the ingress node of a user's SFC get it from the user in the user's field 
*sfc_ingress_egress*. This field has two values, ingress_node and egress_node.  In the above example the user 
requested the s_3, s_1 and s_0, for s_0 the ingress node is the n_2 and the egress node is the node n_3.

```
+----------------------+-------------------------------------------------------+
|         SFCs         |                 ['s_3', 's_1', 's_0']                 |
+----------------------+-------------------------------------------------------+
| SFC Ingress / Egress | {'s_3': {'ingress_node': 'n_3', 'egress_node': 'n_0'} |
|                      | , 's_1': {'ingress_node': 'n_2', 'egress_node': 'n_2' |
|                      | }, 's_0': {'ingress_node': 'n_2', 'egress_node': 'n_3 |
|                      |                          '}}                          |
+----------------------+-------------------------------------------------------+
```

The time that the packet spends from the real data source to arrives first edge node in the edge environment for our simulation is a constant. We consider it a constant because this time cannot be changed by improving placemen or scaling algorithm.

The attributes to create a new SFC are:

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>vnfs</td>
            <td>
                Is the number of possible VNFs that will compose the SFC
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>max_latency</td>
            <td>
                Max tolerable time to the data travels across all the VNF that compose the SFC
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>mean_packet_creation</td>
            <td>
                The packet creation rate variation in different SFC can be an essential factor for the scaling component. Because of that, each SFC has an attribute called mean_packet_creation. Its value is the mean in milliseconds of the packet rate generation. To improve the packet generation for a more accurate model, we use the Poisson distribution over this mean to calculate each packet's time interval. This strategy was also adopted in [Guangwu,2020]. Besides that, this attribute can be used to define types of SFC. For example, an SFC with a high rate of packet generation can be more "network" intensive.
            </td>
            <td>ms</td>
        </tr>          
        <tr>
            <td>packets_burst_interval</td>
            <td>
                The mean interval between two packet bursts
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>packets_burst_size</td>
            <td>
                The number of packets in each packet burst 
            </td>
            <td></td>
        </tr>
        <tr>
            <td>priority</td>
            <td>
                Will define the weight of the energy, resource or latency during the placement
            </td>
            <td></td>
        </tr>
        <tr>
            <td>timeout</td>
            <td>
                The total time that the SFC Instance will be maintained in execution without any packet be processed. After this timeout the VNF_Instances mapped to the SFC_Instance will be released to be used by another SFC_instance.
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>priorities_order</td>
            <td>
                Define the priority that the placement algorithm can take to select the best link and nodes for placing 
the VNF Instance for the requested SFC. The values can be:
* 1: Prioritize Latency
* 2: Prioritize Resource
* 3: Prioritize Energy
            </td>
            <td>int</td>
        </tr>
    </tbody>
</table>

### User 

Is the agent that requires the creation of SFC. The Users attributes are:

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>sfc_request_num</td>>
            <td>
                Is the number of SFCs Requests that the user will make during the simulation 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>latency</td>
            <td>
            Is the latency between the user and the Node that it is connected                
            </td>
            <td>ms</td>
        </tr> 
        <tr>
            <td>bandwidth</td>
            <td>
                The bandwidth between the user and the edge node that it is connected    
            </td>
            <td>Mbps</td>
        </tr> 
        <tr>
            <td>loss_rate</td>
            <td>
                 The loss rate of the link between the user and the edge node *DEPRECATED*
            </td>
            <td>between 0 and 1</td>
        </tr>                         
        <tr>
            <td>priority</td>
            <td>
                The priority that the SFCs requested from the user will be placed. Lower values ​​will be used from the low-priority users.
            </td>
            <td>int</td>
        </tr>                         
    </tbody>
</table>

### Node 

The edge node provides the computational resources to execute the VNF Instances. This entity can be considered as virtual machines being executed over a virtualization infrastructure. The Nodes attributes are:

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>CPU</td>
            <td>
                Is number of IPS available in the edge node.
            </td>
            <td>IPS</td>
        </tr>
        <tr>
            <td>MEM</td>
            <td>
                Is the total memory available in the edge node.
            </td>
            <td>MB</td>
        </tr>
        <tr>
            <td>vnf_num</td>
            <td>
                It the number of different VNF Types that the node can host instances. This will be used as parameter to define how much different VNF Types will be available in each node.
            </td>
            <td>int</td>
        </tr>           
        <tr>
            <td>group</td>
            <td>
                Its a label that categorize the nodes, nodes with same value are part of the same neighborhood. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>energy_max</td>
            <td>
                It is the maximum of energy consumed by the node. We assume that this value occur when the CPU is in the maximum usage.
            </td>
            <td>Watt</td>
        </tr> 
        <tr>
            <td>energy_idle</td>
            <td>
                It is the energy consumed by the node when none VNF is instantiated. If this attribute is blank we define 
the energy_idle as 70% of the selected energy_max, otherwise we select one of the given values randomly, the energy idle 
must be lower than the energy_max. If there is no energy_idle lower than the energy_max selected we use the 0.7 rule.
            </td>
            <td>Watt</td>
        </tr> 
        <tr>
            <td>disk_delay</td>
            <td>
                It is the time consumed to access some data on the disk. If the memory is used over 100% during the VNF processing phase, we will add this time to the packet process. This time is computed only once per-packet processing.
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>ran_node_prob</td>
            <td>
                Its the probability of a node being tagged as a node attached to a RAN 
            </td>
            <td>between 0 and 1</td>
        </tr> 
        <tr>
            <td>core_node_prob</td>
            <td>
                Its the probability of a node being tagged as a core node attached to a central edge data center 
            </td>
            <td>between 0 and 1</td>
        </tr>
        <tr>
            <td>location</td>
            <td>
                Its the geolocation where the node is in execution
            </td>
            <td>Location Object</td>
        </tr>
    </tbody> 
</table>

Location, JSON example 

```json
"location": [
                    {"name": "The name",  "key": "Key", "latitude": -22.9064, "longitude": -43.13325, "node_prob":  0.4} 
                ]
```

#### Node Types 

Each node is tagged as a RAN / CORE / DEFAULT node. These tags will define the edge nodes topology. The RAN nodes will be
the attached to the RAN and will be the node with the user small latency. The CORE nodes will be located in edge datacenters. 
The DEFAULT nodes will be spread between the RAN and the CORE nodes.

The user will be attached to a RAN node. The SFC Requests data ingress node will be created or from the node where the 
user is attached or from a core node. The egress node 

### Link 

Is the virtual link between two nodes, every node has a virtual link to all others nodes.  The delays used to calculated the link latency are:

1. Transmission delay (dtrans)
2. Propagation delay (dprop)

The transmission delay (dtrans) is calculated by the packet size / link bandwidth, the propagation delay is a link attribute. The Links attributes are:

"There are three main components in a response delay: a) communication delay that depends on data rate; b) computational delay that depends on computational time; and c) propagation delay that depends on propagation distance. In general, in cloud computing, the end-to-end delay is greater than 80ms (or 160ms for response delay). This is not suitable for delay-sensitive applications, such as remote surgery and VR, that require tactile speed with a response delay of at most 1ms. In edge computing, UEs experience reduced overall end-to-end delay and response delay due to their close proximity to edge servers. The strategic location of edge cloud reduces the communication and propagation delays. For instance, the propagation distance is reduced to tens of meters via D2D communication and in small cells, and it is generally limited within a kilometer from the UEs." (Hassan,2019)

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>bandwidth</td>
            <td>
                The bandwidth available between the nodes.
            </td>
            <td>Mbps</td>
        </tr>
        <tr>
            <td>loss_rate</td>
            <td>
                The loss rate of the link *DEPRECATED*
            </td>
            <td>between 0 and 1</td>
        </tr>           
        <tr>
            <td>propagation</td>
            <td>
                The propagation delay between the nodes.
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>energy_consumption</td>
            <td>
                The mean energy consumed in the link during one hour of operation. This value will be calculated using the energy consumed in all the network elements used to create the virtual link.
            </td>
            <td>watts/hour</td>
        </tr>
        <tr>
            <td>loopback_bandwidth</td>
            <td>
                The bandwidth used as the Loopback link. This links is used by consecutive VNF Instances running in the same edge node.
            </td>
            <td>Mbps</td>
        </tr>
        <tr>
            <td>num_links_between_nodes</td>
            <td>
                How many links will be created between two nodes. Many values can be defines thus a network with a heterogeneous number of links will be created.
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>max_packet_queue</td>
            <td> 
              This parameter defines the max number of packets that can wait in the queue to be processed by the link. 
              The queue grows when a packet arrives in the Link and, it decreases when a packet starts being processed. 
              If the packet arrives and the number of packets waiting in the queue are higher than the max_packet_queue, 
              it will be dropped. A log will be created for each packet dropped. If -1 the queue will be consider 
              unlimited.
            </td>
            <td>int</td>
        </tr>
    </tbody>
</table>

### Data Source

The packets that the user will be send to be processed in the SFC will follow a pattern defined in one of the Data Source types. 

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>packet_interval</td>
            <td>
                The packet creation rate variation in different SFC can be an essential factor for the scaling component. Because of that, each SFC has an attribute called mean_packet_creation. Its value is the mean in milliseconds of the packet rate generation. To improve the packet generation for a more accurate model, we use the Poisson distribution over this mean to calculate each packet's time interval. This strategy was also adopted in [Guangwu,2020]. Besides that, this attribute can be used to define types of SFC. For example, an SFC with a high rate of packet generation can be more "network" intensive.
            </td>
            <td>ms</td>
        </tr>          
        <tr>
            <td>packets_burst_interval</td>
            <td>
                The mean interval between two packet bursts
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>packets_burst_size</td>
            <td>
                The number of packets in each packet burst 
            </td>
            <td>int</td>
        </tr>        
        <tr>
            <td>packet_size</td>
            <td>
                The number of CPU Instructions that will be demanded to process the packet
            </td>
            <td>IP</td>
        </tr>        
    </tbody>
</table>

## Entities Generated During the Simulation

### Packet 

The Packet entity store data about each packet processed during the simulation. The SLA violation attr is marked to TRUE 
in the exact simulation time when the packet violate the SLA. For example, if the packet was generated in time 10 and 
have a max_delay = 20, thus, if in the simulation time 31 the packet yet not reach the last link of the SFC Instance than 
the packet will be tagged as a packets that violate the SLA.   

The Packet is the entity that will consume the resource in the VNF Instance. Each packet is associated with an SFC Request
and have an unique id in the flow generated by the SFC Request. 


<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>delay</td>
            <td>
                The delay is the time spend by the packet to flow between the ingress and egress node in the 
SFC Instance.  
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>max_delay</td>
            <td>
                Its is the max expected delay   
            </td>
            <td>ms</td>
        </tr>
        <tr>
            <td>sla_violated</td>
            <td>
                If the delay where greater than the max_delay thus the packet will be tagged as violated the SLA   
            </td>
            <td>Bool</td>
        </tr>
        <tr>
            <td>mobility_penalty</td>
            <td>
                When the user move from one node to another a penalty time is computed in the packet delay.
                This value are already computed in the "delay" attribute, thus, this is a informational attr only
            </td>
            <td>ms</td>
        </tr>
    </tbody> 
</table>

### SFC Request

The users will demand for SFCs to execute some task, link "Pedestrian Detection". The SFC_Request object will be used to create this request. In this simulation framework, the SFC requests will be created using the values defined in the User and SFC entities. The SFC_Request object has the following attributes: 

* User: The user that requested the SFC.
* SFC: The SFC requested.
* Data_Source: The object that define the packet patter generator.
* Priority The priority of the request, based on the User priority attribute. This value can be equal or lower than the User priority attribute.
* Arrival_Time: The time when the request will be processed by the simulation.
* Ingress_Node: The node where the data source is connected
* Egress_Node: The node where the last VNF Instance needs to dellivery the processed data


```json
{
  "sfc_requests": {
    "arrival": "poisson",
    "duration": [100]
  }
}
```

```json
{
  "sfc_requests": {
    "arrival": "linear",
    "increase_requests_per_window": 50,
    "duration": [100]
  }
}
```

<table>
    <thead>
        <tr>
            <th scope="col">Attr</th>
            <th scope="col">Description</th>
            <th scope="col">Unit</th>
        </tr>
    </thead>
    <tbody>
          <tr>
            <td>sfc_requests.arrival</td>
            <td>
              How the SFC Requests arrival will be distributed during the simulation. Now we have two options: poisson and linear. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>sfc_requests.increase_requests_per_window</td>
            <td>
              This parameter should be provided when the "linear" arrival was selected. It will define how many requests will be increased in each new time window.
              If the value was defined to 10 the first window will have 10 SFC Requests, the second will have 20, the third will have 30. 
            </td>
            <td>int</td>
        </tr>
        <tr>
            <td>request_duration</td>
            <td>
                For how long time the packets from the user's SFC_Request will be generated.
            </td>
            <td>int</td>
        </tr>
    </tbody>
</table>

Before starting sending packet for the requested SFC, the user will ask for the system to allocate the resources for the task.

```
+-------------+             +-----------+ +---------------+
| SFC_Request |             | Placement | | SFC_Instance  |
+-------------+             +-----------+ +---------------+
       |                          |               |
       | Request Placement        |               |
       |------------------------->|               |
       |                          |               |
       |       Placement Executed |               |
       |<-------------------------|               |
       |                          |               |
       | Process Packets          |               |
       |----------------------------------------->|
       |                          |               |
       |                         Packet Processed |
       |<-----------------------------------------|
       |                          |               |

Created with: https://textart.io/sequence
```

The time between the end of the placement and the user receives the information that it can start sending packets is negligible

### SFC Instance

The SFC_Request will be processed by an SFC_Instance. The SFC_Instance object has the following attributes: 

* Timeout: The total time that the SFC_Instance will be online without receiving any packet
* Slice: The slice where the SFC_Instance is running
* SFC_Requests: A list with all the SFC_Requests whose packets are processed in the SFC_Instance
* Accept New Requests: It is a boolean that define if new SFC_Requests can be mapped to this SFC_Instance 

```diff
The VNF_Instance object will now map the SFC_Instance and not the pairs (user, sfc) anymore 
```

### VNF Instance

The VNF Instance if the entity that will process the packets.

Important attributes:
    
1. **startup_remain_time**: Remain time for the VNF Instance be ready for processing packets
2. **shutdown_remain_time**: Remain time for the VNF Instance release the resources used
3. **timeout**: Define how long the vnf instance will be available without associated with any SFC Instance
4. **accept_sfc_instance**: When False the instance cannot be associated with a SFC Instance
5.**active**: When False the resource used by the VNF Instance will be released

## Placement

The Placements algorithms are responsible for:

1. How many instances of each a VNF Type must be deployed?
2. What node must execute each VNF_Instance created?
3. Which instance will attend each VNF of each SFC Requested?

To implement a new Placement algorithm, you must make an inheritance of the abstract class Placement, 
as depicted in the image below.

![class diagram](doc/img/diagrams-class_diagram.png "Class Diagram")

Independently of the placement strategy adopted, the ultimate challenge will be to select the path in a nom cyclic oriented graph, as depicted in the image below. The nodes of the Graph represent the possible edge nodes that can execute an VNF_Instance of a VNF and the edges represents the cost of use the next vertex in function of the previous vertex. 

![placement strategy](doc/img/diagrams-placement_strategy.png "Placement Strategy")

We provide some implementations:

* *Naive Placement*: Create one instance for each VNF of each SFC requested by the user. It does not verify if the node has or not resource, if the link has sufficient bandwidth and if the SLA is attended. It is really naive!

* *LPP*: Uses a Mixed-integer programming strategy to find the optimal placement strategy. It's very slow even if you run with it in a small environment, for example, with 10 nodes.

* *Dijkstra*: This is a placement that uses Dijkstra implementation to find a good plan to place the requested SFC.

* *Smart Placement*: In progress 

If the placement algorithm could not place an SFC requested by the user, the algorithm's implementation must inform it to the edge environment. The simulation will be only with the placed SFCs.

## Scaling

VNF Scaling the process where the resources allocated to a VNF_Instance are changed according to the demands.    

### Basic CPU Scaling

This scaling method only changes the CPU allocated to the VNF Instance. The Rules to trigger the scaling are fixed and, 
the CPU increment and decrement are also fixed. In the above example, the scaling method will be executed each 100ms, 
and if the CPU usage (load) outrun 100% the CPU allocated to the VNF Instance will be incremented in 10% (SCALING UP), and, if the 
CPU load was lower than 70% thus the CPU allocated will be decremented in 10% (SCALING DOWN).

If the resource required by the scaling were higher than the resource available in the node, the scaling will fail. It 
will also fail if the scaling down try to set an CPU allocated value lower than the minimum of CPU demanded by the 
VNF Type. 

```json
"scaling": {
    "heuristic" : "BasicCPUScaling",
    "parameters": {
      "monitor_interval" : 100,
      "cpu_usage_max"    : 1,
      "cpu_increment"    : 0.1,
      "cpu_usage_min"    : 0.7,
      "cpu_decrement"    : 0.1
    }
}
```

<table>
    <thead>
        <tr>
            <th scope="col">Parameter</th>
            <th scope="col">Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>monitor_interval</td>
            <td>
                The interval between the execution of the scaling
            </td>
        </tr>
        <tr>
            <td>cpu_usage_max</td>
            <td>
                The max threshold for the CPU usage (load) to trigger the scaling up
            </td>
        </tr>        
        <tr>
            <td>cpu_increment</td>
            <td>
                The percentage of CPU that will be increased if the scaling up were triggered
            </td>
        </tr>
        <tr>
            <td>cpu_usage_min</td>
            <td>
                The min threshold for the CPU usage (load) to trigger the scaling down
            </td>
        </tr>        
        <tr>
            <td>cpu_decrement</td>
            <td>
                The percentage of CPU that will be decreased if the scaling down were triggered
            </td>
        </tr>
    </tbody>
</table>

### Smart Vertical Scaling Up

The objective of the **Smart Vertical Scaling Up** is to execute scaling up actions in the VNF Instances resources at the 
SFC Instances whose packets are violating the SLA in a hate above the configured threshold. The algorithm is depicted in 
the image below. 

![mapping](doc/img/scaling/diagrams-ScalingUpAlgorithm.drawio.png "Smart Vertical Scaling Up Algorithm")

The configuration parameters available in the implemented scaling are:

```json
  "scaling": {
    "heuristic" : "SmartVerticalScalingUp",
    "parameters": {
      "monitor_interval": 500,
      "monitor_window_size": 500,
      "load_vnf_instance_limit": 0.5,
      "resource_increment": 0.1,
      "resource_decrement": 0.1,
      "cpu_node_available_importance": 1,
      "mem_node_available_importance": 1,
      "cpu_vnf_load_importance": 1,
      "mem_vnf_load_importance": 1,
      "prioritize_nodes_with_more_resource_available": 0,
      "acceptable_sla_violation_rate": {
        "default":"0.1",
        "s_1": "0.05",
        "s_0": "0.15"
      },
      "waiting_time_between_scaling_ups": 4000
    }
  }
```

<table>
    <thead>
        <tr>
            <th scope="col">Parameter</th>
            <th scope="col">Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>monitor_interval</td>
            <td>
                The interval between each monitoring action 
            </td>
        </tr>
        <tr>
            <td>monitor_window_size</td>
            <td>
                The size of the window used to collect events from the entities  
            </td>
        </tr>
        <tr>
            <td>load_vnf_instance_limit</td>
            <td>
                The max load that a VNF Instance must have before the scaling being executed
            </td>
        </tr>        
        <tr>
            <td>resource_increment</td>
            <td>
                The percentage of CPU and Memory that will be increased if the scaling up were triggered
            </td>
        </tr> 
        <tr>
            <td>resource_decrement</td>
            <td>
                The percentage of CPU and Memory that will be decreased if the scaling down were triggered
            </td>
        </tr>
        <tr>
            <td>cpu_node_available_importance</td>
            <td>
                Used to compute the host allocated metric. Define the importance of the CPU available in the node.   
            </td>
        </tr>
        <tr>
            <td>mem_node_available_importance</td>
            <td>
                Used to compute the host allocated metric. Define the importance of the Memory available in the node.  
            </td>
        </tr>
        <tr>
            <td>cpu_vnf_load_importance</td>
            <td>
                Used to compute the VNF Instance Load Metric. Define the importance of the CPU Load in the VNF Instance.  
            </td>
        </tr>
        <tr>
            <td>mem_vnf_load_importance</td>
            <td>
                Used to compute the VNF Instance Load Metric. Define the importance of the Mem Load in the VNF Instance.  
            </td>
        </tr>
        <tr>
            <td>prioritize_nodes_with_more_resource_available</td>
            <td>
                If 1 the vnf instances running in the node with **higher** resources available will be scaled firstly (node resource balance strategy) 
                If 0 the vnf instances running in the node with **lower** resources available will be scaled firstly (node consolidation strategy)
            </td>
        </tr>
        <tr>
            <td>acceptable_sla_violation_rate</td>
            <td>
                Dict with the max packet violation rate in the monitor window. If the sfc was not defined thust the 
default value will be used.
            </td>
        </tr>
        <tr>
            <td>waiting_time_between_scaling_ups</td>
            <td>
                Time that the monitor must wait after a scaling up before monitoring the SFC Instance again.
            </td>
        </tr>
    </tbody>
</table> 

### Smart Vertical Scaling Down

The objective of the **Smart Vertical Scaling Down** is to execute scaling down actions in the VNF Instances resources at the 
SFC Instances whose resources are not being used and the SLA is being met, as per  the configured threshold. The algorithm is depicted in 
the image below. 


![mapping](doc/img/scaling/diagrams-ScalingDownAlgorithm.drawio.png "Smart Vertical Scaling Down Algorithm")

The configuration parameters available in the implemented scaling are:

```json
 "scaling_down": {
    "heuristic" : "SmartVerticalScalingDown",
    "parameters": {
      "monitor_interval": 100,
      "monitor_window_size": 500,
      "load_vnf_instance_limit": 0.5,
      "resource_decrement": 0.1,
      "cpu_node_available_importance": 1,
      "mem_node_available_importance": 1,
      "cpu_vnf_load_importance": 1,
      "mem_vnf_load_importance": 1,
      "prioritize_nodes_with_more_resource_available": 0,
      "load_metric_importance": 1,
      "process_contribution_importance": 1,
      "resource_available_importance": 1
    }
  }

```

<table>
    <thead>
        <tr>
            <th scope="col">Parameter</th>
            <th scope="col">Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>monitor_interval</td>
            <td>
                The interval between each monitoring action 
            </td>
        </tr>
        <tr>
            <td>monitor_window_size</td>
            <td>
                The size of the window used to collect events from the entities  
            </td>
        </tr>
        <tr>
            <td>load_vnf_instance_limit</td>
            <td>
                The max load that a VNF Instance must have before the scaling being executed
            </td>
        </tr>        
        <tr>
        </tr> 
        <tr>
            <td>resource_decrement</td>
            <td>
                The percentage of CPU and Memory that will be decreased if the scaling down were triggered
            </td>
        </tr>
        <tr>
            <td>cpu_node_available_importance</td>
            <td>
                Used to compute the host allocated metric. Define the importance of the CPU available in the node.   
            </td>
        </tr>
        <tr>
            <td>mem_node_available_importance</td>
            <td>
                Used to compute the host allocated metric. Define the importance of the Memory available in the node.  
            </td>
        </tr>
        <tr>
            <td>cpu_vnf_load_importance</td>
            <td>
                Used to compute the VNF Instance Load Metric. Define the importance of the CPU Load in the VNF Instance.  
            </td>
        </tr>
        <tr>
            <td>mem_vnf_load_importance</td>
            <td>
                Used to compute the VNF Instance Load Metric. Define the importance of the Mem Load in the VNF Instance.  
            </td>
        </tr>
        <tr>
            <td>prioritize_nodes_with_more_resource_available</td>
            <td>
                If 1 the vnf instances running in the node with **higher** resources available will be scaled firstly (node resource balance strategy) 
                If 0 the vnf instances running in the node with **lower** resources available will be scaled firstly (node consolidation strategy)
            </td>
        </tr>
        <tr>
            <td>load_metric_importance</td>
            <td>
                Used to compute the host allocated metric. Define the importance of the load available in the node
            </td>
        </tr>
        <tr>
            <td>process_contribution_importance</td>
            <td>
                Used to compute the VNF Instance process contribution importance Metric. Define the importance of scaling down in the VNF Instance. 
            </td>
        </tr>
			<tr>
            <td>resource_available_importance</td>
            <td>
               Used to compute the VNF Instance available resources importance Metric. Define the importance of available resources in the VNF Instance.  
            </td>
        </tr>
    </tbody>
</table> 

## Todo Placement

- [x] How to choose the order to do the placement?
- [ ] Run simulations for the same implementation with different simulated environments.
- [ ] Create specs for CPU Intensive, Network Intensive VNF.
- [ ] Migrate the instance from one note to another.
- [ ] Placement for a single SFC and for multiples SFCs.
- [ ] Modify the experiment to receive requests for new SFCs during the simulation phase.

## Todo Simulator

Things that we certainly will do.

- [ ] Implement the loss rate in the link process
- [ ] Define the model of how the packets are produced by the SFC using a configuration parameter.
- [ ] SFC lifetime, how long the SFC will stay in the simulation. This parameter will be placed in the SFC. Thus, we will have short and longs SFCs
- [ ] Validate the configuration parameters (users, sfcs, vnfs, link and the placement and scaling algorithm)
- [ ] SDN Controller must consume time for forwarding the first packet of a SFC Request

## Todo Analysis

- [ ] Calculate the mean of the total delay for an SFC from a User. It will be calculated by calculating the difference between the packet creation and the packet processed time in the SFC file

## Ideas

Things that we maybe we will do.

- [x] Create the entities (source) to create the flow (cameras, for example) 
- [ ] Create the entities (sink) to consume the flow (applications, for example) 
- [ ] Place the delay from source to the first VNF instance
- [ ] Place the delay from the last VNF_Instance to the sink
- [ ] Ths SFC Type is associated with one slice, if the same VNF chain can be placed in two slices, than, two SFCs must be defined in design time

# Profiling

If your code is running slowly, and you want to understand where is the bottleneck, you can use the scalene profiler.
We suggest the use the scalene (https://pypi.org/project/scalene/). Just uncomment the above line in run_experiment.sh file, 
it will generate an HTML file named out.html with the parts of the code that is consuming more resource. 

```
python3 -m scalene --html --reduced-profile --outfile=out.html $path_program/main.py \
```


## References

Guangwu Hu, Qing Li, Shuo Ai, Tan Chen, Jingpu Duan, Yu Wu, A proactive auto-scaling scheme with latency guarantees for multi-tenant NFV cloud, Computer Networks, Volume 181, 2020, 107552

N. Hassan, K. A. Yau and C. Wu, "Edge Computing in 5G: A Review," in IEEE Access, vol. 7, pp. 127276-127289, 2019, doi: 10.1109/ACCESS.2019.2938534.
