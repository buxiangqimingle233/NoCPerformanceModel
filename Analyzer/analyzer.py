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

class Analyzer():

    def __init__(self):
        super().__init__()

    def analyze(self, directive_path, hardware_config):
        layers = self.readDirectiveFile(directive_path)
        transformer = Transformer()
        comm_graph = []
        for layer in layers:
            directive_table, layer_type = layer["directive_table"], layer["layer_type"]
            pe_num = hardware_config["pe_num"]
            dim_table, cluster_size = transformer.transform(directive_table, layer_type, pe_num)
            # cluster_num = pe_num // cluster_size
            cluster_indexes = [(begin, begin + cluster_size) for begin in range(0, pe_num, cluster_size)]
            cluster_analysis_engine = Engine()
            for cluster_index_range in cluster_indexes:
                comm_graph += cluster_analysis_engine.analyzeCluster(cluster_index_range, dim_table)
        return comm_graph

    def readDirectiveFile(self, directive_path):
        with open(directive_path, 'r') as f:
            layers = []
            line = f.readline()
            while line:
                if line.find("Type") != -1:
                    pattern = re.compile(r"Type:([a-z]+)")
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
                    raise Exception("Logic error!")

        return layers


if __name__ == "__main__":
    analyzer = Analyzer()
    comm_graph = analyzer.analyze(r"F:\Code\NoCPerformanceModel\implementation\Analyzer\test.txt", {"pe_num": 16})
    print(comm_graph)
