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

    def __init__(self, config_name):
        config_path = root + "/" + config_name
        # read the configuration file
        if not os.path.exists(config_path):
            raise Exception("Invalid configuration path!")
        with open(config_path, "r") as f:
            self.usr_config = json.load(f)
        # default configuration
        with open(root + "/Default/dft_arch.json", "r") as af:
            self.arch_arg = json.load(af)
        with open(root + "/Default/dft_task.json", "r") as tf:
            self.task_arg = json.load(tf)

    def execute(self, ig_name):
        self.__loadClass()
        self.__loadData(ig_name)
        sub_tasks = self.cong_manager.doInjection(self.task_arg, self.arch_arg)
        for task in sub_tasks:
            # task lasting time
            width = self.arch_arg["w"]
            InjctLatcy = [req_v[2] / (req_r[2] * width) for req_v, req_r in zip(task["G_V"], task["G_R"])]
            TransLatcy = self.estimator.calLatency(task, self.arch_arg)
            Latency = [i + j for i, j in zip(InjctLatcy, TransLatcy)]
            print(" ------------------------- Seperator ---------------------------")
            # print("     Injection task: ", task)
            print("     Injection Time: {} ...".format(InjctLatcy[:5]))
            print("     Tansmission Time: {} ...".format(TransLatcy[:5]))
            print("     Overall Latency: ", max(Latency))

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

    def __loadData(self, ig_name):
        # set task graph assignment
        self.task_arg.update(self.usr_config["task_arg"])
        # load communication graph specified by "task_arg.path"
        input_graph = []
        # passed arguments first
        if ig_name == "":
            ig_path = root + "/" + self.usr_config["task_arg"]["path"]
        else:
            ig_path = root + "/" + ig_name
        with open(ig_path, "r") as f:
            for line in f:
                input_graph.append(line.split(","))
        input_graph = [(int(r[0]), int(r[1]), float(r[2])) for r in input_graph]
        self.task_arg["G"] = input_graph
        # set user architecture assignment
        self.arch_arg.update(self.usr_config["arch_arg"])


if __name__ == "__main__":
    os.chdir(root)
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", help="Relative path for configuration file \
        e.g. Configuration/baseline.json")
    parser.add_argument("-i", help="Relative path for communication graph \
        e.g. Data/sample.txt")
    args = parser.parse_args()
    driver = Driver(args.c)

    external_ig_path = args.i if args.i is not None else ""
    driver.execute(external_ig_path)
