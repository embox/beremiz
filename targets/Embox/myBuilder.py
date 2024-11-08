class MybuildBuilder:
    def __init__(self, programm_name) -> None:
        self.package_name = "beremiz.softplc"
        self.annotations = ["@AutoCmd", f"@Cmd(name=\"{programm_name}\", help=\"\", man=\"\")", "@BuildDepends(project.softplc.iecsup)"]
        self.module_name = programm_name
        self.sources = ["plc.st"]
        self.dependencies = ["@NoRuntime depends project.softplc.iecsup", "@NoRuntime depends project.softplc.ieclib.leddrv"]

    def __str__(self):
        return f"package {self.package_name}\n\n" + \
        "\n".join(self.annotations) + \
        f"\nmodule {self.module_name}" + ' {\n' + \
        "\n".join(f"\tsource {src}" for src in self.sources) + "\n\n" + \
        "\n".join(f"\t{dep}" for dep in self.dependencies) + "\n}"
    
    def save(self, path):
        f = open(path, "w")
        f.write(str(self))
        f.close()