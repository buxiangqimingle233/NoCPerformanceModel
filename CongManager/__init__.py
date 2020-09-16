# Input: [(src, dst, vol)]
# Output: [G1, G2, G3...]
# Gi:
#   n * n array: injection rate (first moment);
#   n*n array: injection probability
#   cv_A
#   pkt_size
#   start, end

#   routing strategy independent:
#       往里灌，同比例分配带宽

import sys
sys.path.append("..")

__all__ = ["CongManager", "SFCongManager"]