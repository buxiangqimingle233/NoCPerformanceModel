import sys
sys.path.append(".")
sys.path.append("..")

# from Estimator import path_based
import math
from VirCongManager import VirCongManager


class SFCongManager(VirCongManager):
    '''Small transmission request goes first
        Requests are partitioned into multiple sub-graphs with repect to their volumes
        This manager assumes static average packet size and coefficience.
        If you want to employ this manager, please specify "cv_A" and "pkt_size" field in your
        configuration, errors will be raised otherwise.
        Transmission rates in G_R are # of flits per cycle
    '''
    scale = 1

    def __init__(self):
        print("Log: Small-First-Congestion-Manager has been initialized")

    def setTask(self, task):
        if "cv_A" not in task or "pkt_size" not in task:
            raise Exception("Please specify 'cv_A' and 'pkt_size' fields")
        self.task = task
        return self

    def doInjection(self, task, arch_arg):
        self.setTask(task)
        G = self.task["G"]
        G.sort(key=lambda x: x[-1])
        partition = self.__partition()
        sub_graphs = [G[p[0]: p[1]] for p in partition]
        ijct_vols = list(map(lambda g: [r[-1] for r in g], sub_graphs))
        ijct_rates = list(map(lambda g: [self.scale * v / sum(g) for v in g], ijct_vols))
        ijct_graphs = []
        for subg, rate in zip(sub_graphs, ijct_rates):
            ijctg = {
                "G_R": [(p[0], p[1], r) for p, r in zip(subg, rate)]
            }
            ijctg["G_V"] = subg
            ijctg["cv_A"], ijctg["l"] = self.task["cv_A"], self.task["pkt_size"]
            if len(ijctg["G_R"]) == 1:
                ijctg["cv_A"] = 0
            ijct_graphs.append(ijctg)

        return ijct_graphs

    def __partition(self):
        '''Cut the task graph into multiple sub-graphs, which represent an set
        for simutaneously transmitted data
            Return:
                A list of begin and end for each partition: [(begin, end)]
        '''
        alpha = 0.3

        power = alpha
        l_ = len(self.task["G"])
        sep = [0]
        while sep[-1] < l_:
            sep.append(sep[-1] + math.ceil(l_*power))
            power = power * alpha
        sep = [i for i in sep if i > 0 and i < l_]
        begin = [0] + sep
        end = sep + [l_]

        return list(zip(begin, end))


if __name__ == "__main__":
    task_graph = [
        (0, 1, 5),
        (1, 0, 10),
        (5, 6, 10),
        (3, 2, 10)
    ]
    cm = SFCongManager({"G": task_graph, "cv_A": 1, "pkt_size": 16})
    ijct_graphs = cm.doInjection()
    print(ijct_graphs)
