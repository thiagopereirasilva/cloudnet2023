from abc import abstractmethod

class Scaling(object):

    def __init__(self, environment, sd):
        self.environment = environment
        self.sd = sd
        super().__init__()

    def scaling_up_cpu(self, vnf_instance, new_cpu):
        """
        Increase the CPU allocated to the VNF instance

        Args:
            vnf_instance (VNF_Instance): The VNF instance
            new_cpu (float): The new CPU value
        """
        new_cpu = round(new_cpu)
        node_resources_available = self.edge_environment.get_node_available_resource(self.edge_environment.vnf_instances, vnf_instance.node.name)
        cpu_demanded = new_cpu - vnf_instance.cpu
        if node_resources_available['cpu'] >= cpu_demanded:
            vnf_instance.cpu = new_cpu
            return True

        # There is not CPU available in the node
        return False


    def scaling_down_cpu(self, vnf_instance, new_cpu):
        """
        Decrease CPU allocated to the VNF instance

        Args:
            vnf_instance (VNF_Instance): The VNF instance
            new_cpu (float): The new cpu value
        """
        new_cpu = round(new_cpu)
        if vnf_instance.vnf.cpu <= new_cpu:
            vnf_instance.cpu = new_cpu
            return True

        return False

    def scaling_up_mem(self, vnf_instance, new_mem):
        """
            Increase memory allocated to the VNF instance
        Args:
            vnf_instance (VNF_Instance): The VNF instance
            new_mem (float): The new mem value
        """
        new_cpu = round(new_mem)
        node_resources_available = self.edge_environment.get_node_available_resource(self.edge_environment.vnf_instances, vnf_instance.node.name)
        mem_demanded = new_mem - vnf_instance.mem
        if node_resources_available['cpu'] >= mem_demanded:
            vnf_instance.mem = new_cpu
            return True

        return False

    def scaling_down_mem(self, vnf_instance, new_mem):
        """
        Decrease Memory allocated to the VNF instance

        Args:
            vnf_instance (VNF_Instance): The VNF instance
            new_mem (float): The new memory value
        """
        new_mem = round(new_mem)
        if vnf_instance.vnf.mem <= new_mem:
            vnf_instance.mem = new_mem
            return True

        return False

    def scaling_down(self, instance):

        """
            Decrease memory and cpu capacity of the VNF instance
        Args:
            instance: The VNF instance
        """
        new_cpu = instance.cpu * self.cpu_unit
        new_mem = instance.mem * self.mem_unit

        basic_cpu = instance.cpu_min_required * 0.8
        basic_mem = instance.mem_min_required * 0.8

        if new_cpu >= basic_cpu and new_mem >= basic_mem:
            instance.set_cpu(new_cpu, self.sd, self.env.now)
            instance.set_mem(new_mem, self.sd, self.env.now)
            self.sd.add_scaling_event(instance, self.t_max, self.t_min, self.sd.EVENT_SCALING_DOWN, self.env.now)

    @abstractmethod
    def stop(self):
        pass
