import random
import numpy as np
from collections import defaultdict
import dill as pickle
import os
from enum import IntEnum

class CPUOccupation(IntEnum):
    CPU_OCCUPATION_VERY_HIGH = 1
    CPU_OCCUPATION_HIGH = 2
    CPU_OCCUPATION_LOW = 3
    CPU_OCCUPATION_VERY_LOW = 4

class HostAvailability(IntEnum):
    HOST_CPU_AVAILABILITY_VERY_HIGH = 1
    HOST_CPU_AVAILABILITY_HIGH = 2
    HOST_CPU_AVAILABILITY_LOW = 3
    HOST_CPU_AVAILABILITY_VERY_LOW = 4

class SLAViolations(IntEnum):
    SLA_VIOLATIONS_VERY_HIGH = 1
    SLA_VIOLATIONS_HIGH = 2
    SLA_VIOLATIONS_LOW = 3
    SLA_VIOLATIONS_VERY_LOW = 4

class ActionType(IntEnum):
    ACTION_MAINTAIN = 0
    ACTION_INCREASE = 1
    ACTION_DECREASE = 2

class RLAgent():
     # def __init__(self, env, vnf_instances, state_space, action_space, weight_list, exploration_min, exploration_max,
    #              exploration_decay, discount_factor):
    def __init__(self, vnf_name, weight_list, exploration_min, exploration_max, exploration_decay, discount_factor):
        # self.env = env
        # self.vnf_instances = vnf_instances
        #
        # self.state_state = state_space
        self.action_space = len(ActionType)
        self.agent_name = vnf_name

        self.q_table = defaultdict(lambda: np.zeros(self.action_space))
        self.weight_list = weight_list

        self.exploration_min = exploration_min
        self.exploration_max = exploration_max
        self.exploration_decay = exploration_decay
        self.exploration_rate = exploration_max

        self.discount_factor = discount_factor

    def update_exploration_rate(self):
        self.exploration_rate *= self.exploration_decay
        self.exploration_rate = max(self.exploration_rate, self.exploration_min)

    def update_q_table(self, state_label, action, immediate_reward, next_state_label):
        best_next_action = np.argmax(self.q_table[next_state_label])
        td_target = immediate_reward + self.discount_factor * self.q_table[next_state_label][best_next_action]
        td_delta = td_target - self.q_table[state_label][action]
        self.q_table[state_label] += td_delta

    def get_q_table_value(self, state_label, action):
        return self.q_table[state_label][action]

    def get_immediate_reward(self, next_state):
        # cpu_occupation, host_cpu_availability, sla_violation = next_state[0], next_state[1], next_state[2]
        reward = 0

        for weight, feature in zip(self.weight_list, next_state):
            # if feature == 0.0:
                # reward += weight
            # else:
            reward += weight * feature

        # reward = (self.weight_list[0] * (1/cpu_occupation)) + (self.weight_list[1] * (1/host_cpu_availability))

        return reward

    def act(self, state_label):
        if random.random() < self.exploration_rate:
            action = random.randint(0, self.action_space - 1)
        else:
            action = np.argmax(self.q_table[state_label])

        self.update_exploration_rate()
        return action

    def save_agent(self, path):
        # with open(path + "rl_agent_state-" + self.agent_name + ".pkl", "wb") as f:
        #     pickle.dump(self.q_table, f)
        pass

    def load_agent(self, path):
        # file_name = path + "rl_agent_state-" + self.agent_name + ".pkl"
        # if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        #     with open(path + "rl_agent_state-" + self.agent_name + ".pkl", "rb") as f:
        #         self.q_table = pickle.load(f)
        pass

    @staticmethod
    def get_cpu_occupation_state_label(cpu_occupation):
        if cpu_occupation < 0.25:
            return CPUOccupation.CPU_OCCUPATION_VERY_LOW
        elif (cpu_occupation >= 0.25) and (cpu_occupation < 0.5):
            return CPUOccupation.CPU_OCCUPATION_LOW
        elif (cpu_occupation >= 0.5) and (cpu_occupation < 0.75):
            return CPUOccupation.CPU_OCCUPATION_HIGH
        else:
            return CPUOccupation.CPU_OCCUPATION_VERY_HIGH

    @staticmethod
    def get_host_cpu_availability_state_label(host_cpu_availability):
        if host_cpu_availability < 0.25:
            return HostAvailability.HOST_CPU_AVAILABILITY_VERY_LOW
        elif (host_cpu_availability >= 0.25) and (host_cpu_availability < 0.5):
            return HostAvailability.HOST_CPU_AVAILABILITY_LOW
        elif (host_cpu_availability >= 0.5) and (host_cpu_availability < 0.75):
            return HostAvailability.HOST_CPU_AVAILABILITY_HIGH
        else:
            return HostAvailability.HOST_CPU_AVAILABILITY_VERY_HIGH

    @staticmethod
    def get_sla_violations_state_label(sla_violations):
        if sla_violations < 0.25:
            return SLAViolations.SLA_VIOLATIONS_VERY_LOW
        elif (sla_violations >= 0.25) and (sla_violations < 0.5):
            return SLAViolations.SLA_VIOLATIONS_LOW
        elif (sla_violations >= 0.5) and (sla_violations < 0.75):
            return SLAViolations.SLA_VIOLATIONS_HIGH
        else:
            return SLAViolations.SLA_VIOLATIONS_VERY_HIGH

    @staticmethod
    def get_action_label(action):
        if action == 0:
            return ActionType.ACTION_MAINTAIN
        elif action == 1:
            return ActionType.ACTION_INCREASE
        else:
            return ActionType.ACTION_DECREASE
