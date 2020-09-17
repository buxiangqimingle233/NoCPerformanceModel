

class VirCongManager:

    def __init__(self):
        super()

    def doInjection(self):
        '''
            Return: A list of task graphs which are represented as a dict with items:
                cv_A: coefficiency of the packet size (for modeling burstness)
                l: average packet size
                G_R: [(src, dst, injection rate)]
                G: [(src, dst, transmission volume)]
        '''
        return []
