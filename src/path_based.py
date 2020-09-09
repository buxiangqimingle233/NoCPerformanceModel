import numpy as np


PORT2IDX = {"input": 0, "output": 1, "north": 2, "south": 3, "west": 4, "east": 5}
DIR2PORT = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
PINF = 1e10


class PerformanceModel:
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
    L = np.zeros(1)
    RH = np.zeros(1)

    def __init__(self, arch_config, task_config):
        # Default configuration for on-chip networks
        self.arch_arg["type"] = "mesh"
        self.arch_arg["d"] = 16         # diameter
        self.arch_arg["n"] = 16 * 16    # # of routers
        self.arch_arg["p"] = 6          # # of channels per router (N, S, W, E, I, O)
        self.arch_arg["tr"] = 2         # cycles for arbitration
        self.arch_arg["ts"] = 1         # cycles for switching
        self.arch_arg["tw"] = 1         # cycles for transmitting a flit between two adjacent routers
        self.arch_arg["cp_if"] = 4      # capacity of input buffer (flits)
        self.arch_arg["cp_of"] = 1      # capacity of output buffer (flits)
        self.arch_arg["bw"] = 1         # bandwidth (flits)

        # Default configuration for tasks
        self.task_arg["G_R"] = []        # task graph: (src, dst, rate)
        self.task_arg["cv_A"] = 1.00     # average coefficiency of packet size
        self.task_arg["l"] = 16          # average packet size (flits)
        self.task_arg["pkt_path"] = []   # routed path: [(router, input port, output port)]

        for arg in arch_config:
            self.arch_arg[arg] = arch_config[arg]
        for arg in task_config:
            self.task_arg[arg] = task_config[arg]
        
        if self.arch_arg["n"] != self.arch_arg["d"]**2:
            raise Exception("Invalid hardware configuration: d = {}, n = {}".format(self.arch_arg["d"], self.arch_arg["n"]))

    def CommLatency(self):
        '''Analyzing latency of each transmission request assigned by task_config
            Return:
                Time: A list of estimated transmission latency of requests expressed by task_arg["G_R"],
                    noted that the two lists are with the same order to indicate the correspondence.
        '''
        n, p = self.arch_arg["n"], self.arch_arg["p"]
        P_s2d, L, L_p, P_p2p, L_p2p, RH = self.__Preprocess()
        self.RH = RH
        S = np.zeros((n, p)) + 1e-10
        S2 = np.zeros((n, p)) + 1e-10
        W = np.zeros((n, p, p))

        # Initialize S and S2
        ts, tw, l_ = self.arch_arg["ts"], self.arch_arg["tw"], self.task_arg["l"]
        lb = (l_ - 1) * max(ts, tw)
        S[RH == 0] = ts + tw + lb
        cv_A = self.task_arg["cv_A"]
        S2[RH == 0] = (ts + tw + lb)**2 / (cv_A**2 + 1)
        # Initialize W
        W = self.__updateRouterBlockingTime(W, S, S2, L_p, L_p2p, RH, 0)
        # Calculate blocking time of each router
        max_rh = np.max(RH[RH != PINF])
        for rh in range(1, max_rh + 1):
            S, S2 = self.__updateOCServiceTime(S, S2, W, P_p2p, RH, rh)
            W = self.__updateRouterBlockingTime(W, S, S2, L_p, L_p2p, RH, rh)
        Time = self.__analyzePktTime(W)
        return Time

    def __Preprocess(self):
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

        G = self.task_arg["G_R"]
        Vol = np.asarray([x[2] for x in G])
        # cv_A = self.task_arg["cv_A"]                # cv_A 是单个流packet长度的avg coefficient of variation
        P_s2d = list(Vol / np.sum(Vol))

        n = self.arch_arg["n"]
        p = self.arch_arg["p"]
        L_p2p = np.zeros((n, p, p))
        L = np.zeros(n)
        RH = np.tile(PINF, (n, p)).astype(np.int)

        for request, proportion in zip(G, P_s2d):
            Router_path = self.__RouterPath(request[0], request[1])
            Iport_path, Oport_path = self.__PortPath(Router_path)
            vol = request[2]
            d = self.arch_arg["d"]
            Router_path = [cord[1] * d + cord[0] for cord in Router_path]       # (x, y) x为横坐标，y为纵坐标
            L_p2p[Router_path, Iport_path, Oport_path] += vol * proportion
            L[request[0]] += vol * proportion
            Residual_hops = np.asarray([i for i in range(len(Oport_path) - 1, -1, -1)])
            RH[Router_path, Oport_path] = np.minimum(RH[Router_path, Oport_path], Residual_hops)
            self.task_arg["pkt_path"].append(list(zip(Router_path, Iport_path, Oport_path)))

        L_p2p_t = np.transpose(L_p2p, (1, 0, 2))            # TODO: transpose效率太低了，需要优化
        L_p = np.sum(L_p2p_t, axis=0)
        P_p2p_t = L_p2p_t / (L_p + 1e-10)
        P_p2p = np.transpose(P_p2p_t, (1, 0, 2))
        return P_s2d, L, L_p, P_p2p, L_p2p, RH

    def __updateOCServiceTime(self, S, S2, W, P_p2p, RH, rh):
        '''Calculate s_i^M and s_i^M^2 with rh residual hops
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
        ts = self.arch_arg["ts"]
        tr = self.arch_arg["tr"]
        tw = self.arch_arg["tw"]
        cp_if = self.arch_arg["cp_if"]
        cp_of = self.arch_arg["cp_of"]
        n = self.arch_arg["n"]
        p = self.arch_arg["p"]

        Upd_s = np.zeros((n, p))
        Upd_s2 = np.zeros((n, p))
        R, C = np.where(RH == rh)     # 需要在这个step做的channel
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
        return S, S2

    def __updateRouterBlockingTime(self, W, S, S2, L_p, L_p2p, RH, rh):
        '''Calculate blocking time spent on routers
        Formula 13
            W: A (n, p, p) ndarray, where W[i, j, k] denotes bloking time spent on queuing from
                input channel j to output channel k in router i
            S: A (n, p) ndarray, where S[i, j] dentoes the first moment of service time of 
                output channel j of router i
            S2: A (n, p) ndarray, where S[i, j] dentoes the second moment of service time of 
                output channel j of router i
            L_p: A (n, p) ndarray, where Lp[i, j] denotes packet arrival rate to the 
                output channel j of router i
            L_p2p: A (n, p, p) ndarray, where L_p2p[i, j, k] denotes trasmission rate from 
                channel j to channel k in router i
            RH: A (n, p) ndarray, where RH[i, j] indicates the longest residual hops of packets
                passing router i output channel j
            rh: The present residual hop (step) we are working on
        '''
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
        return W

    def __analyzePktTime(self, W):
        Path = self.task_arg["pkt_path"]
        ts, tw, tr = self.arch_arg["ts"], self.arch_arg["tw"], self.arch_arg["tr"]
        l_ = self.task_arg["l"]
        lb = max(ts, tw) * (l_ - 1)
        Time = []
        for path in Path:
            time = lb
            for r, ic, oc in path:
                time += tr + W[r, ic, oc] + ts + tw
            Time.append(time)
        return Time

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

    def __RouterPath(self, src_rt, dst_rt):
        d = self.arch_arg["d"]
        src_x, src_y = int(src_rt % d), int(src_rt // d)      # x为横坐标，y为纵坐标，左上为(0， 0)
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

    def __PortPath(self, path):
        Iport_path = [PORT2IDX["input"]]
        Oport_path = []
        for prev, pres in zip(path[:-1], path[1:]):
            op_ = (pres[0] - prev[0], pres[1] - prev[1])
            ip_ = (prev[0] - pres[0], prev[1] - pres[1])
            Iport_path.append(PORT2IDX[DIR2PORT[ip_]])
            Oport_path.append(PORT2IDX[DIR2PORT[op_]])
        Oport_path.append(PORT2IDX["output"])
        return Iport_path, Oport_path

if __name__ == "__main__":
    arch_arg = {
        "d": 2,
        "n": 2 * 2
    }
    task_arg = {
        "G_R": [(0, 3, 0.1), (0, 1, 0.05), (1, 2, 0.07), (2, 3, 0.1)]
    }
    pm = PerformanceModel(arch_arg, task_arg)
    T = pm.CommLatency()
    print(np.max(T))
