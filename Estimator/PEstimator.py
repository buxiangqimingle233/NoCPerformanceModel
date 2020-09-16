import copy
from collections import Counter
import numpy as np


PORT2IDX = {"input": 0, "output": 1, "north": 2, "south": 3, "west": 4, "east": 5}
DIR2PORT = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
PINF = 1e5


class PEstimator:
    ''' Estimating average packet latency for a given mesh and communication workload
        Initialize class with two dicts, arch_config and task_config:
            arch_config:
                d: Diameter of the mesh
                n: d**2, # of routers
            task_config:
                G_R: A list denoting task graph, whose factors are (src_rt, dst_rt, trans_rate)
                cv_A: Coefficiency of the packet size
                l: Average packet size
    '''
    arch_arg = {}
    task_arg = {}
    cache = {}

    def __init__(self):
        # Default configuration for on-chip networks
        self.dft_arch = {}
        self.dft_arch["type"] = "mesh"
        self.dft_arch["d"] = 8          # diameter
        self.dft_arch["n"] = 8 * 8      # # of routers
        self.dft_arch["p"] = 6          # # of channels per router (N, S, W, E, I, O)
        self.dft_arch["tr"] = 2         # cycles for arbitration
        self.dft_arch["ts"] = 1         # cycles for switching
        self.dft_arch["tw"] = 1         # cycles for transmitting a flit between two adjacent routers
        self.dft_arch["cp_if"] = 4      # capacity of input buffer (flits)
        self.dft_arch["cp_of"] = 1      # capacity of output buffer (flits)
        self.dft_arch["bw"] = 1         # bandwidth (flits)
        self.dft_arch["w"] = 16         # width of channels(# bits per flit)
        self.arch_arg = copy.deepcopy(self.dft_arch)

        # Default configuration for tasks
        self.dft_task = {}
        self.dft_task["G_R"] = []        # task graph: (src, dst, rate)
        self.dft_task["cv_A"] = 1.00     # average coefficiency of packet size
        self.dft_task["l"] = 64          # average packet size (flits)
        self.task_arg = copy.deepcopy(self.dft_task)

    def calLatency(self, task_arg, arch_arg):
        '''Analyzing latency of each transmission request assigned by task_config
            Return:
                Time: A list of estimated transmission latency of requests expressed by task_arg["G_R"],
                    noted that the two lists are with the same order to indicate the correspondence.
        '''
        self.setTask(task_arg)
        self.setArch(arch_arg)

        # Preprocess the task graph and set up three key tensors: S, S2, W
        self.__preprocess()
        n, p = self.arch_arg["n"], self.arch_arg["p"]
        S = np.zeros((n, p)) + 1e-10    # for getting rid of dividing zeros
        S2 = np.zeros((n, p)) + 1e-10
        W = np.zeros((n, p, p)) + 1e-10
        # Store them
        self.cache["S"], self.cache["S2"], self.cache["W"] = S, S2, W

        # Initialize S and S2
        ts, tw = self.arch_arg["ts"], self.arch_arg["tw"]
        l_, cv_A = self.task_arg["l"], self.task_arg["cv_A"]
        RH = self.cache["RH"]
        lb = (l_ - 1) * max(ts, tw)
        S[RH == 0] = ts + tw + lb
        S2[RH == 0] = (ts + tw + lb)**2 / (cv_A**2 + 1)

        # Initialize W
        self.__updateRouterBlockingTime(0)

        # Calculate blocking time of each router
        max_rh = np.max(RH[RH != PINF])
        for rh in range(1, max_rh + 1):
            self.__updateOCServiceTime(rh)
            self.__updateRouterBlockingTime(rh)
        Time = self.__analyzePktTime()
        return Time

    def getRoutedPath(self):
        '''Return routed paths of all requests in task graph handled by assigned routing strategy
        Routing strategy is set as XY routing by default.
            Return:
                A dict with tuples (src, dst) as keys and pkt_path as values
                pkt_path: A list whose factors are tuples of (router, input channel, output channel)
                Noted that both input and output channels are in view of routers, i.e. they're serial numbers of routers' ports.
                You could use zip(*) to get those three path seperately.
        '''
        if not hasattr(self, "task_arg"):
            raise Exception("Please set task arguments for Estimator first!")
        if not hasattr(self, "arch_arg"):
            raise Exception("Please set architecture arguments for Estimator first!")
        G = self.task_arg["G_R"]
        P = self.__routeTaskGraph()
        ret = {(r[0], r[1]): p for r, p in zip(G, P)}
        return ret

    def setTask(self, task_arg):
        for arg in task_arg:
            self.task_arg[arg] = copy.deepcopy(task_arg[arg])
        self.cache.clear()
        return self

    def setArch(self, arch_arg):
        for arg in arch_arg:
            self.arch_arg[arg] = copy.deepcopy(arch_arg[arg])
        self.cache.clear()
        if self.arch_arg["n"] != self.arch_arg["d"]**2:
            raise Exception("Invalid hardware configuration: d = {}, n = {}".format(self.arch_arg["d"], self.arch_arg["n"]))
        return self

    def __preprocess(self):
        '''Preprocess the task graph and extract its features
        Step 1 & 2 in the article: Calculating P(s->d), L, cv_A, P_p2p, L_p2p, L_p, RH
            Return:
                P_s2d: A list with factors' format as (src_rt, dst_rt, ratio), which denotes the proportion of
                    trasmission volume of the request (src_rt, dst_rt)
                L: A (n, ) ndarray, where L[i] denotes average injection rate of router i
                L_p: A (n, p) ndarray, where Lp[i, j] denotes packet arrival rate to the output channel j of router i
                P_p2p: A (n, p, p) ndarray, where P_p2p[i, j, k] denotes probability of a packet entered
                    from channel j is routed to channel k in router i
                L_p2p: A (n, p, p) ndarray, where L_p2p[i, j, k] denotes trasmission rate from channel j to channel k
                    in router i
                RH: A (n, p) ndarray, where RH[i, j] denotes the longest residual hops of packets
                    passing router i output channel j
        '''

        # Set up P_s2d
        G = self.task_arg["G_R"]
        G = [(r[0], r[1], r[2] / self.task_arg["l"]) for r in G]      # flit/cycle -> packet/cycle

        # TODO: a single request for a (source, destination) pair only
        assert max(Counter([(r[0], r[1]) for r in G]).values()) <= 1

        Vol = np.asarray([r[2] for r in G])
        P_s2d = Vol / np.sum(Vol)

        # Set up L_p2p, L, RH, pkt_path
        n, p = self.arch_arg["n"], self.arch_arg["p"]
        L_p2p = np.zeros((n, p, p))
        L = np.zeros(n)
        RH = np.tile(PINF, (n, p)).astype(np.int)
        pkt_path = self.__routeTaskGraph()

        for request, Path, proportion in zip(G, pkt_path, P_s2d):
            Router_path, Iport_path, Oport_path = zip(*Path)
            vol = request[2]
            L_p2p[Router_path, Iport_path, Oport_path] += vol * proportion
            L[request[0]] += vol * proportion
            Residual_hops = np.asarray([i for i in range(len(Oport_path)-1, -1, -1)])
            RH[Router_path, Oport_path] = np.minimum(RH[Router_path, Oport_path], Residual_hops)

        # Calculate P_p2p
        L_p2p_t = np.transpose(L_p2p, (1, 0, 2))    # TODO: Transpose should be replaced to optimize the performance
        L_p = np.sum(L_p2p_t, axis=0)
        P_p2p_t = L_p2p_t / (L_p + 1e-10)
        P_p2p = np.transpose(P_p2p_t, (1, 0, 2))

        # Store them
        c = self.cache
        c["P_s2d"], c["L"], c["L_p"], c["P_p2p"], c["L_p2p"], c["RH"] = P_s2d, L, L_p, P_p2p, L_p2p, RH

    def __updateOCServiceTime(self, rh):
        '''Update s_i^M and s_i^M^2
        Formula 16
            S: A (n, p) ndarray, where S[i, j] dentoes the first moment of
                service time of output channel j of router i
            S2: A (n, p) ndarray, where S[i, j] dentoes the second moment of
                service time of output channel j of router i
            W: A (n, p, p) ndarray, where W[i, j, k] denotes bloking time spent on queuing from
                input channel j to output channel k in router i
            P_p2p: A (n, p, p) ndarray, where P_p2p[i, j, k] denotes probability of a packet entered
                    from channel j is routed to channel k in router i
            RH: A (n, p) ndarray, where RH[i, j] indicates the longest residual hops of packets
                    passing router i output channel j
            rh: The present residual hop (step) we are working on
        '''
        assert rh > 0
        ts, tr, tw = self.arch_arg["ts"], self.arch_arg["tr"], self.arch_arg["tw"]
        cp_if, cp_of = self.arch_arg["cp_if"], self.arch_arg["cp_of"]
        n, p = self.arch_arg["n"], self.arch_arg["p"]
        S, S2, W = self.cache["S"], self.cache["S2"], self.cache["W"]
        P_p2p, RH = self.cache["P_p2p"], self.cache["RH"]

        Upd_s = np.zeros((n, p))
        Upd_s2 = np.zeros((n, p))
        R, C = np.where(RH == rh)
        for r, c in zip(R, C):
            dst_r, dst_ic = self.__pointTo(r, c)
            for dst_oc in range(6):
                latency = ts + tr + tw
                latency += W[dst_r, dst_ic, dst_oc]
                latency += S[dst_r, dst_oc]
                latency -= max(ts, tw) * (cp_if + cp_of)
                latency = max(latency, 0)
                Upd_s[r, c] += P_p2p[dst_r, dst_ic, dst_oc] * latency
                Upd_s2[r, c] += P_p2p[dst_r, dst_ic, dst_oc] * latency**2
        S += Upd_s
        S2 += Upd_s2

    def __updateRouterBlockingTime(self, rh):
        '''Update W
        Formula 13
            W: A (n, p, p) ndarray, where W[i, j, k] denotes bloking time spent on queuing from
                input channel j to output channel k in router i
            S: A (n, p) ndarray, where S[i, j] dentoes the first moment of service time of
                output channel j of router i
            S2: A (n, p) ndarray, where S[i, j] dentoes the second moment of service time of
                output channel j of router i
            L_p: A (n, p) ndarray, where Lp[i, j] denotes packet arrival rate to the
                output channel j of router
            L_p2p: A (n, p, p) ndarray, where L_p2p[i, j, k] denotes trasmission rate from
                channel j to channel k in router i
            RH: A (n, p) ndarray, where RH[i, j] indicates the longest residual hops of packets
                passing router i output channel j
            rh: The present residual hop (step) we are working on
        '''
        S, S2, W = self.cache["S"], self.cache["S2"], self.cache["W"]
        L_p, L_p2p, RH = self.cache["L_p"], self.cache["L_p2p"], self.cache["RH"]

        lr, lc = np.where(RH == rh)
        for r, oc in zip(lr, lc):
            p = self.arch_arg["p"]
            L = np.asarray([np.sum(L_p2p[r, :i, oc]) for i in range(p)])
            L[0] = L_p2p[r, 0, oc]                  # input channel
            Service_rate = 1 / S[r, oc]
            L[1:] = 2 * (Service_rate - L[1:])**2
            L[0] = 2 * (Service_rate - L[0])        # input channel
            arrival_rate = L_p[r, oc]
            ca2 = self.task_arg["cv_A"]**2
            cs2 = S2[r, oc] / S[r, oc]**2 - 1
            L = arrival_rate * (ca2 + cs2) / L
            L[0] = L[0] / Service_rate              # input channel
            W[r, :, oc] = L

        if np.nan in W:
            raise Exception("NAN in W: rh = {}".format(rh))

    def __analyzePktTime(self):
        l_ = self.task_arg["l"]
        ts, tw, tr = self.arch_arg["ts"], self.arch_arg["tw"], self.arch_arg["tr"]
        W, Path = self.cache["W"], self.cache["pkt_path"]
        lb = max(ts, tw) * (l_ - 1)
        Time = []
        for path in Path:
            time = lb
            for r, ic, oc in path:
                time += tr + W[r, ic, oc] + ts + tw
            Time.append(time)
        return Time

    def __routeTaskGraph(self):
        if "pkt_path" in self.cache:
            return self.cache["pkt_path"]
        ret = []
        for rqst in self.task_arg["G_R"]:
            Router_path = self.__passedRouters(rqst[0], rqst[1])
            Iport_path, Oport_path = self.__passedIOChannels(Router_path)
            Router_path = [cord[1] * self.arch_arg["d"] + cord[0] for cord in Router_path]
            ret.append(list(zip(Router_path, Iport_path, Oport_path)))
        self.cache["pkt_path"] = ret
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

    def __pointTo(self, src, oc):
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


if __name__ == "__main__":
    task_arg = {
        "G_R": [(0, 3, 0.2), (0, 1, 0.2), (1, 2, 0.2), (2, 3, 1)]
    }
    pm = PEstimator()
