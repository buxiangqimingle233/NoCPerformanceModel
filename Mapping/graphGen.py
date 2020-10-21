import os
# import sys
import argparse
import numpy as np
from random import sample, shuffle


def generate(of_path, arch_arg):
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

    with open(of_path, "w") as f:
        for req in comm_graphs:
            f.write(",".join(str(x) for x in req) + "\n")


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    org_cwd = os.getcwd()
    os.chdir(root)

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", help="Path for task graph, with the root directory as NoCPerformanceModel")
    parser.add_argument("-d", type=int, help="Diameter of a single dimension")
    args = parser.parse_args()

    print("log: Generating task graph \
        Path for task graph: {}. Diameter: {}".format(args.o, args.d))
    generate(args.o, {"d": args.d, "n": args.d**2})
    os.chdir(org_cwd)
