import Edge_Environment
from Simulation_Data import Simulation_Data
from Scaling.Scaling import Scaling


class BasicCPUScaling(Scaling):

    def __init__(self, env, edge_environment, sd, cpu_load_max, cpu_load_min, resource_increment, resource_decrement,
                 monitor_interval, waiting_time_between_scalings_ups):
        """
         The definition of the Scaling algorithm that will scaling up/down the VNF instances
         This Basic_Scaling uses the CPU and memory usage as a threshold
        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The object that log the changes in the simulation
            cpu_load_max (float): The max CPU Usage (percentage) before scaling up
            cpu_load_min (float): The min CPU Usage (percentage) before scaling down
            resource_increment (float): the percentage of cpu increment
            resource_decrement (float): the percentage of cpu decrement

            monitor_interval (int): The interval between the monitors of the VNF Instances
            waiting_time_between_scaling_ups (int): Time that the monitor must wait after a scaling up before monitoring the SFC Instance again
        """
        self.env = env
        self.edge_environment = edge_environment
        self.sd = sd
        self.cpu_increment = float(resource_increment)
        self.cpu_decrement = float(resource_decrement)
        self.cpu_load_max = float(cpu_load_max)
        self.cpu_load_min = float(cpu_load_min)
        self.monitor_interval = int(monitor_interval)
        self.waiting_time_between_scalings_ups = int(waiting_time_between_scalings_ups)

        self.vnf_instance_last_scaling = {} # store the simulation time where the scaling up occurs

    def run(self):
        """
        The monitoring process
        """
        while True:
            # For each VNF_Instance in the environment execute the monitoring
            for vnf_instance in self.edge_environment.vnf_instances:

                # Log monitor event
                sfcs = vnf_instance.sfc_instances
                for sfc in sfcs:
                    for sfc_instance in self.edge_environment.sfc_instances:
                        if sfc_instance.name == sfc:
                            self.sd.add_monitor_event(
                                event=self.sd.EVENT_MONITOR_ACTIVATION,
                                time=self.env.now,
                                sfc_instance=sfc_instance,
                                window_size=self.monitor_interval,
                                monitor_interval=self.monitor_interval
                            )

                if vnf_instance.active:

                    # if there in the dict vnf_instance_last_scaling there is a key for the vnf instance thus
                    # wait the time configure until performe the monitor again
                    if vnf_instance.name in self.vnf_instance_last_scaling:
                        del self.vnf_instance_last_scaling[vnf_instance.name]
                        yield self.env.timeout(self.waiting_time_between_scalings_ups)

                    old_cpu = vnf_instance.cpu
                    # print('load da VNF {} = {}'.format(vnf_instance.name, vnf_instance.get_cpu_load()))
                    if vnf_instance.get_cpu_load() > self.cpu_load_max:

                        self.vnf_instance_last_scaling[vnf_instance.name] = self.env.now

                        cpu_increment = (vnf_instance.cpu * self.cpu_increment)
                        new_cpu = vnf_instance.cpu + cpu_increment
                        if self.scaling_up_cpu(vnf_instance, new_cpu):
                            self.sd.add_scaling_event(
                                event=self.sd.EVENT_SCALING_UP_CPU,
                                time=self.env.now,
                                vnf_instance=vnf_instance,
                                old=old_cpu,
                                new=new_cpu
                            )
                            self.log_sfc_resources(vnf_instance, self.sd.EVENT_SCALING_UP_CPU)

                        else:
                            self.sd.add_scaling_event(
                                event=self.sd.EVENT_SCALING_UP_CPU_FAIL,
                                time=self.env.now,
                                vnf_instance=vnf_instance,
                                old=old_cpu,
                                new=new_cpu
                            )
                            self.log_sfc_resources(vnf_instance, self.sd.EVENT_NO_SCALING_CPU)

                    # Scaling Down - CPU
                    elif vnf_instance.get_cpu_load() < self.cpu_load_min:

                        # if the cpu allocated to the VNF Instance is equal to the VNF Type min cpu required do nothing
                        if vnf_instance.cpu <= vnf_instance.vnf.cpu:
                            self.log_sfc_resources(vnf_instance, self.sd.EVENT_NO_SCALING_CPU)
                            continue

                        cpu_decrement = (vnf_instance.cpu * self.cpu_decrement)
                        new_cpu = vnf_instance.cpu - cpu_decrement

                        # If the new CPU is lower than the min CPU required thus define the new cpu equal to the min
                        if new_cpu < vnf_instance.vnf.cpu:
                            new_cpu = vnf_instance.vnf.cpu

                        if self.scaling_down_cpu(vnf_instance, new_cpu):
                            self.sd.add_scaling_event(
                                event=self.sd.EVENT_SCALING_DOWN_CPU,
                                time=self.env.now,
                                vnf_instance=vnf_instance,
                                old=old_cpu,
                                new=new_cpu
                            )
                            self.log_sfc_resources(vnf_instance, self.sd.EVENT_SCALING_DOWN_CPU)

                        else:
                            self.sd.add_scaling_event(
                                event=self.sd.EVENT_SCALING_DOWN_CPU_FAIL,
                                time=self.env.now,
                                vnf_instance=vnf_instance,
                                old=old_cpu,
                                new=new_cpu
                            )
                            self.log_sfc_resources(vnf_instance, self.sd.EVENT_NO_SCALING_DOWN_CPU)
                    else:
                        self.sd.add_scaling_event(
                            event=self.sd.EVENT_NO_SCALING_CPU,
                            time=self.env.now,
                            vnf_instance=vnf_instance,
                            old=vnf_instance.cpu,
                            new=vnf_instance.cpu
                        )

                        self.log_sfc_resources(vnf_instance, self.sd.EVENT_NO_SCALING_CPU)

            # Wait a period to monitoring again
            yield self.env.timeout(self.monitor_interval)

    def log_sfc_resources(self, vnf_instance, event):
        sfcs = vnf_instance.sfc_instances
        for sfc in sfcs:
            for sfc_instance in self.edge_environment.sfc_instances:
                if sfc_instance.name == sfc:
                    total_cpu, total_mem = self.get_sfc_instance_resources(sfc_instance)

                    self.sd.add_sfc_instance_resources_event(
                        event=event,
                        time=self.env.now,
                        sfc_instance=sfc_instance,
                        old_cpu=total_cpu,
                        new_cpu=total_cpu,
                        old_mem=total_mem,
                        new_mem=total_mem
                    )


    def get_sfc_instance_resources(self, sfc_instance):
        """
        Calc the total resources allocated to the SFC Instance.

        The SFC resources are the sum of the resources of each VNF instance that compose the SFC Instance
        """
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        total_cpu = total_mem = 0
        for vnf_instance in vnf_instances:
            total_cpu += vnf_instance.cpu
            total_mem += vnf_instance.mem
        return total_cpu, total_mem
