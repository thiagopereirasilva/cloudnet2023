from Simulation_Entities.SFC_Request import SFC_Request


class Simulation_SDN_Controller:
  """ This file is just a simulation of an SDN Controller. This module is used in our simulation to find 
  who is the next instance mapped with the next VNF for a SFC pipeline.

  S_0 ----> V_1 ----> V_2 ----> V_3

  instances 1.1 -----> 2.2 ----> 3.1

  in this example the SDN_Controller will find that the instance that is in charge for processing 
  packets arrived in the V_2 of S_0 will be processed by 2.2

  """
  def __init__(self, environment):
    self.environment = environment

  def get_vnf_instance(self, sfc_request, vnf_name):
    """Find the instance that is responsible for a VNF_Instance mapped with the VNF of a SFC 
    for a specific user 

    Args:
        sfc_request (SFC_Request) the request where the packet where generated
        vnf_name (str): The VNF Type name
    """
    #for sfc_instance in self.environment.sfc_instances:
      # What SFC_Instance were mapped for the SFC_Request
     # if sfc_request.name in sfc_instance.sfc_requests:
        # Find the VNF_Instances that were mapped from the SFC_Instance
    for vnf_instance in self.environment.vnf_instances:
      if vnf_instance.vnf.name == vnf_name and sfc_request.sfc_instance.name in vnf_instance.sfc_instances:
        return vnf_instance

    return False

  def get_next_vnf_instance(self, sfc_request, vnf_name):
    """Find what is the next instance where the dataflow must go after be processed for a VNF in a SFC_Request

      If there is not a next it means that the SFC finished

    Args:
        sfc_request (SFC_Request) the request where the packet where generated
        vnf_name (str): The VNF Type name

    Returns:
        [Instance]: the instance that will receive the dataflow
    """    
    sfc = sfc_request.sfc
    next_vnf = False
    try:
      for i, item in enumerate(sfc.vnfs):
        if item == vnf_name:
            next_vnf = sfc.vnfs[i + 1]
            break
    except IndexError:
      return False

    return self.get_vnf_instance(sfc_request, next_vnf)
