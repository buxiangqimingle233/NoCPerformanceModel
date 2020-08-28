import sys
sys.path.append(".")
sys.path.append("..")
from src import primitive

model = performance_model.PerformanceModel(1)
model.noc_arg["channel_size"] = 4
model.noc_arg["router_size"] = 4

task_graph = [(0, 3, 0.2), (2, 1, 0.1)]
L, LC = model.analyzeTaskGraph(task_graph)
N = model.estInputQueueSize(L, LC)
print(N)