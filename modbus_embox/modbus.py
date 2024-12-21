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


import os

from modbus_embox.mb_utils import *
from ConfigTreeNode import ConfigTreeNode
from PLCControler import LOCATION_CONFNODE, LOCATION_VAR_MEMORY
import util.paths as paths

ModbusPath = paths.ThirdPartyPath("Modbus")

#
#
#
# S E R V E R    M E M O R Y    A R E A       #
#
#
#

# dictionary implementing:
# key - string with the description we want in the request plugin GUI
# list - (modbus function number, request type, max count value)



class _MemoryAreaPlug(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="MemoryArea">
        <xsd:complexType>
          <xsd:attribute name="MemoryAreaType" type="xsd:string" use="optional" default="01 - Coils"/>
          <xsd:attribute name="Nr_of_Channels" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="65536"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Start_Address" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "MemoryArea":
                for child in element["children"]:
                    if child["name"] == "MemoryAreaType":
                        _list = list(modbus_memtype_dict.keys())
                        _list.sort()
                        child["type"] = _list
        return infos

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        address = self.GetParamsAttributes()[0]["children"][2]["value"]
        count = self.GetParamsAttributes()[0]["children"][1]["value"]
        function = self.GetParamsAttributes()[0]["children"][0]["value"]
        # 'BOOL' or 'WORD'
        datatype = modbus_memtype_dict[function][3]
        # 1 or 16
        datasize = modbus_memtype_dict[function][4]
        # 'Q' for coils and holding registers, 'I' for input discretes and input registers
        # datazone = modbus_memtype_dict[function][5]
        # 'X' for bits, 'W' for words
        datatacc = modbus_memtype_dict[function][6]
        # 'Coil', 'Holding Register', 'Input Discrete' or 'Input Register'
        dataname = modbus_memtype_dict[function][7]
        entries = []
        for offset in range(address, address + count):
            entries.append({
                "name": dataname + " " + str(offset),
                "type": LOCATION_VAR_MEMORY,
                "size": datasize,
                "IEC_type": datatype,
                "var_name": "MB_" + "".join([w[0] for w in dataname.split()]) + "_" + str(offset),
                "location": datatacc + ".".join([str(i) for i in current_location]) + "." + str(offset),
                "description": "description",
                "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "", False


#
#
#
# T C P    S E R V E R                 #
#
#
#

# XXX TODO "Configuration_Name" should disapear in favor of CTN Name, which is already unique

class _ModbusTCPserverPlug(object):
    # NOTE: the Port number is a 'string' and not an 'integer'!
    # This is because the underlying modbus library accepts strings
    # (e.g.: well known port names!)
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusServerNode">
        <xsd:complexType>
          <xsd:attribute name="Configuration_Name" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Local_IP_Address" type="xsd:string" use="optional"  default="#ANY#"/>
          <xsd:attribute name="Local_Port_Number" type="xsd:string" use="optional" default="502"/>
          <xsd:attribute name="SlaveID" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    CTNChildrenTypes = [("MemoryArea", _MemoryAreaPlug, "Memory Area")]
    # TODO: Replace with CTNType !!!
    PlugType = "ModbusTCPserver"

    def __init__(self):
        # NOTE:
        # The ModbusServerNode attribute is added dynamically by ConfigTreeNode._AddParamsMembers()
        # It will be an XML parser object created by
        # GenerateParserFromXSDstring(self.XSD).CreateRoot()
        
        # Set the default value for the "Configuration_Name" parameter
        # The default value will need to be different for each instance of the 
        # _ModbusTCPclientPlug class, so we cannot hardcode the default value in the XSD above
        # This value will be used by the web interface 
        #   (i.e. the extension to the web server used to configure the Modbus parameters).
        #   (The web server is run/activated/started by Beremiz_service.py)
        #   (The web server code is found in runtime/NevowServer.py)
        #   (The Modbus extension to the web server is found in runtime/Modbus_config.py)
        loc_str = ".".join(map(str, self.GetCurrentLocation()))
        self.ModbusServerNode.setConfiguration_Name("Modbus TCP Server " + loc_str)
        
    # Return the number of (modbus library) nodes this specific TCP server will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        return (1, 0, 0)

    # Return a list with a single tuple conatining the (location, IP address, port number)
    #     location   : location of this node in the configuration tree
    #     port number: IP port used by this Modbus/IP server
    #     IP address : IP address of the network interface on which the server will be listening
    #                  ("", "*", or "#ANY#" => listening on all interfaces!)
    def GetIPServerPortNumbers(self):
        port = self.ModbusServerNode.getLocal_Port_Number()
        addr = self.ModbusServerNode.getLocal_IP_Address()
        return [(self.GetCurrentLocation(), addr, port)]

    def GetConfigName(self):
        """ Return the node's Configuration_Name """
        return self.ModbusServerNode.getConfiguration_Name()

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name             = self.BaseParams.getName()
        # start off with flags that count the number of Modbus requests/transactions
        # handled by this Modbus server/slave.
        # These flags are mapped onto located variables and therefore available to the user programs
        # May be used to detect communication errors.
        # execute the Modbus request.
        # NOTE: If the Modbus slave has a 'current_location' of
        #          %QX1.2
        #       then the "Modbus Read Request Counter"  will be %MD1.2.0
        #       then the "Modbus Write Request Counter" will be %MD1.2.1
        #       then the "Modbus Read Request Flag"     will be %MD1.2.2
        #       then the "Modbus Write Request Flag"    will be %MD1.2.3
        #
        # Note that any MemoryArea contained under this server/slave
        # will ocupy the locations of type
        #          %MX or %MW
        # which will never clash with the %MD used here.
        # Additionaly, any MemoryArea contained under this server/slave
        # will ocupy locations with
        #           %M1.2.a.b (with a and b being numbers in range 0, 1, ...)
        # and therefore never ocupy the locations
        #           %M1.2.0
        #           %M1.2.1
        #           %M1.2.2
        #           %M1.2.3
        # used by the following flags/counters.
        entries = []
        entries.append({
            "name": "Modbus Read Request Counter",
            "type": LOCATION_VAR_MEMORY,
            "size": 32,           # UDINT flag
            "IEC_type": "UDINT",  # UDINT flag
            "var_name": "var_name",
            "location": "D" + ".".join([str(i) for i in current_location]) + ".0",
            "description": "Modbus read request counter",
            "children": []})        
        entries.append({
            "name": "Modbus Write Request Counter",
            "type": LOCATION_VAR_MEMORY,
            "size": 32,           # UDINT flag
            "IEC_type": "UDINT",  # UDINT flag
            "var_name": "var_name",
            "location": "D" + ".".join([str(i) for i in current_location]) + ".1",
            "description": "Modbus write request counter",
            "children": []})        
        entries.append({
            "name": "Modbus Read Request Flag",
            "type": LOCATION_VAR_MEMORY,
            "size": 1,            # BOOL flag
            "IEC_type": "BOOL",   # BOOL flag
            "var_name": "var_name",
            "location": "X" + ".".join([str(i) for i in current_location]) + ".2",
            "description": "Modbus read request flag",
            "children": []})        
        entries.append({
            "name": "Modbus write Request Flag",
            "type": LOCATION_VAR_MEMORY,
            "size": 1,            # BOOL flag
            "IEC_type": "BOOL",   # BOOL flag
            "var_name": "var_name",
            "location": "X" + ".".join([str(i) for i in current_location]) + ".3",
            "description": "Modbus write request flag",
            "children": []})        
        # recursively call all the Memory Areas under this Modbus server/save
        # i.e., all the children objects which will be of class _MemoryAreaPlug
        for child in self.IECSortedChildren():
            entries.append(child.GetVariableLocationTree())

        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}


    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [], "", False


def _lt_to_str(loctuple):
    return '.'.join(map(str, loctuple))


#
#
#
# R O O T    C L A S S                #
#
#
#
class RootClass(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRoot">
        <xsd:complexType>
          <xsd:attribute name="MaxRemoteTCPclients" use="optional" default="10">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    CTNChildrenTypes = [("ModbusTCPserver", _ModbusTCPserverPlug, "Modbus TCP Server")]
                        

    # Return the number of (modbus library) nodes this specific instance of the modbus plugin will need
    #   return type: (tcp nodes, rtu nodes, ascii nodes)
    def GetNodeCount(self):
        max_remote_tcpclient = self.GetParamsAttributes()[
            0]["children"][0]["value"]
        total_node_count = (max_remote_tcpclient, 0, 0)
        for child in self.IECSortedChildren():
            # ask each child how many nodes it needs, and add them all up.
            total_node_count = tuple(
                x1 + x2 for x1, x2 in zip(total_node_count, child.GetNodeCount()))
        return total_node_count

    # Return a list with tuples of the (location, port numbers) used by all the Modbus/IP servers
    def GetIPServerPortNumbers(self):
        IPServer_port_numbers = []
        for child in self.IECSortedChildren():
            if child.CTNType == "ModbusTCPserver":
                IPServer_port_numbers.extend(child.GetIPServerPortNumbers())
        return IPServer_port_numbers

    # Return a list with tuples of the (location, configuration_name) used by all the Modbus nodes (tcp/rtu, clients/servers)
    def GetConfigNames(self):
        Node_Configuration_Names = []
        for child in self.IECSortedChildren():
            Node_Configuration_Names.extend([(child.GetCurrentLocation(), child.GetConfigName())])
        return Node_Configuration_Names

    def CTNGenerate_C(self, buildpath, locations):

        loc_dict = {"locstr": "_".join(map(str, self.GetCurrentLocation()))}

        # Determine the number of (modbus library) nodes ALL instances of the modbus plugin will need
        #   total_node_count: (tcp nodes, rtu nodes, ascii nodes)
        #
        # Also get a list with tuples of (location, IP address, port number) used by all the Modbus/IP server nodes
        #   This list is later used to search for duplicates in port numbers!
        #   IPServer_port_numbers = [(location, IP address, port number), ...]
        #       location            : tuple similar to (0, 3, 1) representing the location in the configuration tree "0.3.1.x"
        #       IPserver_port_number: a number (i.e. port number used by the Modbus/IP server)
        #       IP address          : IP address of the network interface on which the server will be listening
        #                             ("", "*", or "#ANY#" => listening on all interfaces!)
        #
        # Also get a list with tuples of (location, Configuration_Name) used by all the Modbus nodes
        #   This list is later used to search for duplicates in Configuration Names!
        #   Node_Configuration_Names = [(location, Configuration_Name), ...]
        #       location          : tuple similar to (0, 3, 1) representing the location in the configuration tree "0.3.1.x"
        #       Configuration_Name: the "Configuration_Name" string
        total_node_count = (0, 0, 0)
        IPServer_port_numbers    = []
        Node_Configuration_Names = []
        for CTNInstance in self.GetCTRoot().IterChildren():
            if CTNInstance.CTNType == "modbus":
                # ask each modbus plugin instance how many nodes it needs, and add them all up.
                total_node_count = tuple(x1 + x2 for x1, x2 in zip(total_node_count, CTNInstance.GetNodeCount()))
                IPServer_port_numbers.   extend(CTNInstance.GetIPServerPortNumbers())
                Node_Configuration_Names.extend(CTNInstance.GetConfigNames        ())

        # Search for use of duplicate Configuration_Names by Modbus nodes
        # Configuration Names are used by the web server running on the PLC
        # (more precisely, run by Beremiz_service.py) to identify and allow 
        # changing the Modbus parameters after the program has been downloaded 
        # to the PLC (but before it is started)
        # With clashes in the configuration names, the Modbus nodes will not be
        # distinguasheble on the web interface!
        for i in range(0, len(Node_Configuration_Names) - 1):
            for j in range(i + 1, len(Node_Configuration_Names)):
                if Node_Configuration_Names[i][1] == Node_Configuration_Names[j][1]:
                    error_message = _("Error: Modbus plugin nodes %{a1}.x and %{a2}.x use the same Configuration_Name \"{a3}\".\n").format(
                                        a1=_lt_to_str(Node_Configuration_Names[i][0]),
                                        a2=_lt_to_str(Node_Configuration_Names[j][0]),
                                        a3=Node_Configuration_Names[j][1])
                    self.FatalError(error_message)

        # Search for use of duplicate port numbers by Modbus/IP servers
        # Note: We only consider duplicate port numbers if using the same network interface!
        i = 0
        for loc1, addr1, port1 in IPServer_port_numbers[:-1]:
            i = i + 1
            for loc2, addr2, port2 in IPServer_port_numbers[i:]:
                if (port1 == port2) and (
                          (addr1 == addr2)   # on the same network interface
                       or (addr1 == "") or (addr1 == "*") or (addr1 == "#ANY#") # or one (or both) of the servers
                       or (addr2 == "") or (addr2 == "*") or (addr2 == "#ANY#") # use all available network interfaces
                   ):
                    error_message = _("Error: Modbus plugin nodes %{a1}.x and %{a2}.x use same port number \"{a3}\" " + 
                                      "on the same (or overlapping) network interfaces \"{a4}\" and \"{a5}\".\n").format(
                                        a1=_lt_to_str(loc1), a2=_lt_to_str(loc2), a3=port1, a4=addr1, a5=addr2)
                    self.FatalError(error_message)

        # Determine the current location in Beremiz's project configuration
        # tree
        current_location = self.GetCurrentLocation()

        # define a unique name for the generated C and h files
        prefix = "_".join(map(str, current_location))
        # Gen_MB_c_path = os.path.join(buildpath, "MB_%s.c" % prefix)
        Gen_MB_h_path = os.path.join(buildpath, "MB_%s.h" % prefix)
        # c_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.c")
        h_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.h")

        tcpserver_node_count = 0
        nodeid = 0
        server_id = 0

        server_node_list = []
        server_memarea_list = []
        loc_vars = []
        loc_vars_init = []
        loc_vars_list = []  # list of variables already declared in C code!
        for child in self.IECSortedChildren():
            # print "<<<<<<<<<<<<<"
            # print "child (self.IECSortedChildren())----->"
            # print child.__class__
            # print ">>>>>>>>>>>>>"
            #
            if child.PlugType == "ModbusTCPserver":
                tcpserver_node_count += 1
                new_node = GetTCPServerNodePrinted(self, child)
                server_node_list.append(new_node)
                if new_node is None:
                    return [], "", False
                                
                for subchild in child.IECSortedChildren():
                    new_memarea = GetTCPServerMemAreaPrinted(self, subchild, nodeid)
                    
                    if new_memarea is None:
                        return [], "", False
                    server_memarea_list.append(new_memarea)
                    location = subchild.GetCurrentLocation()
                    start_address = int(GetCTVal(subchild, 2))
                    number = int(GetCTVal(subchild, 1))
                    function = subchild.GetParamsAttributes()[0]["children"][0]["value"]
                    # 'tab_bits', 'tab_input_bits', 'tab_registers' or 'tab_input_registers'
                    memarea = modbus_memtype_dict[function][1]
                    loc_adr = "__"+ modbus_memtype_dict[function][5] + modbus_memtype_dict[function][6] + "_".join(map(str, location)) + "_"
                    _type = "INT *" if memarea in ("tab_registers", "tab_input_registers") else "BOOL *"
                    for var in range(start_address, start_address + number):
                        var_name = loc_adr + str(var)
                        loc_vars.append(_type + var_name + ";")
                        loc_vars_init.append(var_name + " = &server_nodes[%d].mem_area.%s[%d];" % (
                                        server_id, memarea, var - start_address))
                server_id += 1

        loc_dict["loc_vars"] = "\n".join(loc_vars)
        loc_dict["loc_vars_init"] = "  \\ \n".join(loc_vars_init)
        loc_dict["server_nodes_params"] = ",\n\n".join(server_node_list)
        loc_dict["tcpserver_node_count"] = str(tcpserver_node_count)
        loc_dict["max_remote_tcpclient"] = int(
            self.GetParamsAttributes()[0]["children"][0]["value"])

        # get template file content into a string, format it with dict
        # and write it to proper .h file
        mb_main = open(h_filename).read() % loc_dict
        f = open(Gen_MB_h_path, 'w')
        f.write(mb_main)
        f.close()
