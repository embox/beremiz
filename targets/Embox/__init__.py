import os
from targets.Embox.myBuilder import MybuildBuilder

class Embox_target:
    def __init__(self, CTRInstance) -> None:
        self.CTRInstance = CTRInstance
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())
        self.Mybuilder = MybuildBuilder(CTRInstance.Project.getname())

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.md5key = None

    def build(self):
        path_to_Mybuild = os.path.join(self.buildpath, "Mybuild")
        self.Mybuilder.save(path_to_Mybuild)
        for CTNInstance in self.CTRInstance.IterChildren():
            if CTNInstance.CTNType == "modbus":
                CTNInstance.CTNGenerate_C(self.buildpath, [])


        return True