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
org_cwd = os.getcwd()
os.chdir(root)


class Driver():

    def __init__(self, config_name):        # TODO: Setting default values
        '''
            config_
        '''
        config_path = root + "/Configuration/" + config_name
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

    def execute(self):
        self.__loadClass()
        self.__loadData()
        sub_tasks = self.cong_manager.doInjection(self.task_arg)
        for task in sub_tasks:
            # task lasting time
            width = self.arch_arg["w"]
            duration = task["G"][0][2] / (task["G_R"][0][2] * width)
            T = self.estimator.calLatency(task, self.arch_arg)
            print(duration, T)

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

    def __loadData(self):
        # set task graph assignment
        self.task_arg.update(self.usr_config["task_arg"])
        # load communication graph specified by "task_arg.path"
        input_graph = []
        ig_path = root + "/Data/" + self.usr_config["task_arg"]["path"]
        with open(ig_path, "r") as f:
            for line in f:
                input_graph.append(line.split(","))
        input_graph = [(int(r[0]), int(r[1]), float(r[2])) for r in input_graph]
        self.task_arg["G"] = input_graph
        # set user architecture assignment
        self.arch_arg.update(self.usr_config["arch_arg"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("c", help="Name for configuration file (without the need of full path) \
        e.g. baseline.json")            # TODO: Option arg & default values
    parser.add_argument("--d", help="Name for task graph (without the need of full path)   \
        e.g. sample.txt")   # TODO: 加 path
    args = parser.parse_args()
    driver = Driver(args.c)
    driver.execute()

os.chdir(org_cwd)
