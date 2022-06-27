#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
import os, sys
import re
import json
from pathlib import Path
from sqldb import sql3db

class IDLParser():

    def __init__(self, dbase, msg_dirs=[], verbose=False):
        self._dirs = msg_dirs
        self._verbose = verbose
        self._parsed_files = []

    @property
    def global_message(self):
        return self._global_message

    def is_primitive(self, name):
        return msg_type.is_primitive(name)

    @property
    def dirs(self):
        return self._dirs

    def prepare_input(self, data):
        from re import compile, UNICODE, MULTILINE
        flags = UNICODE | MULTILINE

        pattern = compile('\[[ \n]+', flags)
        data = pattern.sub('[', data)

        pattern = compile('[ \n]+\]', flags)
        data = pattern.sub(']', data)

        pattern = compile('\<[ \n]+', flags)
        data = pattern.sub('<', data)

        pattern = compile('[ \n]+\>', flags)
        data = pattern.sub('>', data)
        return data

    # from a file contents, update the database
    def extract(self, file_contents, file_path, dbase):
        # clean up contents and make them consistent for easier parsing
        file_contents = self.prepare_input(file_contents)
        lines = file_contents.split('\n')
        lines = self._clear_comments(lines)

        # get the parts of the data type name
        fileparts = file_path.parts
        name_base = file_path.stem		# the base of the typenames to be produced
        file_suffix = file_path.suffix
        module_path = fileparts[-3] + '/' + fileparts[-2]
        #path_type = fileparts[-2]		# msg, srv, action
        #path_group = fileparts[-3]		# the 'group', such as: std_msgs, sensor_msgs, etc.

        # start holders for a datatype or constmodule
        # datatypes: idkey, kind, name, mpath, inhids, mids, tags, flags, notes
        dtype = { 'idkey': '0', 'kind': 'msg', 'name': name_base, 'mpath': module_path, 'inhids': '', 'mids': '', 'flags': '', 'notes': '' }
        dtype_midrefs = []
        typemember_count = 0
        ctype = { 'idkey': '0', 'kind': 'msg-const', 'name': name_base + '_Constants', 'mpath': module_path, 'inhids': '', 'mids': '', 'flags': '', 'notes': '' }
        const_member_ids = []
        const_count = 0
        type_name = name_base
        commit_type = False
        # for each file, set the type (this helps select the topic names)
        if file_suffix == '.msg':
            rtypePair = rostopic_kinds[0]
        elif file_suffix == '.srv':
            rtypePair = rostopic_kinds[1]
        elif file_suffix == '.action':
            rtypePair = rostopic_kinds[3]
        
        # parse each line, building and storing as items are completed
        for line in lines:
            # get the parts of each line
            line = line.strip()
            # print(line)
         
            # if there's a divider in a SRV or ACTION file, update the mode and database
            if 'msg' not in rtypePair and line.find('---') >= 0 and line.find('----') < 0:
                type_name = name_base + list(rtypePair.values())[0]
                if const_count > 0:
                    ctype['mids'] = json.dumps(const_member_ids)
                    ctype['name'] = type_name + '_Constants'
                    ctype['kind'] = list(rtypePair.keys())[0] + '-const'
                    typeid = dbase.datatype_insert(ctype)
                    dtype['inhids'] = typeid
                    const_count = 0
                    const_member_ids.clear()

                if typemember_count > 0:
                    dtype['mids'] = json.dumps(dtype_midrefs)
                    dtype['name'] = type_name
                    dtype['kind'] = list(rtypePair.keys())[0]
                    dbase.datatype_insert(dtype)
                    typemember_count = 0
                    dtype_midrefs.clear()
                else:
                    # if a data type has no members, create a default 
                    dummy_id = [self.placeholder_member_id]
                    dtype['mids'] = json.dumps(dummy_id)
                    dtype['name'] = type_name
                    dtype['kind'] = list(rtypePair.keys())[0]
                    dbase.datatype_insert(dtype)

                # go to next kind
                rtIdx = rostopic_idx(list(rtypePair.keys())[0])
                rtypePair = rostopic_kinds[rtIdx + 1]

            else:
                new_const = False

                # columns: idkey, name, tname, attrib, idref, valdef, tags, flags, notes
                line_members = {'attrib': '', 'valdef': '', 'flags': '', 'notes': ''}

                # insert code revision ------------------------------
                # line[0] to first (' ' or '<' or '[') == typename
                endIdx = -1
                match = re.search('[^a-zA-Z0-9_/]', line)
                if match:
                    endIdx = match.start()
                if endIdx == -1:
                    print("Error parsing typename in line: {}".format(line))
                    continue
                line_members['typeName'] = line[0:endIdx]

                # skip any whitespace
                startIdx = endIdx
                match = re.search('[^ \t]', line[startIdx:])
                if match:
                    startIdx += match.start()

                # if '[' or '<' then attrib
                if line[startIdx] == '[' or line[startIdx] == '<':
                    # search ahead to the first non-(space, 0-9, <, =, [, ]) char
                    endIdx = -1
                    match = re.search('[^ 0-9<=\[\]]', line[startIdx:])
                    if match:
                        endIdx = match.start()
                        endIdx += startIdx
                    if endIdx == -1:
                        print("attrib parse error on line: {}".format(line))
                        continue
                    line_members['attributes'] = ''.join(line[startIdx:endIdx].split())
                    startIdx = endIdx

                # next word is Name; get until ' ' or '=' or EOL
                # find next space, '=', or end of buffer
                endIdx = -1
                match = re.search('[ =\n]', line[startIdx:])
                if match == None:
                    line_members['memberName'] = line[startIdx:]
                else:
                    endIdx = match.start()
                    endIdx += startIdx
                    line_members['memberName'] = line[startIdx:endIdx]
                    startIdx = endIdx
            
                    # if ' ' move to next non-space
                    match = re.search('[^ \t]', line[startIdx:])
                    if match:
                        startIdx += match.start()

                    # if '=' then const
                    if line[startIdx] == '=':
                        line_members['valdef'] = '{{"const": "{}"}}'.format(line[startIdx+1:].strip())
                        new_const = True

                    # else default value
                    else:
                        line_members['valdef'] = '{{"default": "{}"}}'.format(line[startIdx:].strip())

                # put this member into the database (returns the IDkey)
                line_members['idkeyRef'] = str(idltypes.typeNameToTypeNumber(line_members['typeName'], 'idl'))
                elemkey = dbase.member_insert(line_members)

                # was this a const member?
                if new_const:
                    const_member_ids.append(elemkey)
                    const_count += 1
                else:
                    dtype_midrefs.append(elemkey)
                    typemember_count += 1

        # when finished, commit the datatype and optional const group
        type_name = name_base + list(rtypePair.values())[0]

        if const_count > 0:
            ctype['mids'] = json.dumps(const_member_ids)
            ctype['name'] = type_name + '_Constants'
            ctype['kind'] = list(rtypePair.keys())[0] + '-const'
            typeid = dbase.datatype_insert(ctype)
            dtype['inhids'] = typeid

        if typemember_count > 0:
            dtype['mids'] = json.dumps(dtype_midrefs)
            dtype['name'] = type_name
            dtype['kind'] = list(rtypePair.keys())[0]
            dbase.datatype_insert(dtype)
        else:
            # if a data type has no members, create a default 
            dummy_id = [self.placeholder_member_id]
            dtype['mids'] = json.dumps(dummy_id)
            dtype['name'] = type_name
            dtype['kind'] = list(rtypePair.keys())[0]
            dbase.datatype_insert(dtype)
            
    def _clear_comments(self, lines):
        output_lines = []
        in_comment = False

        for line in lines:
            line = line.strip()
            output_line = ''
            if line.find('#') >= 0:
                line = line[:line.find('#')]

            for token in line.split(' '):
                if token.find('{') >= 0:
                    token = token.replace('{', ' { ')
                if token.find(':') >= 0:
                    token = re.sub(r'([a-zA-Z0-9_]{1}):([a-zA-Z0-9_]{1}|$)', r'\1 : \2', token)
                if token.find(';') >= 0:
                    token = token.replace(';', ' ;')
                if token.find('(') >= 0:
                    token = token.replace('(', ' ( ')
                token = token.replace(',', ' , ')
                token = token.replace(')', ' ) ')
                token = token.replace('}', ' } ')
                output_line = output_line + ' ' + token.strip()
            if len(output_line.strip()) > 0:
                output_lines.append(output_line.strip() + '\n')
        return output_lines
