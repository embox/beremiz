#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (c) 2016 Mario de Sousa (msousa@fe.up.pt)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This code is made available on the understanding that it will not be
# used in safety-critical situations without a full and competent review.


# dictionary implementing:
# key   - string with the description we want in the request plugin GUI
# tuple - (modbus function number, request type, max count value,
# data_type, bit_size)
modbus_function_dict = {
    "01 - Read Coils":                ('1',  'req_input', 2000, "BOOL",  1, "Q", "X", "Coil"),
    "02 - Read Input Discretes":      ('2',  'req_input', 2000, "BOOL",  1, "I", "X", "Input Discrete"),
    "03 - Read Holding Registers":    ('3',  'req_input',  125, "WORD", 16, "Q", "W", "Holding Register"),
    "04 - Read Input Registers":      ('4',  'req_input',  125, "WORD", 16, "I", "W", "Input Register"),
    "05 - Write Single coil":         ('5', 'req_output',    1, "BOOL",  1, "Q", "X", "Coil"),
    "06 - Write Single Register":     ('6', 'req_output',    1, "WORD", 16, "Q", "W", "Holding Register"),
    "15 - Write Multiple Coils":     ('15', 'req_output', 1968, "BOOL",  1, "Q", "X", "Coil"),
    "16 - Write Multiple Registers": ('16', 'req_output',  123, "WORD", 16, "Q", "W", "Holding Register")}

modbus_memtype_dict = {
    "01 - Coils":            ('1', 'tab_bits',  65536, "BOOL", 1, "Q", "X", "Coil"),
    "02 - Input Discretes":  ('2', 'tab_input_bits',  65536, "BOOL", 1, "I", "X", "Input Discrete"),
    "03 - Holding Registers": ('3', 'tab_registers', 65536, "WORD", 16, "Q", "W", "Holding Register"),
    "04 - Input Registers":  ('4', 'tab_input_registers', 65536, "WORD", 16, "I", "W", "Input Register"),
}

# Configuration tree value acces helper
def GetCTVal(child, index):
    return child.GetParamsAttributes()[0]["children"][index]["value"]


# Configuration tree value acces helper, for multiple values
def GetCTVals(child, indexes):
    return [GetCTVal(child, index) for index in indexes]


def GetTCPServerNodePrinted(self, child):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
    """
    node_init_template = '''/*node %(locnodestr)s*/
{"%(host)s", %(port)s, %(slaveid)s, {%(nb_bits)s, %(start_bits)s, %(nb_input_bits)s, %(start_input_bits)s, %(nb_input_registers)s, %(start_input_register)s, %(nb_registers)s, %(start_registers)s}}'''

    location = ".".join(map(str, child.GetCurrentLocation()))
    config_name, host, port, slaveid = GetCTVals(child, list(range(4)))
    if host == "#ANY#":
        host = ''

    node_dict = {"locnodestr": location,
                 "config_name": config_name,
                 "host": host,
                 "port": port,
                 "slaveid": slaveid,
                 "nb_bits" : "0",
                 "start_bits" : "0",
                 "nb_input_bits" : "0",
                 "start_input_bits" : "0",
                 "nb_input_registers" : "0",
                 "start_input_register" : "0",
                 "nb_registers" : "0",
                 "start_registers" : "0"}
    
    for subchild in child.IECSortedChildren():
        function = subchild.GetParamsAttributes()[0]["children"][0]["value"]
        # 'tab_bits', 'tab_input_bits', 'tab_registers' or 'tab_input_registers'
        memarea = modbus_memtype_dict[function][1]
        node_dict[f"nb_{memarea[4:]}"] = GetCTVal(subchild, 1)
        node_dict[f"start_{memarea[4:]}"] = GetCTVal(subchild, 2)
    return node_init_template % node_dict


def GetTCPServerMemAreaPrinted(self, child, nodeid):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
            nodeid - on C code, each request has it's own parent node (sequential, 0..NUMBER_OF_NODES)
                     It's this parameter.
    return: None - if any definition error found
            The string that should be added on C code - if everything goes allright
    """
    request_dict = {}
    
    request_dict["locreqstr"] = "_".join(map(str, child.GetCurrentLocation()))
    request_dict["nodeid"] = str(nodeid)
    request_dict["address"] = GetCTVal(child, 2)
    if int(request_dict["address"]) not in range(65536):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid Start Address in server memory area node %(locreqstr)s (Must be in the range [0..65535])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    request_dict["count"] = GetCTVal(child, 1)
    if int(request_dict["count"]) not in range(1, 65537):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in server memory area node %(locreqstr)s (Must be in the range [1..65536-start_address])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if (int(request_dict["address"]) + int(request_dict["count"])) not in range(1, 65537):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in server memory area node %(locreqstr)s (Must be in the range [1..65536-start_address])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None

    return ""

