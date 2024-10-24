#!/usr/bin/env python

import sys
import os
import re

# 
# This code was copied from OpenPLC Import Tool
# 

class FunctionBlock:
    def __init__(self, name, fbtype, locals, inputs, outputs, code):
        self.name = name
        self.type = fbtype
        self.locals = locals
        self.inputs = inputs
        self.outputs = outputs
        self.code = code

class Variable:
    def __init__(self, name, type):
        self.name = name
        self.type = type

def parse_variables(data):
    local_variables = []
    input_variables = []
    output_variables = []
    fb_code = ''

    looking_for_local = False
    looking_for_input = False
    looking_for_ouput = False

    lines = data.split('\n')
    for line in lines:
        if not looking_for_local and not looking_for_input and not looking_for_ouput:
            if 'VAR_INPUT' in line:
                looking_for_input = True
            elif 'VAR_OUTPUT' in line:
                looking_for_ouput = True
            elif 'VAR' in line:
                looking_for_local = True
            else:
                fb_code += line + '\n'
        else:
            if 'END_VAR' in line:
                looking_for_local = False
                looking_for_input = False
                looking_for_ouput = False
            elif ':' in line:
                if ':=' in line:
                    line = line.split(':=')[0]
                var_name, var_type = line.split(":")
                var_name = var_name.strip()
                var_type = var_type.strip()
                var_type = var_type.strip(';')
                if looking_for_ouput == True:
                    output_variables.append(Variable(var_name, var_type))
                elif looking_for_input == True:
                    input_variables.append(Variable(var_name, var_type))
                elif looking_for_local == True:
                    local_variables.append(Variable(var_name, var_type))

    return local_variables, input_variables, output_variables, fb_code

def parse_structured_text(data):
    function_blocks = re.findall(r"FUNCTION_BLOCK (\w+)\n(.*?)END_FUNCTION_BLOCK", data, re.DOTALL)
    functions = re.findall(r"FUNCTION (\w+) : (\w+)\n(.*?)END_FUNCTION", data, re.DOTALL)
    return_fb = []

    for f in functions:
        f_name = f[0]
        f_type = f[1]
        f_content = f[2]

        local_vars, input_vars, output_vars, f_code = parse_variables(f_content)

        f = FunctionBlock(f_name, f_type, local_vars, input_vars, output_vars, f_code)
        return_fb.append(f)

    for fb in function_blocks:
        fb_name = fb[0]
        fb_content = fb[1]

        local_vars, input_vars, output_vars, fb_code = parse_variables(fb_content)

        fb = FunctionBlock(fb_name, "FunctionBlock", local_vars, input_vars, output_vars, fb_code)
        return_fb.append(fb)

    return return_fb

def create_blank_xml():
    xml_header = """<?xml version='1.0' encoding='utf-8'?>
<project xmlns:ns1="http://www.plcopen.org/xml/tc6_0201" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://www.plcopen.org/xml/tc6_0201">
<fileHeader companyName="Embox" productName="Embox Function Blocks" productVersion="1.0" creationDateTime="2023-04-26T04:54:00"/>
<contentHeader name="Embox Function Blocks" modificationDateTime="2023-04-26T04:54:00">
<coordinateInfo>
<fbd>
<scaling x="0" y="0"/>
</fbd>
<ld>
<scaling x="0" y="0"/>
</ld>
<sfc>
<scaling x="0" y="0"/>
</sfc>
</coordinateInfo>
</contentHeader>
<types>
<dataTypes/>
<pous>
</pous>
</types>
<instances>
<configurations/>
</instances>
</project>"""
    return xml_header

def generate_vars(var_block):
    return_str = ''
    for variable in var_block:
        if variable.type == 'STRING':
            variable.type == 'string'
        return_str += '<variable name="' + variable.name + '">\n<type>\n<' + variable.type + '/>\n</type>\n'
        return_str += '<documentation>\n<xhtml:p><![CDATA[' + variable.name + ']]></xhtml:p>\n</documentation>\n</variable>\n'
    
    return return_str

def generate_xml(function_blocks):
    xml_file = create_blank_xml()

    xml_pous = ''
    for fb in function_blocks:
        if fb.type == "FunctionBlock":
            xml_pous += '<pou name="' + fb.name + '" pouType="functionBlock">\n<interface>\n'
        else:
            xml_pous += '<pou name="' + fb.name + '" pouType="function">\n<interface>\n<returnType>\n'
            xml_pous += '<' + fb.type + '/>\n</returnType>\n'

        if len(fb.inputs) > 0:
            xml_pous += '<inputVars>\n'
            xml_pous += generate_vars(fb.inputs)
            xml_pous += '</inputVars>\n'
        if len(fb.locals) > 0:
            xml_pous += '<localVars>\n'
            xml_pous += generate_vars(fb.locals)
            xml_pous += '</localVars>\n'
        if len(fb.outputs) > 0:
            xml_pous += '<outputVars>\n'
            xml_pous += generate_vars(fb.outputs)
            xml_pous += '</outputVars>\n'

        xml_pous += '</interface>\n<body>\n<ST>\n<xhtml:p><![CDATA['
        xml_pous += fb.code + ']]></xhtml:p>'
        xml_pous += """</ST>
</body>
<documentation>
<xhtml:p><![CDATA["""
        xml_pous += fb.name + """]]></xhtml:p>
</documentation>
</pou>"""

    xml_pous += '\n</pous>'

    generated_output = ''
    lines = xml_file.split('\n')
    for line in lines:
        if '</pous>' in line:
            generated_output += xml_pous + '\n'
        else:
            generated_output += line + '\n'

    return generated_output


def main(argc, argv):
    if argc < 2:
        print("Error: You must provide a Structured Text file with Embox Function Blocks")
        exit(-1)

    st_file_path = argv[1]

    try:
        st_file = open(st_file_path, "r")
        st_data = st_file.read()
    except FileNotFoundError:
        print(f"Error: File '{st_file_path}' not found")
        exit(-1)
    except IOError:
        print(f"Error: Could not read file '{st_file_path}'")
        exit(-1)

    function_blocks = parse_structured_text(st_data)

    xml_file_path = os.path.join(os.getcwd(), 'plcopen', 'Embox_Function_Blocks.xml')
    xml_data = generate_xml(function_blocks)

    try:
        xml_file = open(xml_file_path, 'w')
        xml_file.write(xml_data)
        xml_file.close()
    except FileNotFoundError:
        print(f"Error: File '{xml_file_path}' not found")
        exit(-1)
    except IOError:
        print(f"Error: Could not write to file '{xml_file_path}'")
        exit(-1)


if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
