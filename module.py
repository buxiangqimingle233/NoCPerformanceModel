import numpy as np

class Estimate:
    '''
        Estimating avg packet latency for a given mesh configuration
    '''
    def __init__(self, config):     # TODO: 加一个 configuration
        self.initNoCArg()

    def initNoCArg():
        # mesh
        noc_arg = {}
        noc_arg["channel_size"] = 9
        noc_arg["type"] = "mesh"
        noc_arg["bandwidth"] = 1      # Bandwidth of channels
        noc_arg["router_service_time"] = 1   # Processing delay of routers
        noc_arg["R"] = 1              # TODO: What does it mean ?

    def packetLatency(self, L, LC):
        '''
            L: A P x P ndarray, L_ij denotes the rate from channel i to
                channel j (P * P)
            LC: A P x P ndarray, LC is a diagonal matrix where LC_ii denotes
                input rate of channel i
            Return: 
        '''
        queue_length = self.routerQueueLength(L, LC)

    def routerQueueLength(self, L, LC):
        '''
            Estimate average length of input queue of each router.
        '''
        P = self.noc_arg["channel_size"]
        T = self.noc_arg["router_service_time"]
        R = self.noc_arg["R"] * np.ones((P, 1))
        diag_idx = [i for i in range(P)]

        F = L / L.sum(axis=0).reshape(P, 1)
        F[diag_idx, diag_idx] = 0

        C = np.dot(F, F.T)
        C[diag_idx, diag_idx] = 1

        Item = np.eye(P)
        Inv = np.linalg.inv(Item - np.dot(T * LC, C))
        N = np.dot(np.dot(Inv, LC), R)

        return N