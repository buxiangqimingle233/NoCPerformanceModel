from dim import Dim


class DimTable():

    def __init__(self, dim_list):
        self.dim_list = dim_list
        self.comm_graph = []

    def genCommGraph(self, config):
        PE_num = config["PE_num"]
        # report communication requests
        # TODO: report memory access counts
        num_of_iteration = 1
        for dim in self.dim_list:
            num_of_iteration *= dim.getStepCnt()
            comm_step = dim.takeStep(PE_num)
            self.comm_graph += [
                (item[0], item[1], item[2]*num_of_iteration)
                for item in comm_step
            ]
        self.postProcessing()
        return self.comm_graph

    def postProcessing(self):
        temp_dict = {(req[0], req[1]): 0 for req in self.comm_graph}
        for req in self.comm_graph:
            temp_dict[(req[0], req[1])] += req[2]
        self.comm_graph = [(src, dst, vol) for (src, dst), vol in temp_dict.items()]

        # 自己传自己以及传0
        self.comm_graph = [item for item in self.comm_graph if item[0] != item[1] and item[-1] != 0]


if __name__ == "__main__":
    config = {"PE_num": 4}
    dim_X = Dim(1, "X", 16, 6, 1, 3, 1)
    dim_Y = Dim(1, "Y", 16, 3, 1, 3, 0)
    dim_X.addRelatedDims(dim_Y)
    dim_Y.addRelatedDims(dim_X)
    dimTable = DimTable([dim_Y, dim_X])
    print(dimTable.genCommGraph(config))
