class Directive():
    dim_group = [
        ('X', 'Y', 'C'),
        ('X\'', 'Y\'', 'K'),
        ('K', 'C', 'R', 'S')
    ]

    def __init__(self, name, type_, size, ofs, dim_size):
        self.name, self.type, self.size, self.ofs, self.dim_size = name, type_, size, ofs, dim_size

    def getRelatedDirectiveName(self):
        ret = []
        for group in self.groups:
            if self.name in group:
                ret = [d != self.name for d in group]
        return ret

    def getName(self):
        return self.name

    def getType(self):
        return self.type

    def getSize(self):
        return self.size

    def getOfs(self):
        return self.ofs

    def getDimSize(self):
        return self.dim_size

    def equals(self, other):
        return self.type == other.type and self.name == other.name
