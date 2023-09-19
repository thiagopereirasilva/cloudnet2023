class SFC_Instance_Monitor:

    """ The packets processed from a SFC_Instance will generate a metric that will define:
    a) If new SFC_Request can be mapped to this SFC_Instance
    b) If some SFC_Request mapped to the SFC_Instance needs to me moved from the SFC_Instance

    The data used for the monitoring if collected from the Simulation_Data object that stores all the
    infos about the packets processing
    """

    def __init__(self, edge_environment, env, sd, monitor_interval = 10, max_sla_violation_sfc_instance_shared = 1, sfc_instance_monitor_window_size = 10, migration_threshold_percentage = 0.8, migration_threshold_packet_window = 10, enable_migration = False):
        """ The definition of the Monitor that will monitor the VNF instances
        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The simulation data object
            monitor_interval (int): The monitoring interval
            max_sla_violation_sfc_instance_shared (int) The max number of packets that violate the SLA
            sfc_instance_monitor_window_size (int): The size of the window that will be used for computing if the SFC Instance can accept more SFC Requests
            migration_threshold_percentage (float): The percentage that represents the migration threshold in relation to the SFC max delay.
            migration_threshold_packet_window (int): Number of last N packets of an SFC Request to be considered during migration threshold comparison.
            enable_migration (bool): Whether migration should be enabled
        """

        self.environment = edge_environment
        self.env              = env
        self.sd               = sd
        self.monitor_interval = monitor_interval
        self.max_sla_violation_sfc_instance_shared = max_sla_violation_sfc_instance_shared
        self.sfc_instance_monitor_window_size = sfc_instance_monitor_window_size
        self.migration_threshold_percentage = migration_threshold_percentage
        self.migration_threshold_packet_window = migration_threshold_packet_window
        self.enable_replacement = enable_migration
        self.sfc_requests_above_migration_threshold = {}

    def run(self):
        """
        The monitoring process
        """
        while True:
            # For each VNF_Instance in the environment execute the monitoring
            start = self.env.now - self.sfc_instance_monitor_window_size

            if start > 0:
                start = 0

            for sfc_instance in self.environment.sfc_instances:
                # Only the alive SFC_Instances 
                if sfc_instance.timeout > 0:
                    if sfc_instance.active:
                        migration_latency_threshold = sfc_instance.sfc.max_latency * self.migration_threshold_percentage
                        #print(self.env.now)
                        sfcs_reqs_above_threshold = self.sd.get_services_above_migration_threshold(sfc_instance, self.migration_threshold_packet_window, migration_latency_threshold)
                        #self.environment.get_sfc_requests_of_sfc_instance(sfc_instance)
                        #print("at", self.env.now, "SFCS above threshold", sfcs_reqs_above_threshold)
                        #for sfc_req in self.environment.get_sfc_requests_of_sfc_instance(sfc_instance):
                        for sfc_req in sfc_instance.sfc_requests:
                            if sfc_req.active:
                            #print(sfc_req.name)
                                if sfc_req.name in sfcs_reqs_above_threshold and sfc_req.name not in self.sfc_requests_above_migration_threshold:
                                    #print(sfc_req.name, "ABOVE threshold!", self.env.now)
                                    self.sd.add_migration_event(
                                        event = self.sd.EVENT_SFC_REQUEST_ABOVE_MIGRATION_THRESHOLD,
                                        time = self.env.now,
                                        sfc_request = sfc_req
                                    )
                                    self.sfc_requests_above_migration_threshold[sfc_req.name] = sfc_req
                                    if(self.enable_replacement and sfc_req.has_user_moved() and not self.environment.is_waiting_placement(sfc_req.name)):
                                        self.environment.add_sfc_request_to_replacement(sfc_req, self.env.now)
                                elif sfc_req.name not in sfcs_reqs_above_threshold and sfc_req.name in self.sfc_requests_above_migration_threshold:
                                    #print(sfc_req.name, "BELOW threshold!", self.env.now)
                                    self.sd.add_migration_event(
                                        event = self.sd.EVENT_SFC_REQUEST_BELOW_MIGRATION_THRESHOLD,
                                        time = self.env.now,
                                        sfc_request = sfc_req
                                    )
                                    del self.sfc_requests_above_migration_threshold[sfc_req.name]
                                    if(self.enable_replacement and self.environment.is_waiting_placement(sfc_req.name)):
                                        self.environment.remove_sfc_request_from_replacement_wait(sfc_req)

                    #self.sfc_requests_above_migration_threshold = sfcs_reqs_above_threshold

                    # data[sfc_instance.name] = self.sd.get_num_packets_ingress_sfc_instance(sfc_instance,start, self.env.now)
                    #@ data[sfc_instance.name] = self.sd.get_num_packets_violated_sla(sfc_instance,start, self.env.now)
                    data_frame_violations = self.sd.get_num_packets_violated_sla(sfc_instance, start, self.env.now)
                    # print(data_frame_violations)
                    # print("---------------")
                    violations = data_frame_violations.shape[0]

                    if violations > self.max_sla_violation_sfc_instance_shared:
                        if sfc_instance.accept_requests == True:
                            sfc_instance.accept_requests = False
                            # Log lock event
                            self.sd.add_sfc_instance_event(
                                event = self.sd.EVENT_SFC_INSTANCE_LOCKED,
                                time = self.env.now,
                                sfc_instance = sfc_instance
                            )
                    # @todo When unblock correctly?????
                    else:
                        # Log lock event
                        if sfc_instance.accept_requests == False:
                            self.sd.add_sfc_instance_event(
                                event = self.sd.EVENT_SFC_INSTANCE_UNLOCKED,
                                time = self.env.now,
                                sfc_instance = sfc_instance
                            )
                            sfc_instance.accept_requests = True

            #for sfc_req in self.sfc_requests_above_migration_threshold.values():
            #    if sfc_req.has_user_moved() and \
            #    not self.environment.is_waiting_placement(sfc_req.name) and self.enable_replacement:
            #        #sfc_req.sfc_instance
            #        self.environment.add_sfc_request_to_replacement(sfc_req)


            # Wait a period to monitoring again
            yield self.env.timeout(self.monitor_interval)
