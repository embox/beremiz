import os


class MybuildBuilder:
    def __init__(self, programm_name) -> None:
        self.module_name = programm_name.replace(" ", "_")
        self.modbus_flag = False

    def save(self, path):
        loc_dict = {"module_name" : self.module_name}

        if self.modbus_flag:
            loc_dict["softplc_type"] = "sofplc_modbus"
            loc_dict["build_deps"] = "@BuildDepends(third_party.lib.libmodbus)"
            loc_dict["deps"] = '''@NoRuntime depends embox.compat.posix.pthreads
	@NoRuntime depends third_party.lib.libmodbus'''
            loc_dict["headers"] = '''@IncludeExport(path="")
	source "MB_0.h"'''
        else:
            loc_dict["softplc_type"] = "sofplc"
            loc_dict["build_deps"] = ""
            loc_dict["deps"] = ""
            loc_dict["headers"] = ""
        Mybuild_filename =  os.path.join(os.path.split(__file__)[0], "Mybuild")
        mybuild = open(Mybuild_filename).read() % loc_dict
        f = open(path, "w")
        f.write(mybuild)
        f.close()
