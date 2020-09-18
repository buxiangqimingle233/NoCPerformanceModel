import AddPath
import numpy as np
from VirCongManager import VirCongManager
from Util import XYRouting as RS


class MUCongManager(VirCongManager):
    scale = 1

    def __init__(self):
        print("Log: MU Congestion Manager has been initialized")
        self.cache = {}

    def doInjection(self, task_arg, arch_arg):
        self.__setTaskArch(task_arg, arch_arg)
        self.__forwardPropagation()
        self.__backwardPropagation()
        ret = [{
            "G_V": task_arg["G"],
            "G_R": [(key[0], key[1], val) for key, val in self.cache["G_R"].items()],
            "l": 16,
            "cv_A": 0
        }]          # we have only one graph now
        return ret

    def __setTaskArch(self, task_arg, arch_arg):
        self.task_graph = task_arg["G"]
        self.arch_arg = arch_arg
        d = arch_arg["d"]
        self.cache["vst_cnt"] = np.zeros(4 * d**2 - 4 * d).astype("int16")
        self.cache["rvs_ptr"] = [[] for i in range(len(self.cache["vst_cnt"]))]
        self.rter = RS.XYRouting(self.arch_arg)

    def __forwardPropagation(self):
        packed_path = self.rter.packedPath(self.task_graph)
        self.cache["packed_path"] = packed_path
        vst_cnt = self.cache["vst_cnt"]
        for sd, path in packed_path.items():
            channels = [self.rter.rc2c(r, oc) for r, ic, oc in path[: -1]]
            vst_cnt[channels] += 1
            rvs_ptr = self.cache["rvs_ptr"]
            for c in channels:
                rvs_ptr[c].append(sd)

    def __backwardPropagation(self):
        packed_path = self.cache["packed_path"]
        vst_cnt = self.cache["vst_cnt"]
        rvs_ptr = self.cache["rvs_ptr"]

        G_R = {sd: 0 for sd in packed_path}
        remain = np.ones(len(vst_cnt)).astype("float64")
        for step in range(np.max(vst_cnt), 0, -1):
            channels = np.where(vst_cnt == step)
            for ch in list(channels[0]):
                ratio = remain[ch] / (len(rvs_ptr[ch]) + 1e-10)
                for sd in rvs_ptr[ch]:
                    G_R[sd] = ratio
                    passingby = [self.rter.rc2c(r, oc) for r, ic, oc in packed_path[sd][: -1]]
                    remain[passingby] -= ratio
                    for c in passingby:
                        if c != ch:      # To avoid removing items from the list we're iterating now
                            rvs_ptr[c].remove(sd)
                rvs_ptr[ch].clear()

        self.cache["G_R"] = G_R


if __name__ == "__main__":
    cm = MUCongManager()
    print(cm.doInjection({"G": [(0, 2, 3), (3, 2, 4), (1, 2, 5)]}, {"d": 4}))
