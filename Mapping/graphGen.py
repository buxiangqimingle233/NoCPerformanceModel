import numpy as np
from random import sample, shuffle


arch_arg = {
  "n": 4 * 4,
  "d": 4
}
n = arch_arg["n"]
out_degree = np.random.normal(n / 2, 1.0, n).astype("int16")
out_degree[out_degree < 0] = 0
out_degree[out_degree >= n] = n - 1
dstss = [sample([i for i in range(n)], od) for od in out_degree]
srcs = [i for i in range(n)]
links = [(src, dst) for src, dsts in zip(srcs, dstss) for dst in dsts if src != dst]
shuffle(links)

min_vol, max_vol = 0, 500
vols = np.random.normal((min_vol + max_vol) / 2, 80, len(links))
comm_graphs = [tuple(list(sd) + [vol]) for sd, vol in zip(links, vols)]

with open("sample.txt", "w") as f:
    for req in comm_graphs:
        tmp = ",".join(str(x) for x in req) + "\n"
        f.write(tmp)
