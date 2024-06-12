# mqtt/client.py

from __future__ import absolute_import

import os

from editors.ConfTreeNodeEditor import ConfTreeNodeEditor
from PLCControler import LOCATION_CONFNODE, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT
from .mqtt_client_gen import MQTTClientPanel, MQTTClientModel, MQTT_IEC_types, authParams

import util.paths as paths

PahoMqttCPath = paths.ThirdPartyPath("MQTT")
PahoMqttCLibraryPath = PahoMqttCPath 
PahoMqttCIncludePaths = [PahoMqttCPath]

class MQTTClientEditor(ConfTreeNodeEditor):
    CONFNODEEDITOR_TABS = [
        (_("MQTT Client"), "CreateMQTTClient_UI")]

    def Log(self, msg):
        self.Controler.GetCTRoot().logger.write(msg)

    def CreateMQTTClient_UI(self, parent):
        return MQTTClientPanel(parent, self.Controler.GetModelData(), self.Log, self.Controler.GetConfig)

class MQTTClient(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="MQTTClient">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="AuthType" minOccurs="0">
              <xsd:complexType>
                <xsd:choice minOccurs="0">
                  <xsd:element name="x509">
                    <xsd:complexType>
                      <xsd:attribute name="Certificate" type="xsd:string" use="optional" default="certificate.pem"/>
                      <xsd:attribute name="PrivateKey" type="xsd:string" use="optional" default="private_key.pem"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="UserPassword">
                    <xsd:complexType>
                      <xsd:attribute name="User" type="xsd:string" use="optional"/>
                      <xsd:attribute name="Password" type="xsd:string" use="optional"/>
                    </xsd:complexType>
                  </xsd:element>
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="Broker_URI" type="xsd:string" use="optional" default="ws://localhost:1883"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    EditorType = MQTTClientEditor

    def __init__(self):
        self.modeldata = MQTTClientModel(self.Log, self.CTNMarkModified)

        filepath = self.GetFileName()
        if os.path.isfile(filepath):
            self.modeldata.LoadCSV(filepath)

    def Log(self, msg):
        self.GetCTRoot().logger.write(msg)

    def GetModelData(self):
        return self.modeldata

    def GetConfig(self):
        def cfg(path): 
            try:
                attr=self.GetParamsAttributes("MQTTClient."+path)
            except ValueError:
                return None
            return attr["value"]

        AuthType = cfg("AuthType")
        res = dict(URI=cfg("Broker_URI"), AuthType=AuthType)

        paramList = authParams.get(AuthType, None)
        if paramList:
            for name,default in paramList:
                value = cfg("AuthType."+name)
                if value == "" or value is None:
                    value = default
                # cryptomaterial is expected to be in project's user provide file directory
                if name in ["Certificate","PrivateKey"]:
                    value = os.path.join(self.GetCTRoot()._getProjectFilesPath(), value)
                res[name] = value

        return res

    def GetFileName(self):
        return os.path.join(self.CTNPath(), 'selected.csv')

    def OnCTNSave(self, from_project_path=None):
        self.modeldata.SaveCSV(self.GetFileName())
        return True

    def CTNGenerate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        locstr = "_".join(map(str, current_location))
        c_path = os.path.join(buildpath, "mqtt_client__%s.c" % locstr)

        c_code = '#include "beremiz.h"\n'
        c_code += self.modeldata.GenerateC(c_path, locstr, self.GetConfig())

        with open(c_path, 'w') as c_file:
            c_file.write(c_code)

        LDFLAGS = [' "' + os.path.join(PahoMqttCLibraryPath, "libpaho-mqtt3as.a") + '"', '-lcrypto']

        CFLAGS = ' '.join(['-I"' + path + '"' for path in PahoMqttCIncludePaths])

        return [(c_path, CFLAGS)], LDFLAGS, True

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        locstr = "_".join(map(str, current_location))
        name = self.BaseParams.getName()
        entries = []
        for direction, data in self.modeldata.iteritems():
            iec_direction_prefix = {"input": "__I", "output": "__Q"}[direction]
            for row in data:
                dname, ua_nsidx, ua_nodeid_type, _ua_node_id, ua_type, iec_number = row
                iec_type, C_type, iec_size_prefix, ua_type_enum, ua_type = MQTT_IEC_types[ua_type]
                c_loc_name = iec_direction_prefix + iec_size_prefix + locstr + "_" + str(iec_number)
                entries.append({
                    "name": dname,
                    "type": {"input": LOCATION_VAR_INPUT, "output": LOCATION_VAR_OUTPUT}[direction],
                    "size": {"X":1, "B":8, "W":16, "D":32, "L":64}[iec_size_prefix],
                    "IEC_type": iec_type,
                    "var_name": c_loc_name,
                    "location": iec_size_prefix + ".".join([str(i) for i in current_location]) + "." + str(iec_number),
                    "description": "",
                    "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}
