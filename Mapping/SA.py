import os
# import sys
# import numpy as np
from copy import deepcopy
from random import sample, random, randint
import argparse
import math


class SA:
    '''Simulated Annealing Algorithm for Task Mapping Problem
        Input:
            if_graph: with format as (src, dst, vol), which could be read directly
                from communication graph generated by
    '''
    T = 1e5
    T_min = 1e-2
    alpha = 0.98
    global_epc_limit = 1e6
    local_epc_limit = 100

    def __init__(self, if_graph, arch_arg):
        print("log: Employing SA for searching mapping stratey")
        self.arch_arg = arch_arg
        n = self.arch_arg["n"]
        srcs, dsts, vols = zip(*if_graph)
        self.comm_graph = {sd: vol for sd, vol in zip(zip(srcs, dsts), vols)}
        self.nodes = list(set(srcs + dsts))
        self.labels = {node: -1 for node in self.nodes}
        self.asgn_labels = {i: -1 for i in range(n)}

    def execute(self):
        temperature = self.T
        overall_counter = 0
        self.__initLabels()
        min_consp = self.__consumption(self.labels)
        while temperature > self.T_min and overall_counter < self.global_epc_limit:
            for i in range(self.local_epc_limit):
                new_lables, new_asgn_labels = self.__disturbance(deepcopy(self.labels), deepcopy(self.asgn_labels))
                new_consp = self.__consumption(new_lables)
                delta_E = (new_consp - min_consp) / min_consp * 100
                if self.__judge(delta_E, temperature):
                    min_consp = new_consp
                    self.labels, self.asgn_labels = new_lables, new_asgn_labels
                if delta_E < 0:     # have found a better solution
                    break
            temperature = temperature * self.alpha
            overall_counter += 1
            if overall_counter % 100 == 0:
                print("episode: {}, present consumption: {}, temperature: {}".format(overall_counter, min_consp, temperature))
        print("labels: ", self.labels)
        print("score: ", min_consp)

        L = self.labels
        task_graph = [(L[src], L[dst], self.comm_graph[(src, dst)]) for src, dst in self.comm_graph]
        return task_graph

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
        comm_graph = [list(sd) + [self.comm_graph[sd]] for sd in self.comm_graph]
        for req1, req2 in zip(comm_graph[:-1], comm_graph[1:]):
            src1, dst1, src2, dst2 = \
                labels[req1[0]], labels[req1[1]], labels[req2[0]], labels[req2[1]]
            (src1_x, src1_y), (dst1_x, dst1_y), (src2_x, src2_y), (dst2_x, dst2_y) = \
                map(lambda x: (x // d, x % d), (src1, dst1, src2, dst2))
            coincidence = min(abs(src1_x - dst1_x), abs(src2_x - dst2_x)) if src1_y == src2_y else 0
            coincidence += min(abs(src1_y - dst1_y), abs(src2_y - dst2_y)) if src1_x == src2_x else 0
            consp += coincidence * (req1[2] + req2[2])
        return consp

    def __judge(self, delta_E, tempreature):
        if delta_E < 0:
            return True
        elif math.exp(-delta_E / tempreature) > random():
            return True
        else:
            return False


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    org_cwd = os.getcwd()
    os.chdir(root)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Path for communication graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-o", help="Path for task graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-d", type=int, help="Diameter of a single dimension")
    args = parser.parse_args()

    print("log: Searching for mapping strategy \
        Path for communication graph: {}  Path for task graph: {}  \
        Diameter: {}".format(args.i, args.o, args.d))

    with open(args.i, "r") as f:
        if_graph = [eval(line) for line in f]
    d = args.d if hasattr(args, "d") else 4

    sa = SA(if_graph, {"d": d, "n": d * d})
    task_graph = sa.execute()

    with open(args.o, "w") as f:
        for req in task_graph:
            f.write(",".join(str(x) for x in req) + "\n")

    os.chdir(org_cwd)
