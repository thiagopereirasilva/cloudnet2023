# Python Classes
from Scaling import Scaling
from Simulation_Entities.SFC_Request import SFC_Request
from Simulation_Entities.VNF_Instance import VNF_Instance
from Simulation_Entities.SFC_Instance import SFC_Instance
from Simulation_Entities.Packet import Packet

from Edge_Entities.Node import Node
from Edge_Entities.VNF import VNF
from Edge_Entities.User import User
from Edge_Entities.SFC import SFC
from Edge_Entities.Link import Link
from Edge_Entities.Data_Source import Data_Source

import simpy.rt
import simpy
import random
import json
import argparse

import time

# Store info about the edge environment entities
from Edge_Environment import Edge_Environment

# Simulation Class
from Simulation import Simulation
from Simulation_SDN_Controller import Simulation_SDN_Controller
from Simulation_Data import Simulation_Data
from Simulation_Monitor import Simulation_Monitor

# Placement and Scaling Classes
from Placement import *
from Scaling import *

from Scaling.BasicCPUScaling import BasicCPUScaling
from Scaling.SmartVerticalScalingUp import SmartVerticalScalingUp
from Scaling.SmartVerticalScalingDown import SmartVerticalScalingDown
from Scaling.SmartQueueScaling import SmartQueueScaling
from Scaling.TCPInspiredVerticalScalingUp import TCPInspiredVerticalScalingUp
def main():

    # Parse parameters
    parser = argparse.ArgumentParser(prog='VNF Simulator')
    parser.add_argument('--debug', default=False, help='Print the debug options --debug 1.')
    parser.add_argument('--save', default=False, help='Save the generated entities in a json file --save Entities.json .')
    parser.add_argument('--load', default=False, help='Load the saved entities from a json file and convert it in environment entities --load Entities.json .')
    parser.add_argument('--list', default=False, help='Print all the entities generated --list 1.')
    parser.add_argument('--show', default=False, help='Show the first instance of each entity generated --show 1.')
    parser.add_argument('--specs', default=0, help='The specs file that will guide the entities generation --specs ./specs.json.')
    parser.add_argument('--path_result_files', default="./Results/", help='Path where the result files will be saved --path_result_files ./Results_ExperimentX')
    parser.add_argument('--simulation_parameters', default="./simulation_parameters.json", help='Path where the simulation paramer file is located --simulation_parameters ./simulation_parameters.json')
    parser.add_argument('--random_seed', default="", help='The random seed used by Python to generate the same random values among multiples executions')
    parser.add_argument('--only_placement', default="", help='Execute only the placement and stops before starting the simulation')
    parser.add_argument('--user_mobility_file', default="", help='The file with the mobility pattern from the users')

    # args process
    args = parser.parse_args()

    # Load the specifications from the specs files
    specs = ""
    with open(args.specs) as json_file:
        specs = json.load(json_file)

    simulation_parameters = {}
    with open(args.simulation_parameters) as json_file:
        simulation_parameters = json.load(json_file)

    # If the random_seed is provided as a parameter use it, also use the value in the config specs file
    if args.random_seed != "":
        RANDOM_SEED = args.random_seed
    else:
        RANDOM_SEED = simulation_parameters['simulation']['random_seed']

    # Seed used in all the random functions
    random.seed(RANDOM_SEED)

    # How many times the simulation will be executed using the same environment entities
    NUM_ROUNDS_SIMULATION = simulation_parameters['simulation']['num_rounds']

    # The total time simulation limit (ms)
    TOTAL_TIME_SIMULATION = simulation_parameters['simulation']['total_time']

    # The total time simulation limit (ms)
    TIME_WINDOW = simulation_parameters['simulation']['time_window']

    # Will define if the loopback link will be inserted in the events of link process
    COMPUTE_LOOPBACK_TIME = simulation_parameters['simulation']['compute_loopback_time']

    # The interval for monitoring the SFC Instances
    try:
        SFC_INSTANCE_MONITOR_INTERVAL=simulation_parameters['simulation']['sfc_instance_monitor_interval']
    except KeyError as ke:
        # Default value
        SFC_INSTANCE_MONITOR_INTERVAL=100

    # Config for generating or not packets during the simulation, if not we are testing only the placement
    try:
        PACKET_GENERATION=simulation_parameters['simulation']['packet_generation']
    except KeyError as ke:
        # Default value
        PACKET_GENERATION=0

    # The max number of packets that can violate the SLA without
    try:
        MAX_SLA_VIOLATION_SFC_INSTANCE_SHARED=simulation_parameters['simulation'][
            'max_sla_violation_sfc_instance_shared']
    except KeyError as ke:
        # Default value
        MAX_SLA_VIOLATION_SFC_INSTANCE_SHARED=1

    # The size of the packet window that will be analyzed
    try:
        SFC_INSTANCE_MONITOR_WINDOW_SIZE=simulation_parameters['simulation'][
            'sfc_instance_monitor_window_size']
    except KeyError as ke:
        # Default value
        SFC_INSTANCE_MONITOR_WINDOW_SIZE = 200    # The size of the packet window that will be analyzed

    try:
        ENABLE_REPLACEMENT=False
        if simulation_parameters['placement']['enable_replacement'] == 1:
            ENABLE_REPLACEMENT=True
    except KeyError as ke:
        ENABLE_REPLACEMENT=False # Default value

    try:
        MAX_REPLACEMENT_RETRIES=simulation_parameters['placement']['max_replacement_retries']
    except KeyError as ke:
        MAX_REPLACEMENT_RETRIES=4 # Default value

    try:
        REPLACEMENT_BACKOFF_SLOT_SIZE=simulation_parameters['placement']['replacement_backoff_slot_size']
    except KeyError as ke:
        REPLACEMENT_BACKOFF_SLOT_SIZE=200 # Default value

    try:
        MIGRATION_THRESHOLD_PERCENTAGE=simulation_parameters['migration']['migration_threshold_percentage']
    except KeyError as ke:
        # Default value
        MIGRATION_THRESHOLD_PERCENTAGE = 0.8    # Percentage of the SFC Max Delay to be considered as a migration threshold

    try:
        MIGRATION_THRESHOLD_PACKET_WINDOW=simulation_parameters['migration']['migration_threshold_packet_window']
    except KeyError as ke:
        # Default value
        MIGRATION_THRESHOLD_PACKET_WINDOW = 10    # Number of packets of a user to be considered in migration threshold detection

    ORDER_SFC_REQUEST_BY_SIMILARITY = None
    try:
        if simulation_parameters['simulation']['order_sfc_request_by_similarity']:
            ORDER_SFC_REQUEST_BY_SIMILARITY=simulation_parameters['simulation']['order_sfc_request_by_similarity']

            # if in the config file the similatiry is defined as "none"
            if ORDER_SFC_REQUEST_BY_SIMILARITY == "none":
                ORDER_SFC_REQUEST_BY_SIMILARITY = None
    except KeyError as ke:
        pass

    try:
        LOG_LINK_EVENTS=False
        if simulation_parameters['simulation']['log_link_events'] == 1:
            LOG_LINK_EVENTS=True
    except KeyError as ke:
        # Default value
        LOG_LINK_EVENTS=False

    try:
        LOG_VNF_INSTANCE_EVENTS=False
        if simulation_parameters['simulation']['log_vnf_instance_events'] == 1:
            LOG_VNF_INSTANCE_EVENTS=True
    except KeyError as ke:
        # Default value
        LOG_VNF_INSTANCE_EVENTS=False

    try:
        EXECUTE_USER_MOBILITY=False
        if simulation_parameters['simulation']['execute_user_mobility'] == 1:
            EXECUTE_USER_MOBILITY=True
    except KeyError as ke:
        # Default value
        EXECUTE_USER_MOBILITY=False

    try:
        TIME_LIMIT_TO_PACKET_GENERATION = TOTAL_TIME_SIMULATION
        if 'time_limit_to_packet_generation' in simulation_parameters['simulation']:
            TIME_LIMIT_TO_PACKET_GENERATION = simulation_parameters['simulation']['time_limit_to_packet_generation']
    except KeyError as ke:
        # Default value
        TIME_LIMIT_TO_PACKET_GENERATION = TOTAL_TIME_SIMULATION

    try:
        LOG_LINK_ENTITY=False
        if simulation_parameters['simulation']['log_link_entity'] == 1:
            LOG_LINK_ENTITY=True
    except KeyError as ke:
        # Default value
        LOG_LINK_ENTITY=True

    NUM_NODEs             = specs['entities_number']['nodes']
    NUM_USERs             = specs['entities_number']['users']
    NUM_VNFs              = specs['entities_number']['vnfs']
    NUM_SFCs              = specs['entities_number']['sfcs']
    NUM_DATA_SOURCES      = specs['entities_number']['data_sources']

    # The interval for monitoring the SFC Instances
    user_mobility = {}
    USER_MOBILITY_FILE = ""
    if args.user_mobility_file:
        USER_MOBILITY_FILE = args.user_mobility_file

    sfc_requests_parameters = {}
    try:
        sfc_requests_parameters=specs['sfc_requests']
    except KeyError as ke:
        sfc_requests_parameters = {
            "arrival": SFC_Request.ARRIVAL_POISSON
        }
        pass

    # Specs Validation
    if args.load == False:

        # a) The number of VNF created must be greater than the number of VNFs requested by the SFC
        if max(specs['sfc']['vnf_num']) > specs['entities_number']['vnfs']:
            print("Error: The number of VNFs created is lower them the number of VNFs requested by the SFCs")
            quit()

        # b) The number of SFC created must be greater than the number of SFCs requested by the User
        if max(specs['user']['sfc_request_num']) > specs['entities_number']['sfcs']:
            print("Error: The number of SFCs created is lower them the number of SFCs requested by the users")
            quit()

        # c) The number of VNFs in the Node must be lower than the number of VNFs created
        if max(specs['node']['vnf_num']) > specs['entities_number']['vnfs']:
            print("Error: The number of VNFs in the Node must be lower than the number of VNFs created")
            quit()

    # Execute the same experiment 'n' times, this will avoid bias
    for i in range(NUM_ROUNDS_SIMULATION):

        start_time = time.time()

        # Real Time Simulation
        # env = simpy.rt.RealtimeEnvironment(factor=0.001, strict=False)
        env = simpy.Environment()

        # The simulation data object
        sd = Simulation_Data()

        # Path where the files will be stored (csv and images)
        exp_path = "{}/Round_{}".format(args.path_result_files, i)

        # Generate the random edge environment
        # the name is not used yet, is just a label
        e1 = Edge_Environment(
            name="edge1",
            specs=specs,
            random_seed=RANDOM_SEED,
            total_time = TOTAL_TIME_SIMULATION,
            time_window=TIME_WINDOW,
            max_replacement_retries=MAX_REPLACEMENT_RETRIES,
            replacement_backoff_slot_size=REPLACEMENT_BACKOFF_SLOT_SIZE,
        )

        # Create the SDN Controller Like
        ctrl = Simulation_SDN_Controller(e1)

        # If a file is informed in the load parameter, replace all the entities previously
        # created with the entities in the load file
        if args.load:
            e1.load_entities_json(args.load)

        # Save the entities generated randonly into a file
        if args.save:
            e1.save_entities_json(args.save)

        # Generate the plan for the VNF instance allocation
        # Load the correct object based on the specification placement_heuristic selected
        parameters = []
        if simulation_parameters['simulation']['share_sfc_instance'] == "1" or simulation_parameters['simulation']['share_sfc_instance'] == 1:
            parameters.append("sfc_instance_sharable=True")
        else:
            parameters.append("sfc_instance_sharable=False")

        str_parameter = ""
        if 'parameters' in simulation_parameters['placement'] and len(simulation_parameters['placement']['parameters']) > 0:
            aux_parameters = simulation_parameters['placement']['parameters']
            for p in aux_parameters:
                key = p
                value = aux_parameters[key]
                parameters.append("{}='{}'".format(key, value))

        str_parameter = ", ".join(parameters)
        str_parameter = ", {}".format(str_parameter)

        str_placement = "{0}.{0}(e1 {1})".format(simulation_parameters['placement']['heuristic'], str_parameter)
        placement = eval(str_placement)

        ####### Scaling object
        # Create the scaling
        # only execute if there is a scaling configured
        scaling = False
        if 'scaling' in simulation_parameters:
            # Load the correct object based on the specification placement_heuristic selected
            scaling_parameters = []
            str_parameter = ""
            if 'parameters' in simulation_parameters['scaling'] and len(
                    simulation_parameters['scaling']['parameters']) > 0:
                aux_parameters = simulation_parameters['scaling']['parameters']
                for p in aux_parameters:
                    key = p
                    value = aux_parameters[key]
                    scaling_parameters.append("{}=\"{}\"".format(key, value))

                str_parameter = ", ".join(scaling_parameters)
                str_parameter = "{}".format(str_parameter)

            str_scaling = "{}(env=env, edge_environment = e1, sd = sd, {})".format(simulation_parameters['scaling']['heuristic'], str_parameter)
            scaling = eval(str_scaling)

        ####### Scaling object
        # Create the scaling
        # only execute if there is a scaling configured
        scaling_down = False
        if 'scaling_down' in simulation_parameters:
            # Load the correct object based on the specification placement_heuristic selected
            scaling_parameters = []
            str_parameter = ""
            if 'parameters' in simulation_parameters['scaling'] and len(
                    simulation_parameters['scaling_down']['parameters']) > 0:
                aux_parameters = simulation_parameters['scaling_down']['parameters']
                for p in aux_parameters:
                    key = p
                    value = aux_parameters[key]
                    scaling_parameters.append("{}=\"{}\"".format(key, value))

                str_parameter = ", ".join(scaling_parameters)
                str_parameter = "{}".format(str_parameter)

            str_scaling = "{}(env=env, edge_environment = e1, sd = sd, {})".format(simulation_parameters['scaling_down']['heuristic'], str_parameter)

            scaling_down = eval(str_scaling)

        # Show the first of each generated entity
        if args.show:
            e1.nodes['n_0'].show()
            e1.sfcs['s_0'].show()
            e1.vnfs['v_0'].show()
            e1.users['u_0'].show()
            e1.links[('n_0','n_1')].show()
            list(e1.vnf_instances)[0].show()

        # Only generate the placement plan files
        if args.only_placement == "1":
            print("Quit after generate the placement")
            quit()

        # Create the shared resources for each Link
        resource_links = {}
        for link in e1.links:
            aux_link = e1.links[link]
            resource_links[aux_link.name] = simpy.Resource(env, capacity=1)

        # Create the simulation
        sm = Simulation (
            edge_environment = e1,
            placement = placement,
            ctrl = ctrl,
            env = env,
            sd = sd,
            round=i,
            total_time_simulation = TOTAL_TIME_SIMULATION,
            time_window = TIME_WINDOW,
            resource_links = resource_links,
            path_result_files = exp_path,
            compute_loopback_time = COMPUTE_LOOPBACK_TIME,
            order_sfc_request_by_similarity=ORDER_SFC_REQUEST_BY_SIMILARITY,
            packet_generation=PACKET_GENERATION,
            log_vnf_instance_events=LOG_VNF_INSTANCE_EVENTS,
            log_link_events=LOG_LINK_EVENTS,
            user_mobility_file=USER_MOBILITY_FILE,
            execute_user_mobility=EXECUTE_USER_MOBILITY,
            time_limit_to_packet_generation=TIME_LIMIT_TO_PACKET_GENERATION
        )

        # # Run the SFC_Instance Monitor
        # mn = Simulation_SFC_Instance_Monitor(e1, env, sd, 1000)
        # env.process(mn.run())

        # Create the Master Monitors
        simulation_monitor = Simulation_Monitor(
            edge_environment=e1,
            env=env,
            sd=sd,
            sfc_instance_monitor_interval=SFC_INSTANCE_MONITOR_INTERVAL,
            max_sla_violation_sfc_instance_shared=MAX_SLA_VIOLATION_SFC_INSTANCE_SHARED,
            sfc_instance_monitor_window_size=SFC_INSTANCE_MONITOR_WINDOW_SIZE,
            migration_threshold_percentage=MIGRATION_THRESHOLD_PERCENTAGE,
            migration_threshold_packet_window=MIGRATION_THRESHOLD_PACKET_WINDOW,
            enable_migration=ENABLE_REPLACEMENT,
            scaling=scaling,
            scaling_down=scaling_down
        )

        # Run the Master Monitor
        simulation_monitor.run()

        # Run the Simulation
        sm.run()

        # Destroy the simulation and generate the final logs
        sm.finish_simulation()

        simulation_monitor.stop()

        print("fim")

        # Save the entities
        e1.save_entities_csv(
            file_path="{}/Entities".format(args.path_result_files),
            log_link_entity=LOG_LINK_ENTITY
        )

        # After the execution of the simulation save the data
        sd.save_events_csv(
            edge_environment=e1,
            sm=sm,
            file_path=exp_path
        )

        # Print the entities
        if args.list:
            print("**************")
            print("List Environment Entities")
            print("**************")
            User.list(e1.users)
            VNF.list(e1.vnfs)
            Node.list(e1.nodes)
            SFC.list(e1.sfcs)
            SFC_Request.list(e1.sfc_requests)
            Data_Source.list(e1.data_sources)
            # Link.list(e1.links)

            print("**************")
            print("List Simulation Entities")
            print("**************")
            SFC_Request.list(e1.sfc_requests)
            SFC_Instance.list(e1.sfc_instances)
            VNF_Instance.list((e1.vnf_instances))

            Packet.list(sm.packets)

        # Save the process time for each round
        file = open('{}/process_time.txt'.format(exp_path), 'w')
        file.write("{}".format(time.time() - start_time))
        file.close()

if __name__ == "__main__":
    main()

