from __future__ import print_function
from __future__ import absolute_import

import csv
import functools
from threading import Thread
from collections import OrderedDict

import wx
import wx.dataview as dv

# from perfect_hash import generate_code, IntSaltHash

MQTT_IEC_types = dict(
# IEC61131|  C  type   | sz
    BOOL  = ("uint8_t" , "X"),
    SINT  = ("int8_t"  , "B"),
    USINT = ("uint8_t" , "B"),
    INT   = ("int16_t" , "W"),
    UINT  = ("uint16_t", "W"),
    DINT  = ("uint32_t", "D"),
    UDINT = ("int32_t" , "D"),
    LINT  = ("int64_t" , "L"),
    ULINT = ("uint64_t", "L"),
    REAL  = ("float"   , "D"),
    LREAL = ("double"  , "L"),
)

"""
 QoS - Quality of Service
  0  : "At most one delivery"
  1  : "At least one delivery"
  2  : "Exactly one delivery"
"""
QoS_values = [0, 1, 2]

def boolean(v):
    if v in ["False","0"]:
        return False
    else:
        return bool(v)

lstcolnames  = [ "Topic",  "QoS",  "Retain", "Type", "Location"]
lstcolwidths = [     100,     50,       100,    100,         50]
lstcoltypess = [     str,    int,   boolean,    str,        int]
lstcoldeflts = [ "a/b/c",    "1",     False, "DINT",        "0"]
Location_column = lstcolnames.index("Location")

directions = ["input", "output"]

authParams = {
    "x509":[
        ("Certificate", "certificate.der"),
        ("PrivateKey", "private_key.pem")],
    "UserPassword":[
        ("User", None),
        ("Password", None)]}

class MQTTTopicListModel(dv.PyDataViewIndexListModel):
    def __init__(self, data, log):
        dv.PyDataViewIndexListModel.__init__(self, len(data))
        self.data = data
        self.log = log

    def GetColumnType(self, col):
        return "string"

    def GetValueByRow(self, row, col):
        return str(self.data[row][col])

    # This method is called when the user edits a data item in the view.
    def SetValueByRow(self, value, row, col):
        expectedtype = lstcoltypess[col]

        try:
            v = expectedtype(value)
        except ValueError: 
            self.log("String {} is invalid for type {}\n".format(value,expectedtype.__name__))
            return False

        if col == lstcolnames.index("QoS") and v not in QoS_values:
            self.log("{} is invalid for IdType\n".format(value))
            return False

        self.data[row][col] = v
        return True

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(lstcolnames)

    # Report the number of rows in the model
    def GetCount(self):
        #self.log.write('GetCount')
        return len(self.data)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        if col == Location_column:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False


    def DeleteRows(self, rows):
        # make a copy since we'll be sorting(mutating) the list
        # use reverse order so the indexes don't change as we remove items
        rows = sorted(rows, reverse=True)

        for row in rows:
            # remove it from our data structure
            del self.data[row]
            # notify the view(s) using this model that it has been removed
            self.RowDeleted(row)


    def AddRow(self, value):
        if self.data.append(value):
            # notify views
            self.RowAppended()

    def InsertDefaultRow(self, row):
        self.data.insert(row, lstcoldeflts[:])
        # notify views
        self.RowInserted(row)
    
    def ResetData(self):
        self.Reset(len(self.data))

class MQTTTopicListPanel(wx.Panel):
    def __init__(self, parent, log, model, direction):
        self.log = log
        wx.Panel.__init__(self, parent, -1)

        self.dvc = dv.DataViewCtrl(self,
                                   style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   | dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )

        self.model = model

        self.dvc.AssociateModel(self.model)

        for idx,(colname,width) in enumerate(zip(lstcolnames,lstcolwidths)):
            self.dvc.AppendTextColumn(colname,  idx, width=width, mode=dv.DATAVIEW_CELL_EDITABLE)


        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.direction =  direction
        titlestr = direction + " variables"

        title = wx.StaticText(self, label = titlestr)

        addbt = wx.Button(self, label="Add")
        self.Bind(wx.EVT_BUTTON, self.OnAddRow, addbt)
        delbt = wx.Button(self, label="Delete")
        self.Bind(wx.EVT_BUTTON, self.OnDeleteRows, delbt)

        topsizer = wx.BoxSizer(wx.HORIZONTAL)
        topsizer.Add(title, 1, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 5)
        topsizer.Add(addbt, 0, wx.LEFT|wx.RIGHT, 5)
        topsizer.Add(delbt, 0, wx.LEFT|wx.RIGHT, 5)
        self.Sizer.Add(topsizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)


    def OnAddRow(self, evt):
        items = self.dvc.GetSelections()
        row = self.model.GetRow(items[0]) if items else 0
        self.model.InsertDefaultRow(row)

    def OnDeleteRows(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]
        self.model.DeleteRows(rows)


