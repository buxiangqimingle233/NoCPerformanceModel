import numpy as np


# FIXME: 这里的x指的是纵坐标，y指的是横坐标
class MEstimator:
    '''
        Estimating average packet latency for a given mesh configuration
    '''
    noc_arg = {}

    def __init__(self, config):     # TODO: 加一个 configuration
        # mesh
        self.noc_arg["channel_size"] = 12          # # of channels
        self.noc_arg["router_size"] = 9           # # of routers
        self.noc_arg["type"] = "mesh"             # network type
        self.noc_arg["bandwidth"] = 1             # Bandwidth of channels
        self.noc_arg["router_service_time"] = 1   # Processing delay of routers
        self.noc_arg["R"] = 1                     # Residual Service time (当一个pkt到达时，当前正在处理的pkt的剩余时间)

    def estPacketLatency(self, task_graph):
        '''
            Return:
        '''
        L, LC = self.analyzeTaskGraph(task_graph)
        queue_length = self.estInputQueueSize(L, LC)
        router_latency = queue_length / np.diag(LC)

    def analyzeTaskGraph(self, task_graph):
        '''
        Generate L & LC of a given traffic task with XY routing
            task_graph: An iterable object donoting traffic pattern with \
            components as (src_index, dst_index, traffic_volume)
            Return: L & LC
        '''
        n = np.sqrt(self.noc_arg["router_size"])
        cs = self.noc_arg["channel_size"]
        L_Sum = np.zeros((cs, cs))  # L_ii is the average rate of virtual channels
        L_Cnt = np.zeros((cs, cs))  # i.e. L = L_Sum / L_Cnt
        LC = np.zeros((cs, cs))

        def index2cord(num):
            return (int(num // n), int(num % n))

        def routerCord2channelIndex(x, y, direction):
            bias = {"east": 0, "west": -1, "north": -n, "south": n - 1}
            return x * (2 * n - 1) + y + bias.get(direction)

        cord_task_graph = [
            (index2cord(item[0]), index2cord(item[1]), item[2])
            for item in task_graph
        ]

        for request in cord_task_graph:
            src_x, src_y = request[0]
            dst_x, dst_y = request[1]
            V = request[2]
            # x routing
            step = 1 if src_y < dst_y else -1
            direction = "east" if src_y < dst_y else "west"
            path = [
                routerCord2channelIndex(src_x, y, direction)
                for y in range(src_y, dst_y, step)
            ]
            # y routing
            step = 1 if src_x < dst_x else -1
            direction = "south" if src_x < dst_x else "north"
            path += [
                routerCord2channelIndex(x, dst_y, direction)
                for x in range(src_x, dst_x, step)
            ]
            path = [int(i) for i in path]
            # update
            L_Sum[path[:-1], path[1:]] += V
            L_Cnt[path[:-1], path[1:]] += 1
            LC[path, path] += V

        diag_index = [i for i in range(cs)]
        L = L_Sum / (L_Cnt + 1e-10)
        L[diag_index, diag_index] = 0
        return L, LC

    def estInputQueueSize(self, L, LC):
        '''
        Estimate input queue length in each channel
            L: A P x P ndarray, L_ij denotes the rate routed from channel i to
                channel j (P * P)
            LC: A P x P ndarray, LC is a diagonal matrix where LC_ii denotes
                input rate of channel i
            Return: A P x 1 ndarray, where N_i denotes average queue length of 
                router i
        '''
        P = self.noc_arg["channel_size"]
        diag_idx = [i for i in range(P)]

        LSum = L.sum(axis=0).reshape(1, P) + 1e-10
        F = L / np.tile(LSum, (P, 1))
        F[diag_idx, diag_idx] = 0

        T = self.noc_arg["router_service_time"]
        C = np.dot(F, F.T)
        C[diag_idx, diag_idx] = 1

        I_ = np.eye(P)
        Inv = np.linalg.inv(I_ - np.dot(T * LC, C))
        R = np.asarray([(T * T * LC[i, i] / 2) for i in range(P)])
        N = np.dot(np.dot(Inv, LC), R)

        return N