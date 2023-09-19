from enum import IntEnum
from Scaling.RLAgent import ActionType, RLAgent

class AgentInstances(IntEnum):
    THRESHOLD_UP = 1
    THRESHOLD_DOWN = 2
    RESOURCE_DECREMENT = 3

class RLAgentProcessor:
    def __init__(self):
        self.instance = None
        self.instance_type = -1

    def set_instance(self, instance, type):
        if type not in AgentInstances:
            print("RL agent type '" + type + "' unknown.")
            quit()
        self.instance = instance
        self.instance_type = type

    def get_instance(self):
        return {'instance': self.instance, 'type': self.instance_type}

    def act(self, state, parameter, delta):
        if self.instance_type == AgentInstances.RESOURCE_DECREMENT:
            state_label = (RLAgent.get_cpu_occupation_state_label(state[0]),
                           RLAgent.get_host_cpu_availability_state_label(state[1]))
        else:
            state_label = (RLAgent.get_sla_violations_state_label(state[-1]))

        action = self.instance.act(state_label)
        new_parameter = self.__perform_action(action, parameter, delta)

        action_param_update = {'action': action, 'updated_parameter': new_parameter}

        return action_param_update

    def update(self, action, state, next_state):
        if self.instance_type == AgentInstances.RESOURCE_DECREMENT:
            immediate_reward = self.instance.get_immediate_reward(next_state)
            current_state_label = (RLAgent.get_cpu_occupation_state_label(state[0]),
                                   RLAgent.get_host_cpu_availability_state_label(state[1]))
            next_state_label = (RLAgent.get_cpu_occupation_state_label(next_state[0]),
                                RLAgent.get_host_cpu_availability_state_label(next_state[1]))
        else:
            immediate_reward = self.instance.get_immediate_reward([next_state[-1]])
            current_state_label = (RLAgent.get_sla_violations_state_label(state[-1]))
            next_state_label = (RLAgent.get_sla_violations_state_label(next_state[-1]))

        self.instance.update_q_table(current_state_label, action, immediate_reward, next_state_label)

    def __perform_action(self, action, parameter, delta):
        if action == ActionType.ACTION_MAINTAIN:
            return parameter
        if action == ActionType.ACTION_INCREASE:
            return min(1.0, parameter + delta)
        if action == ActionType.ACTION_DECREASE:
            return max(0.0, parameter - delta)
