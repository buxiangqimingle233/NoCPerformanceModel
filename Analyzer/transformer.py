from directive_table import DirectiveTable
from dim_table import DimTable
from directive import Directive
from dim import Dim


class Transformer():
    '''Transform data-centric directives to comm-centric directives for a cluster
        Transfrom to wz-regular data-centric directives first
    '''
    def __init__(self):
        super().__init__()

    def transform(self, directive_table, layer_type, pe_num):
        drct_cluster = directive_table.findDirective('CL')
        if len(drct_cluster) == 0:
            cluster_size = pe_num
        else:
            cluster_size = drct_cluster[0].getSize()
        cluster_num = pe_num // cluster_size
        assert cluster_num * cluster_size == pe_num        # 整除

        dim_table = self.analyzeDirectives(directive_table, layer_type, cluster_size, cluster_num)
        dim_table = self.addMissingDims(dim_table, layer_type)
        dim_table = self.setRelatedDims(dim_table, layer_type)

        return dim_table, cluster_size

    def analyzeDirectives(self, directive_table, layer_type, cluster_size, cluster_num):

        dim_table = DimTable()
        if layer_type == "conv":
            directive_before_cluster = directive_table.getDirectiveBeforeCluster()
            directive_after_cluster = directive_table.getDirectiveAfterCluster()

            for directive in directive_before_cluster:
                name = directive.getName()
                if not dim_table.hasDim(name):
                    dim = Dim(name, directive.getDimSize())
                    if directive.getType() == "TM":
                        dim.map_size = directive.getSize()
                        dim.map_ofs = directive.getOfs()
                        dim.dis_size = dim.map_size
                        dim.dis_ofs = 0
                    elif directive.getType() == "SM":
                        dim.map_size = directive.getSize()
                        dim.map_ofs = directive.getOfs() * (cluster_num - 1) + dim.map_size
                        # 默认对PE做broadcast
                        dim.dis_size = dim.map_size
                        dim.dis_ofs = 0
                    dim_table.appendDim(dim)
                else:
                    raise Exception("Dual assignment for a dimension!")

            for directive in directive_after_cluster:
                name = directive.getName()
                if not dim_table.hasDim(name):
                    dim = Dim(name, directive.getDimSize())
                    if directive.getType() == "TM":
                        dim.map_size = directive.getSize()
                        dim.map_ofs = directive.getOfs()
                        dim.dis_size = dim.map_size
                        dim.dis_ofs = 0
                    elif directive.getType() == "SM":
                        dim.map_size = (cluster_size - 1) * directive.getOfs() + directive.getSize()
                        dim.map_ofs = directive.getOfs() * (cluster_size - 1) + dim.map_size
                        dim.dis_size = directive.getSize()
                        dim.dis_ofs = directive.getOfs()
                    dim_table.appendDim(dim)
                else:
                    dim = dim_table.findDim(name)
                    if directive.getType() == "TM":
                        # redundant directives
                        pass
                    elif directive.getType() == "SM":
                        assert dim.map_size == (cluster_size - 1) * directive.getOfs() + directive.getSize()
                        dim.dis_size = directive.getSize()
                        dim.dis_ofs = directive.getOfs()
                    dim_table.updateDim(dim)

        elif layer_type == "fc":
            dim_name_fc = []    # TODO: 添加对FC的支持

        return dim_table

    def addMissingDims(self, dim_table, layer_type):
        '''Add directives for output features
        '''
        # check if all the dimensions are included
        if layer_type == 'conv':
            whole_dim_name_list = ['X', 'Y', 'C', 'X\'', 'Y\'', 'K', 'C', 'R', 'S']
            dim_name_list = [dim.getName() for dim in dim_table.getDimList()]
            if (len(dim_name_list) == len(whole_dim_name_list)):
                return dim_table

            missing_dim_name_list = [dim for dim in whole_dim_name_list if dim not in dim_name_list]
            for d in missing_dim_name_list:
                if d not in ['X\'', 'Y\'']:
                    raise Exception("Warning: These dimensions are not specified by directives!!! {}".format(missing_dim_name_list))

            # TODO: 多层得接起来，现在只做一层的就把output送到mem中
            # FIXME: 在没有stride的前提下，我们无法不知道X'与Y'的ofs，默认ofs=size
            dim_S, dim_X = dim_table.findDim('S'), dim_table.findDim('X')
            dim_R, dim_Y = dim_table.findDim('R'), dim_table.findDim('Y')
            # FIXME: 默认stride为1
            x_comma_size = dim_X.getDisSize() - dim_S.getDisSize() + 1
            y_comma_size = dim_Y.getDisSize() - dim_R.getDisSize() + 1

            # 添加在XY移动的正下方，循环次数为1，因为其实X'与Y'与X和Y是同步移动的，
            if 'X\'' in missing_dim_name_list:
                index_X = dim_table.findDimReturnIndex('X')
                dim_X_comma = Dim('X\'', x_comma_size)
                dim_X_comma.map_size, dim_X_comma.dis_size = x_comma_size, x_comma_size
                dim_X_comma.map_ofs, dim_X_comma.dis_ofs = x_comma_size, 0
                dim_table.insertDim(dim_X_comma, index_X + 1)
            if 'Y\'' in missing_dim_name_list:
                index_Y = dim_table.findDimReturnIndex('Y')
                dim_Y_comma = Dim('Y\'', y_comma_size)
                dim_Y_comma.map_size, dim_Y_comma.dis_size = y_comma_size, y_comma_size
                dim_Y_comma.map_ofs, dim_Y_comma.dis_ofs = y_comma_size, 0
                dim_table.insertDim(dim_Y_comma, index_Y + 1)
        else:
            raise Exception("Unsupported layer type!")

        return dim_table

    def setRelatedDims(self, dim_table, layer_type):
        if layer_type == "conv":
            dim_sets = [
                ['X', 'Y', 'C'],
                ['X\'', 'Y\'', 'K'],
                ['K', 'C', 'R', 'S']
            ]
            for dim in dim_table.getDimList():
                name = dim.getName()
                related_names = [name_set for name_set in dim_sets if name in name_set]
                related_names = [n for names in related_names for n in names if n != name]
                related_dims = dim_table.findDims(related_names)
                dim.addRelatedDims(related_dims)
        else:
            raise Exception("Unsupported layer type yet!")

        return dim_table


