class DirectiveTable():

    def __init__(self):
        self.directive_list = []

    def appendDirective(self, directive):
        self.directive_list.append(directive)
        return self

    def updateDirective(self, directive):
        for i in range(0, len(self.directive_list)):
            if self.directive_list[i].equals(directive):
                self.directive_list[i] = directive
        return self

    def insertDirective(self, directive, idx):
        self.directive_list.insert(idx, directive)
        return self

    def deleteDirective(self, directive):
        for i in range(0, len(self.directive_list)):
            if self.directive_list[i].equals(directive):
                del self.directive_list[i]
        return self

    def findDirective(self, name):
        ret = []
        for d in self.directive_list:
            if d.getName() == name:
                ret.append(d)
        return ret

    def getDirectiveBeforeCluster(self):
        ret = []
        for d in self.directive_list:
            if d.getType() == "CL":
                break
            ret.append(d)
        if len(ret) == len(self.directive_list):
            ret = []
        return ret

    def getDirectiveAfterCluster(self):
        ret = []
        for d in reversed(self.directive_list):
            if d.getType() == "CL":
                break
            ret.append(d)
        return list(reversed(ret))