class MQTTClientPanel(wx.Panel):
    def __init__(self, parent, modeldata, log, config_getter):
        self.log = log
        wx.Panel.__init__(self, parent)

        # TODO replace FlexGridSizer with a simpler one
        self.inout_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        self.inout_sizer.AddGrowableCol(0)
        self.inout_sizer.AddGrowableRow(0)

        self.config_getter = config_getter

        self.selected_splitter = wx.SplitterWindow(self, style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.selected_datas = modeldata
        self.selected_models = { direction:MQTTTopicListModel(self.selected_datas[direction], log) for direction in directions }
        self.selected_lists = { direction:MQTTTopicListPanel(
                self.selected_splitter, log, 
                self.selected_models[direction], direction) 
            for direction in directions }

        self.selected_splitter.SplitHorizontally(*[self.selected_lists[direction] for direction in directions]+[300])

        self.inout_sizer.Add(self.selected_splitter, flag=wx.GROW)
        self.inout_sizer.Layout()
        self.SetAutoLayout(True)
        self.SetSizer(self.inout_sizer)

    def OnClose(self):
        pass

    def __del__(self):
        self.OnClose()

    def Reset(self):
        for direction in directions:
            self.selected_models[direction].ResetData() 
        

class MQTTClientList(list):
    def __init__(self, log, change_callback):
        super(MQTTClientList, self).__init__(self)
        self.log = log
        self.change_callback = change_callback

    def append(self, value):
        v = dict(list(zip(lstcolnames, value)))

        if type(v["Location"]) != int:
            if len(self) == 0:
                v["Location"] = 0
            else:
                iecnums = set(zip(*self)[Location_column])
                greatest = max(iecnums)
                holes = set(range(greatest)) - iecnums
                v["Location"] = min(holes) if holes else greatest+1

        if v["QoS"] not in QoS_values:
            self.log("Unknown QoS\n".format(value))
            return False

        try:
            for t,n in zip(lstcoltypess, lstcolnames):
                v[n] = t(v[n]) 
        except ValueError: 
            self.log("MQTT topic {} (Location={}) has invalid type\n".format(v["Topic"],v["Location"]))
            return False

        if len(self)>0 and v["Topic"] in list(zip(*self))[lstcolnames.index("Topic")]:
            self.log("MQTT topic {} (Location={}) already in the list\n".format(v["Topic"],v["Location"]))
            return False

        list.append(self, [v[n] for n in lstcolnames])

        self.change_callback()

        return True

    def __delitem__(self, index):
        list.__delitem__(self, index)
        self.change_callback()

class MQTTClientModel(dict):
    def __init__(self, log, change_callback = lambda : None):
        super(MQTTClientModel, self).__init__()
        for direction in directions:
            self[direction] = MQTTClientList(log, change_callback)

    def LoadCSV(self,path):
        with open(path, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            buf = {direction:[] for direction, _model in self.iteritems()}
            for direction, model in self.iteritems():
                self[direction][:] = []
            for row in reader:
                direction = row[0]
                # avoids calling change callback when loading CSV
                list.append(self[direction],row[1:])

    def SaveCSV(self,path):
        with open(path, 'w') as csvfile:
            for direction, data in self.items():
                writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for row in data:
                    writer.writerow([direction] + row)

    def _TopicsPerfectHash(self, topics):
        template = """
#define NK  $NK       /* number of keys */
#define NG  $NG       /* number of vertices */
#define NS  $NS       /* length of array T1 and T2 */

int S1[] = {$S1};
int S2[] = {$S2};
int G[] = {$G};
char *K[] = {$K};
"""
        code = generate_code(topics, Hash=IntSaltHash, template=template)
        code += """
/* return index of key in K if key is found, -1 otherwise */
int MQTT_Topic_index(const char *key)
{
    int i, f1 = 0, f2 = 0;

    for (i = 0; key[i] != '\\0' && i < NS; i++) {
        f1 += S1[i] * key[i];
        f2 += S2[i] * key[i];
        f1 %= NG;
        f2 %= NG;
    }
    i = (G[f1] + G[f2]) % NG;
    if (i < NK && strcmp(key, K[i]) == 0)
        return i;

    return -1;
}
""" 
        return code

    def GenerateC(self, path, locstr, config):
        template = """/* code generated by beremiz MQTT extension */

#include <stdint.h>
#include <pthread.h>

#include "MQTTClient.h"
#include "MQTTClientPersistence.h"

#define _Log(level, ...)                                                                           \\
    {{                                                                                             \\
        /* char mstr[256];                          */                                            \\
        /* snprintf(mstr, 255, __VA_ARGS__);        */                                            \\
        /* LogMessage(level, mstr, strlen(mstr));   */                                            \\
        printf(__VA_ARGS__);                                                          \\
    }}

#define LogInfo(...) _Log(LOG_INFO, __VA_ARGS__);
#define LogError(...) _Log(LOG_CRITICAL, __VA_ARGS__);
#define LogWarning(...) _Log(LOG_WARNING, __VA_ARGS__);

static MQTTClient client;
static MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer5;
static pthread_mutex_t clientMutex;  // mutex to keep PLC data consistent

void trace_callback(enum MQTTCLIENT_TRACE_LEVELS level, char* message)
{{
    LogWarning("Paho MQTT Trace : %d, %s\\n", level, message);
}}

#define DECL_VAR(iec_type, C_type, c_loc_name)                                                     \\
static C_type PLC_##c_loc_name##_buf = 0;                                                          \\
static C_type MQTT_##c_loc_name##_buf = 0;                                                         \\
C_type *c_loc_name = &PLC_##c_loc_name##_buf;

{decl}

#define INIT_TOPIC(topic, iec_type, c_loc_name)                                            \\
{{#topic, &MQTT_##c_loc_name##_buf, iec_type##_ENUM}},

static struct {{
    const char *topic; //null terminated topic string
    void *mqtt_pdata; //data from/for MQTT stack
    __IEC_types_enum vartype;
}} topics [] = {{
{topics}
}};

static int _connect_mqtt(void)
{{
    int rc;
    MQTTProperties props = MQTTProperties_initializer;
    MQTTProperties willProps = MQTTProperties_initializer;
    MQTTResponse response = MQTTResponse_initializer;

    response = MQTTClient_connect5(client, &conn_opts, &props, &willProps);
    rc = response.reasonCode;
    MQTTResponse_free(response);

	return rc;
}}

void __cleanup_{locstr}(void)
{{
    int rc;

    /* TODO stop publish thread */

    if (rc = MQTTClient_disconnect5(client, 5000, MQTTREASONCODE_SUCCESS, NULL) != MQTTCLIENT_SUCCESS)
    {{
        LogError("MQTT Failed to disconnect, return code %d\\n", rc);
    }}
    MQTTClient_destroy(&client);
}}

void connectionLost(void* context, char* reason)
{{
    LogWarning("ConnectionLost, reconnecting\\n");
	_connect_mqtt();
    /* TODO wait if error */
}}

int messageArrived(void *context, char *topicName, int topicLen, MQTTClient_message *message)
{{
    /* TODO : something with message */
    printf("Message arrived\\n");
    printf("     topic: %s\\n", topicName);
    printf("   message: %.*s\\n", message->payloadlen, (char*)message->payload);
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}}

#define INIT_NoAuth()                                                                             \\
    LogInfo("MQTT Init no auth");

#define INIT_x509(PrivateKey, Certificate)                                                        \\
    LogInfo("MQTT Init x509 %s,%s", PrivateKey, Certificate);
    /* TODO */

#define INIT_UserPassword(User, Password)                                                         \\
    LogInfo("MQTT Init UserPassword %s,%s", User, Password);                                      \\
	conn_opts.username = User;                                                                    \\
	conn_opts.password = Password;

#define INIT_SUBSCRIPTION(Topic, QoS)                                                             \\
    {{                                                                                            \\
        MQTTResponse response = MQTTClient_subscribe5(client, #Topic, QoS, NULL, NULL);            \\
        rc = response.reasonCode;                                                                 \\
        MQTTResponse_free(response);                                                              \\
        if (rc != MQTTCLIENT_SUCCESS)                                                             \\
        {{                                                                                        \\
            LogError("MQTT client failed to subscribe to '%s', return code %d\\n", #Topic, rc);\\
        }}                                                                                        \\
    }}

int __init_{locstr}(int argc,char **argv)
{{
    char *uri = "{uri}";
    char *clientID = "{clientID}";
    int rc;

	MQTTClient_createOptions createOpts = MQTTClient_createOptions_initializer;

	conn_opts.MQTTVersion = MQTTVERSION_5;
    conn_opts.cleanstart = 1;

    createOpts.MQTTVersion = MQTTVERSION_5;

    MQTTClient_setTraceCallback(trace_callback);
    MQTTClient_setTraceLevel(MQTTCLIENT_TRACE_ERROR);


	rc = MQTTClient_createWithOptions(
        &client, uri, clientID, MQTTCLIENT_PERSISTENCE_NONE, NULL, &createOpts);
	if (rc != MQTTCLIENT_SUCCESS)
	{{
        LogError("MQTT Failed to create client, return code %d\\n", rc);
        return rc;
    }}

	rc = MQTTClient_setCallbacks(client, NULL, connectionLost, messageArrived, NULL);
	if (rc != MQTTCLIENT_SUCCESS)
	{{
        LogError("MQTT Failed to set callbacks %d", rc);
        return rc;
	}}

{init}

	rc = _connect_mqtt();

	if (rc != MQTTCLIENT_SUCCESS) {{
        LogError("MQTT Init Failed %d", rc);
        return rc;
    }}
    /* TODO start publish thread */

    return 0;
}}

#define READ_VALUE(c_loc_name, C_type) \\
    PLC_##c_loc_name##_buf = MQTT_##c_loc_name##_buf;

void __retrieve_{locstr}(void)
{{
    /* TODO try take mutex */
{retrieve}
    /* TODO free mutex */
}}

#define WRITE_VALUE(c_loc_name, C_type) \\
    MQTT_##c_loc_name##_buf = PLC_##c_loc_name##_buf;

void __publish_{locstr}(void)
{{
    /* TODO try take mutex */
{publish}
    /* TODO free mutex */
    /* TODO unblock publish thread */
}}

"""
        
        formatdict = dict(
            locstr   = locstr,
            uri      = config["URI"],
            clientID = config["clientID"],
            decl     = "",
            topics   = "",
            cleanup  = "",
            init     = "",
            retrieve = "",
            publish  = "" 
        )

        AuthType = config["AuthType"]
        if AuthType == "x509":
            formatdict["init"] += """
    INIT_x509("{PrivateKey}", "{Certificate}")""".format(**config)
        elif AuthType == "UserPassword":
            formatdict["init"] += """
    INIT_UserPassword("{User}", "{Password}")""".format(**config)
        else:
            formatdict["init"] += """
    INIT_NoAuth()"""

        topics = OrderedDict()
        for direction, data in self.items():
            iec_direction_prefix = {"input": "__I", "output": "__Q"}[direction]
            for row in data:
                Topic, QoS, Retain, iec_type, iec_number = row
                C_type, iec_size_prefix = MQTT_IEC_types[iec_type]
                c_loc_name = iec_direction_prefix + iec_size_prefix + locstr + "_" + str(iec_number)

                formatdict["decl"] += """
DECL_VAR({iec_type}, {C_type}, {c_loc_name})""".format(**locals())

                formatdict["topics"] += """
    INIT_TOPIC({Topic}, {iec_type}, {c_loc_name})""".format(**locals())

                if direction == "input":
                    formatdict["init"] += """
    INIT_SUBSCRIPTION({Topic}, {QoS})""".format(**locals())
                    formatdict["retrieve"] += """
    READ_VALUE({c_loc_name}, {C_type})""".format(**locals())

                if direction == "output":
                    # formatdict["init"] += " NOTHING ! publish doesn't need init. "
                    formatdict["publish"] += """
    WRITE_VALUE({c_loc_name}, {C_type})""".format(**locals())

        Ccode = template.format(**formatdict)
        
        return Ccode

if __name__ == "__main__":

    import wx.lib.mixins.inspection as wit
    import sys,os

    app = wit.InspectableApp()

    frame = wx.Frame(None, -1, "MQTT Client Test App", size=(800,600))

    argc = len(sys.argv)

    config={}
    config["URI"] = sys.argv[1] if argc>1 else "tcp://localhost:1883"
    config["clientID"] = sys.argv[2] if argc>2 else ""
    config["AuthType"] = None

    if argc > 3:
        AuthType = sys.argv[3]
        config["AuthType"] = AuthType
        for (name, default), value in zip_longest(authParams[AuthType], sys.argv[4:]):
            if value is None:
                if default is None:
                    raise Exception(name+" param expected")
                value = default
            config[name] = value

    test_panel = wx.Panel(frame)
    test_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
    test_sizer.AddGrowableCol(0)
    test_sizer.AddGrowableRow(0)

    modeldata = MQTTClientModel(print)

    mqtttestpanel = MQTTClientPanel(test_panel, modeldata, print, lambda:config)

    def OnGenerate(evt):
        dlg = wx.FileDialog(
            frame, message="Generate file as ...", defaultDir=os.getcwd(),
            defaultFile="", 
            wildcard="C (*.c)|*.c", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            Ccode = """
/*
In case open62541 was built just aside beremiz, you can build this test with:
gcc %s -o %s \\
    -I ../../open62541/plugins/include/ \\
    -I ../../open62541/build/src_generated/ \\
    -I ../../open62541/include/ \\
    -I ../../open62541/arch/ ../../open62541/build/bin/libopen62541.a
*/

"""%(path, path[:-2]) + modeldata.GenerateC(path, "test", config) + """

int LogMessage(uint8_t level, char* buf, uint32_t size){
    printf("log level:%d message:'%.*s'\\n", level, size, buf);
};

int main(int argc, char *argv[]) {

    __init_test(arc,argv);
   
    __retrieve_test();
   
    __publish_test();

    __cleanup_test();

    return EXIT_SUCCESS;
}
"""

            with open(path, 'w') as Cfile:
                Cfile.write(Ccode)


        dlg.Destroy()

    def OnLoad(evt):
        dlg = wx.FileDialog(
            frame, message="Choose a file",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="CSV (*.csv)|*.csv",
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            modeldata.LoadCSV(path)
            mqtttestpanel.Reset()

        dlg.Destroy()

    def OnSave(evt):
        dlg = wx.FileDialog(
            frame, message="Save file as ...", defaultDir=os.getcwd(),
            defaultFile="", 
            wildcard="CSV (*.csv)|*.csv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            modeldata.SaveCSV(path)

        dlg.Destroy()

    test_sizer.Add(mqtttestpanel, flag=wx.GROW|wx.EXPAND)

    testbt_sizer = wx.BoxSizer(wx.HORIZONTAL)

    loadbt = wx.Button(test_panel, label="Load")
    test_panel.Bind(wx.EVT_BUTTON, OnLoad, loadbt)

    savebt = wx.Button(test_panel, label="Save")
    test_panel.Bind(wx.EVT_BUTTON, OnSave, savebt)

    genbt = wx.Button(test_panel, label="Generate")
    test_panel.Bind(wx.EVT_BUTTON, OnGenerate, genbt)

    testbt_sizer.Add(loadbt, 0, wx.LEFT|wx.RIGHT, 5)
    testbt_sizer.Add(savebt, 0, wx.LEFT|wx.RIGHT, 5)
    testbt_sizer.Add(genbt, 0, wx.LEFT|wx.RIGHT, 5)

    test_sizer.Add(testbt_sizer, flag=wx.GROW)
    test_sizer.Layout()
    test_panel.SetAutoLayout(True)
    test_panel.SetSizer(test_sizer)

    def OnClose(evt):
        mqtttestpanel.OnClose()
        evt.Skip()

    frame.Bind(wx.EVT_CLOSE, OnClose)

    frame.Show()

    app.MainLoop()
