import os
import sys
# import numpy as np
from copy import deepcopy
from random import sample, random, randint
import argparse
import math
import json

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root)
sys.path.append(root + "/Driver")

from Driver.SDriver import Driver


class SA:
    '''Simulated Annealing Algorithm for Task Mapping Problem
        Input:
            if_graph: with format as (src, dst, vol), which could be read directly
                from communication graph generated by
    '''
    T = 1e5
    T_min = 1       # FIXME: 为了快改的
    alpha = 0.98
    global_epc_limit = 1e6
    local_epc_limit = 100

    def __init__(self):
        print("log: Employing SA for searching mapping stratey")
        super().__init__()
        self.estimate_driver = Driver()

    def execute(self, task_graph_path, comm_graph_path, arch_config_path):
        self.task_graph_path = task_graph_path
        self.comm_graph_path = comm_graph_path
        self.arc_config_path = arch_config_path

        self.__readData(comm_graph_path, arch_config_path)
        temperature = self.T
        overall_counter = 0
        self.__initLabels()
        min_consp = self.__consumption(self.labels)
        print("\n -------------- Task Mapping ---------------\n")
        while temperature > self.T_min and overall_counter < self.global_epc_limit:
            for i in range(self.local_epc_limit):
                try:
                    new_lables, new_asgn_labels = self.__disturbance(deepcopy(self.labels), deepcopy(self.asgn_labels))
                    new_consp = self.__consumption(new_lables)
                    delta_E = (new_consp - min_consp) / (min_consp + 1e-10) * 100
                    if self.__judge(delta_E, temperature):
                        min_consp = new_consp
                        self.labels, self.asgn_labels = new_lables, new_asgn_labels
                    if delta_E < 0:     # have found a better solution
                        break
                except Exception:
                    pass
            temperature = temperature * self.alpha
            overall_counter += 1
            if overall_counter % 100 == 0:
                print("episode: {}, present consumption: {}, temperature: {}".format(overall_counter, min_consp, temperature))
        print("labels: ", self.labels)
        print("score: ", min_consp)

        # FIXME: 实验设置
        # self.labels = {i: i for i in range(len(self.labels))}

        task_graph = self.__label2TaskGraph(self.labels)
        self.__writeTaskGraph(task_graph_path, task_graph)
        # self.__writeTaskGraph(task_graph_path, comm_graph_path)
        return task_graph

    def __readData(self, comm_graph_path, arch_config_path):
        arch_arg = self.__readArchConfig(arch_config_path)
        whole_comm_graph = self.__readCommGraph(comm_graph_path)

        comm_graph_between_pe = [req for req in whole_comm_graph if req[0] != -1]
        srcs, dsts, vols = zip(*comm_graph_between_pe)
        self.comm_graph_between_pe = {sd: vol for sd, vol in zip(zip(srcs, dsts), vols)}
        self.nodes = list(set(srcs + dsts))
        self.labels = {node: -1 for node in self.nodes}
        n = arch_arg["n"]
        self.asgn_labels = {i: -1 for i in range(n)}

        comm_graph_with_mem = [req for req in whole_comm_graph if req[0] == -1]
        msrcs, mdsts, mvols = zip(*comm_graph_with_mem)
        self.comm_graph_with_mem = {sd: vol for sd, vol in zip(zip(msrcs, mdsts), mvols)}

    def __initLabels(self):
        n = self.arch_arg["n"]
        for node in self.nodes:
            label = randint(0, n - 1)
            while self.asgn_labels[label] != -1:
                label = randint(0, n - 1)
            self.labels[node] = label
            self.asgn_labels[label] = node

    def __disturbance(self, labels, asgn_labels):
        l1, l2 = sample(asgn_labels.keys(), 2)
        while asgn_labels[l1] == -1 and asgn_labels[l2] == -1:      # 避免交换两个空的label
            l2, l2 = sample(asgn_labels.keys(), 2)
        try:
            labels[asgn_labels[l1]], labels[asgn_labels[l2]] = l2, l1
        except KeyError:
            pass
        asgn_labels[l1], asgn_labels[l2] = asgn_labels[l2], asgn_labels[l1]     # swap assigned labels
        return labels, asgn_labels

    def __consumption(self, labels):
        d = self.arch_arg["d"]
        consp = 0
        task_graph = self.__label2TaskGraph(labels)
        self.__writeTaskGraph(self.task_graph_path, task_graph)
        consp = self.estimate_driver.execute(self.task_graph_path, "Configuration/baseline.json", self.arc_config_path, False)
        # for req1, req2 in zip(task_graph[:-1], task_graph[1:]):
        #     src1, dst1, src2, dst2 = req1[0], req1[1], req2[0], req2[1]
        #     (src1_x, src1_y), (dst1_x, dst1_y), (src2_x, src2_y), (dst2_x, dst2_y) = \
        #         map(lambda x: (x // d, x % d), (src1, dst1, src2, dst2))
        #     coincidence = min(abs(src1_x - dst1_x), abs(src2_x - dst2_x)) if src1_y == src2_y else 0
        #     coincidence += min(abs(src1_y - dst1_y), abs(src2_y - dst2_y)) if src1_x == src2_x else 0
        #     consp += coincidence * (req1[2] + req2[2])
        return consp

    def __judge(self, delta_E, tempreature):
        if delta_E < 0:
            return True
        elif math.exp(-delta_E / tempreature) > random():
            return True
        else:
            return False

    def __label2TaskGraph(self, labels):
        '''Translate transmission requests between PEs according to labels
        Assign access to memory with multi banks in a round-roubin style, represented by the last row of PE array
        '''
        L = labels
        comm_graph_with_mem, comm_graph_between_pe = self.comm_graph_with_mem, self.comm_graph_between_pe
        task_graph_between_pe = [
            (L[src], L[dst], comm_graph_between_pe[(src, dst)])
            for src, dst in comm_graph_between_pe
        ]
        d = self.arch_arg["d"]      # TODO: bank 与边长相同
        bias = self.arch_arg["n"]
        mapped_bank = [i % d + bias for i in range(len(comm_graph_with_mem))]
        task_graph_with_mem = [
            (mb, L[dst], comm_graph_with_mem[(src, dst)])
            for mb, (src, dst) in zip(mapped_bank, comm_graph_with_mem)
        ]
        task_graph = task_graph_between_pe + task_graph_with_mem
        return task_graph

    def __readCommGraph(self, comm_graph_path):
        full_comm_graph_path = root + "/" + comm_graph_path
        with open(full_comm_graph_path, "r") as f:
            comm_graph = [eval(line) for line in f]
        self.comm_graph_with_mem = comm_graph
        return comm_graph

    def __readArchConfig(self, arch_config_path):
        full_arch_config_path = root + "/" + arch_config_path
        if not os.path.exists(full_arch_config_path):
            raise Exception("Invalid configuration path!")
        with open(full_arch_config_path, "r") as f:
            self.arch_arg = json.load(f)
        return self.arch_arg

    def __writeTaskGraph(self, task_graph_path, task_graph):
        full_task_graph_path = root + "/" + task_graph_path
        with open(full_task_graph_path, "w") as f:
            for req in task_graph:
                f.write(",".join(str(x) for x in req) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Path for communication graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-o", help="Path for task graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-c", help="Path for architecture configruation.")
    args = parser.parse_args()

    print("\nlog: Searching for mapping strategy",
          "Path for communication graph: " + args.i,
          "Path for task graph:" + args.o,
          "Path for configuration file:" + args.c,
          sep="\n")

    sa = SA()
    sa.execute(args.o, args.i, args.c)
