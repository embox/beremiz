

class Embox_target:
    def __init__(self, CTRInstance) -> None:
        self.CTRInstance = CTRInstance
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.md5key = None