if __name__ == "__main__":
    directive_table = DirectiveTable()
    name_list = ['X', 'Y', 'C', 'X\'', 'Y\'', 'K', 'C', 'R', 'S']
    d_K = Directive('K', 'TM', 1, 1, 1)
    d_C = Directive('C', 'SM', 2, 2, 4)
    d_Y = Directive('Y', 'TM', 3, 1, 16)
    d_X = Directive('X', 'TM', 3, 1, 16)
    d_cluster = Directive('CL', 'CL', 2, 2, 2)
    d_C_ = Directive('C', "SM", 1, 1, 2)
    d_R = Directive('R', 'TM', 3, 3, 3)
    d_S = Directive('S', 'TM', 3, 3, 3)
    directive_table.appendDirective(d_K).appendDirective(d_C).appendDirective(d_Y).appendDirective(d_X)   \
        .appendDirective(d_cluster).appendDirective(d_C_).appendDirective(d_R).appendDirective(d_S)

    transformer = Transformer()
    dim_table, _ = transformer.transform(directive_table, 'conv', 4)
    print(dim_table)

    '''
        TemporalMap(1, 1) K;    TM, 1, 1, K
        SpatialMap(1,1) C;
        TemporalMap(Sz(R),1) Y;
        TemporalMap(Sz(S),1) X;
        Cluster(2)
        TemporalMap(Sz(R),Sz(R)) R;
        TemporalMap(Sz(S),Sz(S)) S;
    '''
