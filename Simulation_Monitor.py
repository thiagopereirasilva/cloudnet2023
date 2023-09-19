from Monitor.SFC_Instance_Monitor import SFC_Instance_Monitor

class Simulation_Monitor:
    """ Each VNF_Instance is periodically monitored and, if the resources above or below the 
    limits the scaling component will execute the scaling up or down if necessary
    """

    def __init__(self,
                 edge_environment,
                 env,
                 sd,
                 scaling = False,
                 scaling_down = False,
                 sfc_instance_monitor_interval = 10,
                 vnf_instance_monitor_interval = 10,
                 max_sla_violation_sfc_instance_shared = 1,
                 sfc_instance_monitor_window_size = 10,
                 migration_threshold_percentage = 0.8,
                 migration_threshold_packet_window = 10,
                 enable_migration = False):
        """ The definition of the Monitor that will monitor the VNF instances
        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The Simulation Data
            scaling (Scaling): The Scaling Up component
            scaling_down (Scaling): The Scaling Down component
            sfc_instance_monitor_interval (int): The SFC Instance monitoring interval
            vnf_instance_monitor_interval (int): The VNF Instance monitoring interval
            max_sla_violation_sfc_instance_shared (int): The number of packets that can violate the SLA without blocking the SFC Instance for been used for new SFC Requests
            sfc_instance_monitor_window_size (int): The size of the window that will be used for computing if the SFC Instance can accept more SFC Requests
            migration_threshold_percentage (float): The percentage that represents the migration threshold in relation to the SFC max delay.
            migration_threshold_packet_window (int): Number of last N packets of an SFC Request to be considered during migration threshold comparison.
            enable_migration (bool): Whether migration should be enabled
        """
        self.edge_environment = edge_environment
        self.env              = env
        self.sd               = sd
        self.scaling          = scaling
        self.scaling_down     = scaling_down

        self.vnf_instance_monitor_interval = vnf_instance_monitor_interval
        self.sfc_instance_monitor_interval = sfc_instance_monitor_interval
        self.max_sla_violation_sfc_instance_shared = max_sla_violation_sfc_instance_shared
        self.sfc_instance_monitor_window_size = sfc_instance_monitor_window_size
        self.migration_threshold_percentage = migration_threshold_percentage
        self.migration_threshold_packet_window = migration_threshold_packet_window
        self.enable_migration = enable_migration

    def run(self):

        # Run the SFC_Instance Monitor
        sfc_instance_monitor = SFC_Instance_Monitor(
            edge_environment=self.edge_environment,
            env=self.env,
            sd=self.sd,
            monitor_interval=self.sfc_instance_monitor_interval,
            max_sla_violation_sfc_instance_shared=self.max_sla_violation_sfc_instance_shared,
            sfc_instance_monitor_window_size=self.sfc_instance_monitor_window_size,
            migration_threshold_percentage = self.migration_threshold_percentage,
            migration_threshold_packet_window = self.migration_threshold_packet_window,
            enable_migration = self.enable_migration
        )
        self.env.process(sfc_instance_monitor.run())

        # Run the scaling up or the scaling that make the scaling up and down at same time
        if self.scaling:
            self.env.process(self.scaling.run())

        # Run the scaling down
        if self.scaling_down:
            self.env.process(self.scaling_down.run())

    def stop(self):
        if self.scaling:
            self.scaling.stop()
