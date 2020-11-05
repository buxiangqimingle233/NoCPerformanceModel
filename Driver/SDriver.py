import sys
import os
import importlib
import argparse
import json

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root)
sys.path.append(root + "/Driver")
sys.path.append(root + "/Estimator")
sys.path.append(root + "/CongManager")
sys.path.append(root + "/Util")
sys.path.append(root + "/Default")


class Driver():

    def __init__(self):
        print("log: Employ SDriver.")

    def execute_mem(self, task_graph, usr_config_path, arch_config_path, should_print):
        if not hasattr(self, "arch_arg"):
            self.__loadConfigs(usr_config_path, arch_config_path)
        self.task_arg["G"] = task_graph
        self.__rectangle2Square()
        self.__loadClass()
        ret = self.do_execution(should_print)
        self.__resetArch()
        return ret

    def execute(self, task_graph_path, usr_config_path, arch_config_path, should_print):
        self.__loadConfigs(usr_config_path, arch_config_path)
        self.__loadTaskGraph(task_graph_path)
        self.__rectangle2Square()
        self.__loadClass()
        ret = self.do_execution(should_print)
        self.__resetArch()
        return ret

    def do_execution(self, should_print):
        sub_tasks = self.cong_manager.doInjection(self.task_arg, self.arch_arg)
        total_latency = 0
        for task in sub_tasks:
            # task lasting time
            width = self.arch_arg["w"]
            inject_latency = [req_v[2] / (req_r[2] * width) for req_v, req_r in zip(task["G_V"], task["G_R"])]
            transmission_latency = self.estimator.calLatency(task, self.arch_arg)
            latency = [i + j for i, j in zip(inject_latency, transmission_latency)]
            inject_ratio = [i / j for i, j in zip(inject_latency, latency)]
            if False in [i > 0 for i in transmission_latency]:
                raise Exception("Negative transmission latency occurs!!!")
            max_idx = latency.index(max(latency))
            if should_print:
                print("\n -------------------- Estimation Result -----------------------\n")
                # print("     Injection task: ", task)
                print("     Injection Time: {} ...".format(inject_latency[:5]))
                print("     Tansmission Time: {} ...".format(transmission_latency[:5]))
                print("     Overall Time: {}, ratio of injection time: {}, injection time: {}, transmission time: {}"
                    .format(latency[max_idx], inject_ratio[max_idx], inject_latency[max_idx], transmission_latency[max_idx]))
                total_latency += latency[max_idx]
        return total_latency

    def __loadClass(self):
        # load classes estimator and congestion manager
        est_module = importlib.import_module(
            "Estimator." + self.usr_config["prj_arg"]["Estimator"])
        cm_module = importlib.import_module(
            "CongManager." + self.usr_config["prj_arg"]["CongManager"])
        self.est_class = est_module.__getattribute__(self.usr_config["prj_arg"]["Estimator"])
        self.cm_class = cm_module.__getattribute__(self.usr_config["prj_arg"]["CongManager"])
        self.cong_manager = self.cm_class()
        self.estimator = self.est_class()

    def __loadTaskGraph(self, task_graph_path):
        # load communication graph specified by "task_arg.path"
        task_graph = []
        # passed arguments first
        if task_graph_path == "":
            full_task_graph_path = root + "/" + self.usr_config["task_arg"]["path"]
        else:
            full_task_graph_path = root + "/" + task_graph_path
        with open(full_task_graph_path, "r") as f:
            for line in f:
                task_graph.append(line.split(","))
        task_graph = [(int(r[0]), int(r[1]), float(r[2])) for r in task_graph]
        self.task_arg["G"] = task_graph

        # # set task graph assignment
        # self.task_arg.update(self.usr_config["task_arg"])
        # # set user architecture assignment
        # self.arch_arg.update(self.usr_config["arch_arg"])
        return task_graph

    def __loadConfigs(self, usr_config_path, arch_config_path):
        full_usr_config_path = root + "/" + usr_config_path
        full_arch_config_path = root + "/" + arch_config_path
        # read the configuration file
        if not os.path.exists(full_usr_config_path):
            raise Exception("Invalid configuration path!")
        with open(full_usr_config_path, "r") as f:
            self.usr_config = json.load(f)
        # default configuration
        with open(full_arch_config_path, "r") as af:
            self.arch_arg = json.load(af)
        with open(root + "/Default/dft_task.json", "r") as tf:
            self.task_arg = json.load(tf)

    def __rectangle2Square(self):
        '''Transform indices of PEs in rectangle [(d + 1) x d] to squares [(d + 1) x (d + 1)]
        '''
        d, n = self.arch_arg['d'], self.arch_arg['n']
        task_graph = self.task_arg['G']
        print("\nLog: Change the shape of PE array, from {} x {} to {} x {}"
              .format(d, d + 1, d + 1, d + 1))
        print("\nWarn: Transform latency estimation is carried out on the {} x {} array"
              .format(d + 1, d + 1))

        def Tf(a):
            return a + a // d
        self.task_arg['G'] = [(Tf(req[0]), Tf(req[1]), req[2]) for req in task_graph]
        self.arch_arg['d'] = d + 1
        self.arch_arg['n'] = (d + 1)**2
        return task_graph, d, n

    def __resetArch(self):
        self.arch_arg['d'] = self.arch_arg['d'] - 1
        self.arch_arg['n'] = self.arch_arg['d']**2

if __name__ == "__main__":
    os.chdir(root)
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Relative path for task graph e.g. Data/sample.txt")
    parser.add_argument("-uc", help="Relative path for user configuration file e.g. Configuration/baseline.json")
    parser.add_argument("-ac", help="Relative path for architecture configuration, e.g. Default/dft_task.json")
    args = parser.parse_args()
    driver = Driver()
    driver.execute(args.i, args.uc, args.ac, True)
