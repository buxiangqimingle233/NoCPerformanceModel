from dim import Dim


class DimTable():

    def __init__(self):
        self.dim_list = []
        self.comm_graph = []

    def hasDim(self, name):
        return self.findDim(name) is not None

    def findDim(self, name):
        for dim in self.dim_list:
            if dim.name == name:
                return dim
        return None

    def findDims(self, names):
        ret = [self.findDim(name) for name in names]
        ret = [item for item in ret if item is not None]
        return ret

    def findDimReturnIndex(self, name):
        for i in range(len(self.dim_list)):
            if self.dim_list[i].name == name:
                return i
        return None
    
    def insertDim(self, dim, index):
        self.dim_list.insert(index, dim)
        return self

    def appendDim(self, dim):
        self.dim_list.append(dim)
        return self

    def updateDim(self, dim):
        for i in range(len(self.dim_list)):
            if self.dim_list[i].getName() == dim.getName():
                self.dim_list[i] = dim
        return self

    def getDimList(self):
        return self.dim_list


if __name__ == "__main__":
    config = {"PE_num": 4}
    dim_X = Dim(1, "X", 16, 6, 1, 3, 1)
    dim_Y = Dim(1, "Y", 16, 3, 1, 3, 0)
    dim_X.addRelatedDims(dim_Y)
    dim_Y.addRelatedDims(dim_X)
    dimTable = DimTable()
    dimTable.appendDim(dim_X).appendDim(dim_Y)
    print(dimTable.genCommGraph(config))
