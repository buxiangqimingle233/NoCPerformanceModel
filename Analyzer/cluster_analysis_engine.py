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
            comm_graph, comm_graph_fgn = self.genCommGraph(self.size)
            self.comm_graph_cache = (comm_graph, comm_graph_fgn)
        else:
            comm_graph, comm_graph_fgn = self.comm_graph_cache
        # virtual pe index to physical pe index
        begin = self.range[0]
        ret_comm_graph = []
        ret_comm_graph_fgn = []
        for req in comm_graph:
            src = req[0] + begin if req[0] != -1 else -1
            dst = req[1] + begin if req[1] != -1 else -1
            vol = req[2]
            ret_comm_graph.append((src, dst, vol))
        for req_fgn in comm_graph_fgn:
            src = req_fgn[0] + begin if req_fgn[0] != -1 else -1
            dst = req_fgn[1] + begin if req_fgn[1] != -1 else -1
            vol = req_fgn[2]
            ret_comm_graph_fgn.append((src, dst, vol))
        return ret_comm_graph, ret_comm_graph_fgn

    def genCommGraph(self, PE_num):
        # report communication requests
        # TODO: report memory access counts
        dim_list = self.dim_table.getDimList()
        comm_graph = []
        comm_graph_fine_granularity = []
        num_of_iteration = 1

        for dim in dim_list:
            print(dim.toString())

        for dim in dim_list:
            num_of_iteration *= dim.getStepCnt()
            comm_step = dim.takeStep(PE_num)
            comm_graph += [
                (item[0], item[1], item[2] * num_of_iteration)
                for item in comm_step
            ]
            comm_graph_fine_granularity += [
                (item[0], item[1], (item[2], num_of_iteration))
                for item in comm_step
            ]
        self.comm_graph, self.comm_graph_fine_granularity = comm_graph, comm_graph_fine_granularity
        self.__postProcessing()
        return self.comm_graph, self.comm_graph_fine_granularity

    def __postProcessing(self):
        comm_graph, comm_graph_fine_granularity = self.comm_graph, self.comm_graph_fine_granularity
        temp_dict = {(req[0], req[1]): 0 for req in comm_graph}
        temp_dict_fine_granularity = {key: [] for key in temp_dict}
        for req, req_fgn in zip(comm_graph, comm_graph_fine_granularity):
            temp_dict[(req[0], req[1])] += req[2]
            temp_dict_fine_granularity[(req_fgn[0], req_fgn[1])].append(req_fgn[2])

        # 自己传自己以及传0
        comm_graph = [(src, dst, vol) for (src, dst), vol in temp_dict.items()]            
        comm_graph = [item for item in comm_graph if item[0] != item[1] and item[-1] != 0]

        comm_graph_fine_granularity = [(src, dst, vol) for (src, dst), vol in temp_dict_fine_granularity.items()]
        comm_graph_fine_granularity = [item for item in comm_graph_fine_granularity if item[0] != item[1] and item[-1] != []]

        self.comm_graph = comm_graph
        self.comm_graph_fine_granularity = comm_graph_fine_granularity
        return comm_graph, comm_graph_fine_granularity
