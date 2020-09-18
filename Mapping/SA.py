import os
# import sys
# import numpy as np
from copy import deepcopy
from random import sample, random, randint
import math

class SA:
    T = 1e5
    T_min = 1e-5
    alpha = 0.98
    max_time = 1e6

    def __init__(self, if_graph_path, arch_arg):
        self.arch_arg = arch_arg
        with open(if_graph_path, "r") as f:
            if_graph = [eval(line) for line in f]
            srcs, dsts, vols = zip(*if_graph)
            self.comm_graph = {sd: vol for sd, vol in zip(zip(srcs, dsts), vols)}
        self.nodes = list(set(srcs + dsts))
        n = self.arch_arg["n"]
        self.labels = {node: -1 for node in self.nodes}
        self.asgn_labels = {i: -1 for i in range(n)}

    def execute(self):
        temprature = self.T
        cnt = 0
        self.__initLabels()
        min_consp = self.__consumption(self.labels)
        while temprature > self.T_min and cnt < self.max_time:
            new_lables, _ = self.__disturbance(deepcopy(self.labels), deepcopy(self.asgn_labels))
            new_consp = self.__consumption(new_lables)
            delta_E = (new_consp - min_consp)
            if self.__judge(delta_E):
                min_consp = new_consp
            if delta_E < 0:
                temprature = temprature * self.alpha
            else:
                cnt += 1
        print("labels: ", self.labels)
        print("score: ", min_consp)
        return self.labels

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

    def __judge(self, delta_E):
        if delta_E < 0:
            return True
        elif math.exp(-delta_E / self.T) > random():
            return True
        else:
            return False


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    sa = SA("sample.txt", {"d": 4, "n": 4 * 4})
    print(sa.execute())
