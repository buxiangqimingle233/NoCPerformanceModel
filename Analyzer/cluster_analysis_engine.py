from dim_table import DimTable
from dim import Dim


class ClusterAnalysisEngine():

    def __init__(self):
        super().__init__()

    def analyzeCluster(self, pe_idx_range, dim_table):
        self.range = pe_idx_range
        self.size = pe_idx_range[1] - pe_idx_range[0]
        self.dim_table = dim_table

        if not hasattr(self, "comm_graph_cache"):
            comm_graph = self.genCommGraph(self.size)
            self.comm_graph_cache = comm_graph
        else:
            comm_graph = self.comm_graph_cache
        # virtual pe index to physical pe index
        begin = self.range[0]
        ret = []
        for req in comm_graph:
            src = req[0] + begin if req[0] != -1 else -1
            dst = req[1] + begin if req[1] != -1 else -1
            vol = req[2]
            ret.append((src, dst, vol))
        return ret

    def genCommGraph(self, PE_num):
        # report communication requests
        # TODO: report memory access counts
        dim_list = self.dim_table.getDimList()
        comm_graph = []
        num_of_iteration = 1
        for dim in dim_list:
            num_of_iteration *= dim.getStepCnt()
            comm_step = dim.takeStep(PE_num)
            comm_graph += [
                (item[0], item[1], item[2]*num_of_iteration)
                for item in comm_step
            ]
        self.comm_graph = self.__postProcessing(comm_graph)
        return self.comm_graph

    def __postProcessing(self, comm_graph):
        temp_dict = {(req[0], req[1]): 0 for req in comm_graph}
        for req in comm_graph:
            temp_dict[(req[0], req[1])] += req[2]
        comm_graph = [(src, dst, vol) for (src, dst), vol in temp_dict.items()]

        # 自己传自己以及传0
        comm_graph = [item for item in comm_graph if item[0] != item[1] and item[-1] != 0]
        return comm_graph

