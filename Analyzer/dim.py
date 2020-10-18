from math import log


class Dim():
    '''
        Dimension class for data-centric directives
    '''

    def __init__(self, name, size, map_size=0, map_ofs=0, dis_size=0, dis_ofs=0):
        self.name, self.size, self.map_size, self.map_ofs, self.dis_size, self.dis_ofs  \
            = name, size, map_size, map_ofs, dis_size, dis_ofs
        self.related_dims = []

    def takeStep(self, PENum):
        '''Analyze transmission due to the move of this dimension
                Return:
                    A list of transmission requests induced by taking a step forward of this dimension,
                    which with the type of (source, destination, transmission_volume). Noted that PE gets
                    data from memory when source is -1.
        '''
        if self.map_size != (PENum - 1) * self.dis_ofs + self.dis_size:
            raise Exception("Dimension {} is invalid, with parameters as: \n map_size: {}, map_ofs: {}, dis_size: {}, dis_ofs: {}"
                .format(self.name, self.map_size, self.map_ofs, self.dis_size, self.dis_ofs))
        if self.size < 0:
            raise Exception("Please set all the attributes before calling function 'takeStep'")

        if all([dim.getDisOfs() == 0 for dim in self.related_dims]) and self.dis_ofs == 0:       # 全都是 TM 就可以broadcast了
            self.comm_graph = self.recursiveDoubling(list(range(PENum)), -1, self.map_ofs)

        else:  
            # FIXME: 写优美点！
            # TODO: 记录PE map的index range
            map_size, map_ofs, dis_size, dis_ofs = self.map_size, self.map_ofs, self.dis_size, self.dis_ofs
            idxs = [i for i in range(PENum)]
            for idx in idxs:
                begin_pres = idx * dis_ofs + map_ofs
                end_pres = begin_pres + dis_size
                begin_prev, end_prev = begin_pres - map_ofs, end_pres - map_ofs

                if begin_pres >= map_size:
                    self.addRequest(-1, idx, dis_size)
                elif end_pres > map_size:
                    vol_from_mem = end_pres - map_size
                    vol_from_pe = map_size - begin_pres
                    if begin_pres < end_prev:
                        vol_from_pe -= end_prev - begin_pres
                    self.addRequest(-1, idx, vol_from_mem)
                    self.addRequest(len(idxs) - 1, idx, vol_from_pe)
                else:
                    # 均来自于PE
                    PE1 = begin_pres // dis_ofs
                    if begin_pres % dis_ofs == 0:
                        # 只有一个PE
                        self.addRequest(PE1, idx, dis_size)
                    else:
                        # 有两个PE
                        PE2 = PE1 + 1
                        vol_from_pe2 = end_pres - (map_size + dis_ofs * PE1)
                        vol_from_pe1 = map_size - vol_from_pe2
                        self.addRequest(PE1, idx, vol_from_pe1)
                        self.addRequest(PE2, idx, vol_from_pe2)

        for req in self.comm_graph:
            for dim in self.related_dims:
                req[-1] *= dim.getDisSize()

        self.postProcessing()

        return self.comm_graph

    def recursiveDoubling(self, PE_list, data_source, volume):
        '''Employ recursive doubling for broadcasting
        '''
        size = len(PE_list)
        assert size & (size - 1) == 0   # TODO: 目前只处理2的幂次方
        mask = size - 1
        ret = []
        for sft in range(int(log(size, 2) - 1), -1, -1):
            mask = mask ^ (1 << sft)
            srcs = [PE_list[idx] for idx in range(size)
                if (idx & (1 << sft) == 0) and (idx & mask == 0)]

            dsts = [PE_list[idx] for idx in range(size)
                if (idx & (1 << sft) != 0) and (idx & mask == 0)]

            for src, dst in zip(srcs, dsts):
                ret.append([src, dst, volume])

        ret.append([data_source, 0, volume])
        return ret

    def postProcessing(self):
        # 合并相同的
        temp_dict = {(req[0], req[1]): 0 for req in self.comm_graph}
        for req in self.comm_graph:
            temp_dict[(req[0], req[1])] += req[2]
        self.comm_graph = [(src, dst, vol) for (src, dst), vol in temp_dict.items()]

        # 自己传自己以及传0
        self.comm_graph = [item for item in self.comm_graph if item[0] != item[1] and item[-1] != 0] 

        return self.comm_graph

    def addRequest(self, src, dst, volume):
        if hasattr(self, 'comm_graph'):
            self.comm_graph.append([src, dst, volume])
        else:
            self.comm_graph = [[src, dst, volume]]
        return self

    def addRelatedDims(self, related_dim):
        if isinstance(related_dim, list):
            self.related_dims += related_dim
        else:
            self.related_dims.append(related_dim)
        return self

    def getStepCnt(self):
        return (self.size - self.map_size) / self.map_ofs + 1

    def getRelatedDims(self):
        return self.related_dims

    def getName(self):
        return self.name

    def getMapSize(self):
        return self.map_size

    def getDisSize(self):
        return self.dis_size

    def getDisOfs(self):
        return self.dis_ofs

if __name__ == "__main__":
    dim_X = Dim(1, "X", 16, 6, 1, 3, 1)
    dim_Y = Dim(1, "Y", 16, 3, 1, 3, 0)
    dim_X.addRelatedDims(dim_Y)
    dim_Y.addRelatedDims(dim_X)
    PE_num = 4
    ret = dim_X.takeStep(PE_num)
    print(ret)
