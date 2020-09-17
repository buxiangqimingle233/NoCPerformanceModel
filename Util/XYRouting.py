PORT2IDX = {"input": 0, "output": 1, "north": 2, "south": 3, "west": 4, "east": 5}
DIR2PORT = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}


class XYRouting:

    def __init__(self, arch_arg):
        self.arch_arg = arch_arg
        self.cache = {}

    def path(self, task_graph):
        '''Do XY-routing for given task graph
            task_graph: A list of (src, dst, vol)
            Return:
                A list of routed paths for requests in the task graph, where the path is
                given as a list of (router, input channel, output channel)
        '''
        if "pkt_path" in self.cache:
            return self.cache["pkt_path"]
        ret = []
        for rqst in task_graph:
            Router_path = self.__passedRouters(rqst[0], rqst[1])
            Iport_path, Oport_path = self.__passedIOChannels(Router_path)
            Router_path = [cord[1] * self.arch_arg["d"] + cord[0] for cord in Router_path]
            ret.append(list(zip(Router_path, Iport_path, Oport_path)))
        self.cache["pkt_path"] = ret
        return ret

    def packedPath(self, task_graph):
        '''Return routed paths of all requests in task graph handled by assigned routing strategy
        Routing strategy is set as XY routing by default.
            Return:
                A dict with tuples (src, dst) as keys and pkt_path as values
                pkt_path: A list whose factors are tuples of (router, input channel, output channel)
                Noted that both input and output channels are in view of routers, i.e. they're serial numbers of routers' ports.
                You could use zip(*) to get those three path seperately.
        '''
        P = self.path(task_graph)
        ret = {(r[0], r[1]): p for r, p in zip(task_graph, P)}
        return ret

    def __passedRouters(self, src_rt, dst_rt):
        d = self.arch_arg["d"]
        src_x, src_y = int(src_rt % d), int(src_rt // d)      # The 2D coordinate is left-half system
        dst_x, dst_y = int(dst_rt % d), int(dst_rt // d)
        # X routing
        step_x = 1 if src_x < dst_x else -1
        Router_path = [(x, src_y) for x in range(src_x, dst_x, step_x)]
        # Y routing
        step_y = 1 if src_y < dst_y else -1
        Router_path += [(dst_x, y) for y in range(src_y, dst_y, step_y)]
        Router_path += [(dst_x, dst_y)]    # the destination router
        Router_path = list(map(lambda x: (int(x[0]), int(x[1])), Router_path))
        return Router_path

    def __passedIOChannels(self, path):
        Iport_path = [PORT2IDX["input"]]
        Oport_path = []
        for prev, pres in zip(path[:-1], path[1:]):
            op_ = (pres[0] - prev[0], pres[1] - prev[1])
            ip_ = (prev[0] - pres[0], prev[1] - pres[1])
            Iport_path.append(PORT2IDX[DIR2PORT[ip_]])
            Oport_path.append(PORT2IDX[DIR2PORT[op_]])
        Oport_path.append(PORT2IDX["output"])
        return Iport_path, Oport_path

    def pointTo(self, src, oc):
        d = self.arch_arg["d"]
        if oc == PORT2IDX["west"]:
            ret = src - 1
            ic = PORT2IDX["east"]
        elif oc == PORT2IDX["east"]:
            ret = src + 1
            ic = PORT2IDX["west"]
        elif oc == PORT2IDX["north"]:
            ret = src - d
            ic = PORT2IDX["south"]
        elif oc == PORT2IDX["south"]:
            ret = src + d
            ic = PORT2IDX["north"]
        else:
            raise Exception("Invalid output port: router = {}, oc = {}".format(src, oc))
        if src < 0 and src >= d:
            raise Exception("Router exceeded the boundary: router = {}, oc = {}".format(src, oc))
        return ret, ic

    def rc2c(self, r, oc):
        d = self.arch_arg["d"]
        base = (r // d) * (2 * d - 1)
        if oc == PORT2IDX["west"]:
            ret = base + r % d - 1
        elif oc == PORT2IDX["east"]:
            ret = base + r % d
        elif oc == PORT2IDX["north"]:
            ret = base + r % d - d
        elif oc == PORT2IDX["south"]:
            ret = base + r % d + d - 1
        return int(ret)

if __name__ == "__main__":
    r = XYRouting({"d": 4})
    res = r.route([(1, 2, 3), (3, 1, 5)])
    print(res)
