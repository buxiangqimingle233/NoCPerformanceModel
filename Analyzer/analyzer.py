'''
    Given the path of directive file, generate the task graph and write it to the assigned file.
'''

# cluster-based analysis: 
#   Input: pe physical indecies
#   Output: communication graph in the cluster
from directive import Directive
from directive_table import DirectiveTable
from transformer import Transformer
from cluster_analysis_engine import ClusterAnalysisEngine as Engine

import re
import os
import sys
import argparse
import json

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root)
sys.path.append(root + "/Driver")
sys.path.append(root + "/Estimator")
sys.path.append(root + "/CongManager")
sys.path.append(root + "/Util")
sys.path.append(root + "/Default")


class Analyzer():

    def __init__(self):
        super().__init__()

    def analyze(self, comm_graph_path, directive_path, arch_config_path):
        layers = self.__readDirectiveFile(directive_path)
        arch_config = self.__readArchConfig(arch_config_path)
        transformer = Transformer()
        comm_graph = []
        for layer in layers:
            directive_table, layer_type = layer["directive_table"], layer["layer_type"]
            pe_num = arch_config["n"]
            dim_table, cluster_size = transformer.transform(directive_table, layer_type, pe_num)
            # cluster_num = pe_num // cluster_size
            cluster_indexes = [(begin, begin + cluster_size) for begin in range(0, pe_num, cluster_size)]
            cluster_analysis_engine = Engine()
            for cluster_index_range in cluster_indexes:
                comm_graph += cluster_analysis_engine.analyzeCluster(cluster_index_range, dim_table)
        self.__writeCommGraph(comm_graph_path, comm_graph)
        return comm_graph

    def __readDirectiveFile(self, directive_path):
        full_directive_path = root + "/" + directive_path
        with open(full_directive_path, 'r') as f:
            layers = []
            line = f.readline()
            while line:
                if line.find("Type") != -1:
                    pattern = re.compile(r"Type:\s*([a-z]+)")
                    layer_type = pattern.match(line).group(1)

                    line = f.readline()
                    pattern = re.compile(r"[A-Z]'?:\s*\d+")
                    dim_sizes_l = [tuple(p.split(':')) for p in pattern.findall(line)]
                    dim_sizes = {p[0]: int(p[1]) for p in dim_sizes_l}

                    directive_table = DirectiveTable()
                    # Read directives
                    line = f.readline()
                    while line.find("Type") == -1 and line.find("}") == -1:
                        spl = line.split(",")
                        spl = [s.strip() for s in spl]
                        name, type_, size, ofs = spl[0], spl[1], int(spl[2]), int(spl[3])
                        if name == "CL":
                            directive = Directive(name, type_, size, ofs, size)
                        else:
                            directive = Directive(name, type_, size, ofs, dim_sizes[name])
                        directive_table.appendDirective(directive)
                        line = f.readline()
                    layers.append({"directive_table": directive_table, "layer_type": layer_type})
                    line = f.readline()
                else:
                    raise Exception("Directive syntax error!")
        self.layers = layers
        return layers

    def __readArchConfig(self, arch_config_path):
        full_arch_config_path = root + "/" + arch_config_path
        if not os.path.exists(full_arch_config_path):
            raise Exception("Invalid configuration path!")
        with open(full_arch_config_path, "r") as f:
            self.arch_config = json.load(f)
        return self.arch_config

    def __writeCommGraph(self, comm_graph_path, comm_graph):
        full_comm_graph_path = root + "/" + comm_graph_path
        with open(full_comm_graph_path, "w") as f:   # TODO: 文件未存在的时候应该创建一个
            for req in comm_graph:
                req_ = [i for i in req]
                for i in range(len(req_)):
                    if req_[i] < 0:
                        req_[i] = 0
                if req_[0] == req_[1]:
                    continue
                f.write(",".join(str(x) for x in req_) + "\n")       # FIXME: 这里只是为了跑通，-1该处理还是要处理的


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Path for directives, with the root directory as NoCPerformanceModel")
    parser.add_argument("-o", help="Path for communication graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-c", help="Path for configuration file,  with the root directory as NoCPerformanceModel")
    args = parser.parse_args()
    analyzer = Analyzer()
    comm_graph = analyzer.analyze(args.o, args.i, args.c)
