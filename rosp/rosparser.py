#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
import os, sys
import re, datetime
import json, base64
from pathlib import Path
from sqldb import sql3db
from sqldb import types as idltypes

# try this here
# scan for data typedef files
def scan_paths_for_datatype_files(paths, types, tags, dbname):
    rosDataTypes = ['.msg','.srv','.action']
    myRosTypes = {type for type in types if type in rosDataTypes}

    # connect or create database and create table
    mydb = sql3db.SQL3Util(dbname)
    mydb.create_tables()

    rosparser_ = ROSParser(mydb)
    rosfilecount = 0
    idlfilecount = 0

    for path in paths:
        for root, dirs, files in os.walk(path):
            # check for data typedef files in this dir tree
            if len(files) > 0:
                for thisfile in files:
                    filepath = Path("{}/{}".format(root, thisfile))
                    thisname, thisext = os.path.splitext(thisfile)
                    # ROS native file types
                    if thisext in myRosTypes and os.path.exists('{}/{}'.format(root, thisfile)):
                        rosfilecount += 1
                        with open('{}/{}'.format(root, thisfile), "r", encoding="utf8" ) as f:
                            ros_in = f.read()
                            rosparser_.extract(ros_in, filepath, tags, mydb)
        
                    # IDL file (later)
                    if thisfile.endswith('.idl'):
                        idlfilecount += 1
                        # open the file, read contents
                        #print("IDL: {} : {}".format(root, thisfile))
                        #with open('{}/{}'.format(root, thisfile), "r", encoding="utf8" ) as f:
                            #idl_in = f.read()
                            #idlparser_.extract(idl_in, filepath, mydb)
        
    mydb.database_commit()
    print("ScanTotal: {} ros files, {} IDL files".format(rosfilecount, idlfilecount))

    # now resolve any unresolved type references
    mydb.resolve_member_trefs(tags)
    mydb.database_commit()
    # final check to flag types with unresolved members
    mydb.datatypes_flag_member_errors()

    mydb.database_close()


rostopic_kinds = [{'msg':''},{'srv-rq':'_Request'},{'srv-rr':'_Response'},{'act-g':'_Goal'},{'act-r':'_Result'},{'act-f':'_Feedback'}]

def rostopic_idx(rtype):
    for kind in rostopic_kinds:
        if rtype in kind:
            return rostopic_kinds.index(kind)
    return -1

class ROSParser():

    def __init__(self, dbase):
        self.dbase = dbase
        self.placeholder_member_id = ''

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

    # see if there's anything that flags this as "not a ROS type def file"
    def file_qualify(self, lines, file_path):
        # ROS2 allows .msg files to be completely empty
        if file_path.suffix == '.msg' and len(lines) == 0:
            return True

        # is this an email message file?
        if file_path.suffix == '.msg' and lines[0].startswith('From:'):
            return False

        # analyze line-by-line
        repattern = '.,<>?;:"~`!@$%^&*()_+={}|'
        for line in lines:
            line = line.strip()
            if len(line) > 0:
                if line[0] in repattern:
                    print('Rejecting non-datatype file {}'.format(str(file_path)))
                    return False
        return True



    # from a file contents, update the database
    def extract(self, file_contents, file_path, tags, dbase):

        # FIXME: move this to be called only if INSERT fails
        # create a placeholder member (this is a ROS thing, for otherwise empty topics)
        self.placeholder_member_id = self.insert_placeholder_member(dbase, tags)

        # clean up contents and make them consistent for easier parsing
        file_contents = self.prepare_input(file_contents)
        lines = file_contents.split('\n')
        lines = self._clear_comments(lines)

        # disqualfy if not a ROS data typedef file
        if self.file_qualify(lines, file_path) == False:
            return

        # get the parts of the data type name
        fileparts = file_path.parts
        name_base = file_path.stem		# the base of the typenames to be produced
        file_suffix = file_path.suffix
        module_path = fileparts[-3]

        # tryit
        startDir = str(Path.cwd().as_posix())
        fileDir = str(file_path.as_posix())
        commonPath = ''
        for i, c in enumerate(startDir):
            if c != fileDir[i]:
                commonPath = startDir[:i]
                break
        relDir = fileDir.replace(commonPath, '')


        # prepare the 'notes' for this file (filename and time/date now)
        fnotes = {'src': relDir, 'scan': datetime.datetime.now().isoformat(timespec='milliseconds')}

        # start holders for a datatype or constmodule
        # datatypes: idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags, notes
        dtype = { 'idkey': '0', 'typeName': name_base, 'typePath': module_path, 'typeKind': 'msg', 'inherits': '', 'memberList': '', 'tags': tags, 'flags': '', 'notes': json.dumps(fnotes) }
        dtype_members = []
        typemember_count = 0
        ctype = { 'idkey': '0', 'typeName': name_base + '_Constants', 'typePath': module_path, 'typeKind': 'msg-const', 'inherits': '', 'memberList': '', 'tags': tags, 'flags': '', 'notes': json.dumps(fnotes) }
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
                    ctype['memberList'] = json.dumps(const_member_ids)
                    ctype['typeName'] = type_name + '_Constants'
                    ctype['typeKind'] = list(rtypePair.keys())[0] + '-const'
                    typeid = dbase.datatype_insert(ctype)
                    dtype['inherits'] = json.dumps([typeid])
                    const_count = 0
                    const_member_ids.clear()

                if typemember_count > 0:
                    dtype['memberList'] = json.dumps(dtype_members)
                    dtype['typeName'] = type_name
                    dtype['typeKind'] = list(rtypePair.keys())[0]
                    dbase.datatype_insert(dtype)
                    typemember_count = 0
                    dtype_members.clear()
                else:
                    # if a data type has no members, create a default 
                    dummy_id = [self.placeholder_member_id]
                    dtype['memberList'] = json.dumps(dummy_id)
                    dtype['typeName'] = type_name
                    dtype['typeKind'] = list(rtypePair.keys())[0]
                    dbase.datatype_insert(dtype)

                # go to next kind
                rtIdx = rostopic_idx(list(rtypePair.keys())[0])
                rtypePair = rostopic_kinds[rtIdx + 1]

            else:
                new_const = False

                # columns: idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, tags, flags, notes
                # line_members = {'attributes': '', 'valdefs': '', 'flags': '', 'notes': ''}
                line_members = {'memberName': '', 'typeName': '', 'typePath': '', 'attributes': '', 'idkeyRef': '', 'valdefs': '', 'tags': tags, 'flags': '', 'notes': ''}
                endIdx = -1
                match = re.search('[^a-zA-Z0-9_/]', line)
                if match:
                    endIdx = match.start()
                if endIdx == -1:
                    print("Error parsing typename in line: {} for file {}".format(line, file_path))
                    continue

                # type names are either 'primitive', or they ref another via typePath/typeName or just typeName
                line_members['typeName'] = line[0:endIdx]
                
                # if idltypes.checkTypeId(line_members['typeName']) == '-1':
                if idltypes.typeNameToTypeNumber(line_members['typeName'], 'ros') == -1:
                    if '/' in line_members['typeName']:
                        pathAndName = line_members['typeName'].split('/')
                        line_members['typePath'] = pathAndName[0]
                        line_members['typeName'] = pathAndName[1]
                    else:
                        # if the typePath is not specified, use the typePath of this parent type
                        line_members['typePath'] = module_path
                        # and set a flag to let post-process type resolver know
                        line_members['flags'] = 'IMPLIEDPATH'

                # skip any whitespace
                startIdx = endIdx
                match = re.search('[^ \t]', line[startIdx:])
                if match:
                    startIdx += match.start()

                # if '[' or '<' then attrib
                if line[startIdx] == '[' or line[startIdx] == '<':
                    attribDict = {}
                    # search ahead to the first non-(space, 0-9, <, =, [, ]) char
                    endIdx = -1
                    match = re.search('[^ 0-9<=\[\]]', line[startIdx:])
                    if match:
                        endIdx = match.start()
                        endIdx += startIdx
                    if endIdx == -1:
                        print("attributes parse error on line: {}".format(line))
                        continue
                    attribPre = ''.join(line[startIdx:endIdx].split())

                    if line_members['typeName'] != 'string' and line_members['typeName'] != 'wstring':
                        # non-string arrays and sequences have simpler rules:
                        atribTmp = attribPre.strip('[').strip(']')
                        if atribTmp == '':
                            # '[]': unbounded non-string array --> unbounded sequence 'q'
                            attribPre = '<-1>'
                            attribDict['0'] = 'q-1'
                        elif '<=' in atribTmp:
                            # '[<=N]': non-string array up to size N --> bounded sequence
                            attribPre = '<' + atribTmp.strip('<').strip('=') + '>'
                            attribDict['0'] = 'q{}'.format(atribTmp.strip('<').strip('='))
                        else:
                            # '[N]': non-string array of fixed size --> array of fixed size
                            attribPre = '[' + atribTmp + ']'
                            attribDict['0'] = 'a{}'.format(atribTmp)
                    else:
                        # strings can have some complexity
                        attribList = attribPre.partition('[')
                        if attribList[1] == '':
                            # 'string<=N': bounded string
                            attribPre = '$' + attribList[0].strip('<').strip('=')
                            attribDict['0'] = 's{}'.format(attribList[0].strip('<').strip('='))
                        else:
                            # 'string...[..]' : strings in an array
                            attribPre = '<$'
                            if attribList[0] == '':
                                # 'string[..]' : unbounded strings in an array
                                attribPre = attribPre + '-1'
                                if attribList[2] != ']':
                                    # 'string[N]' : bounded array of unbounded strings --> bounded sequence of unbounded strings
                                    attribPre = attribPre + ',' + attribList[2].strip('<').strip('=').strip(']')
                                    attribDict['0'] = 'q{}'.format(attribList[2].strip('<').strip('=').strip(']'))
                                    attribDict['1'] = 's-1'
                                else:
                                    # 'string[]' : unbounded array of unbounded strings --> unbounded sequence of unbounded strings
                                    attribDict['0'] = 'q-1'
                                    attribDict['1'] = 's-1'

                                attribPre = attribPre + '>'
                            else:
                                # 'string<=N[..]' : bounded strings in an array
                                attribPre = attribPre + attribList[0].strip('<').strip('=')
                                attribDict['1'] = 's{}'.format(attribList[0].strip('<').strip('='))
                                if attribList[2] != ']':
                                    # 'string<-N[M]' : bounded array of bounded strings --> bounded sequence of bounded strings
                                    attribPre = attribPre + ',' + attribList[2].strip('<').strip('=').strip(']')
                                    attribDict['0'] = 'q{}'.format(attribList[2].strip('<').strip('=').strip(']'))
                                else:
                                    # 'string<-N[]' : unbounded array of bounded strings --> unbounded sequence of bounded strings
                                    attribDict['0'] = 'q-1'

                                attribPre = attribPre + '>'
                    # line_members['attributes'] = attribPre
                    line_members['attributes'] = json.dumps(attribDict)
                    startIdx = endIdx
                elif line_members['typeName'] == 'string' or line_members['typeName'] == 'wstring':
                    # if unbounded (w)string, add attribute
                    line_members['attributes'] = '{"0": "s-1"}'


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
                        constValStr = line[startIdx+1:].strip().strip('"')
                        if line_members['typeName'] == 'bool' and (constValStr.lower() == 'true' or constValStr.lower() == 'false'):
                            constValStr = constValStr.upper()
                        line_members['valdefs'] = '{{"const": "{}"}}'.format(constValStr)
                        new_const = True

                    # else default value
                    else:
                        defValStr = line[startIdx:].strip()
                        if line_members['typeName'] == 'bool' and (defValStr.lower() == 'true' or defValStr.lower() == 'false'):
                            defValStr = defValStr.upper()

                        # most default values will be simple, but...
                        try:
                            defVals = { 'default': json.loads(line[startIdx:]) }
                            line_members['valdefs'] = json.dumps(defVals)
                        except:
                            # ROS2 has some default strings that intermix ['",/] (for testing (?))
                            # store these encoded as base64 with key: 'default-x'
                            defVals = { 'default-x': base64.b64encode(line[startIdx:].encode('ascii')).decode('ascii') }
                            line_members['valdefs'] = json.dumps(defVals)

                # Check and correct some ROS unfortunates...
                if line_members['memberName'] == 'sequence':
                    line_members['memberName'] = 'sequence_'
                            
                # put this member into the database (returns the IDkey), and normalize the primitive typename
                primTypeNumber = idltypes.typeNameToTypeNumber(line_members['typeName'], 'ros')
                if primTypeNumber != -1:
                    line_members['typeName'] = idltypes.typeNumberToTypeName(primTypeNumber, 'idl')
                line_members['idkeyRef'] = str(primTypeNumber)
                elemkey = dbase.member_insert(line_members)

                # was this a const member?
                if new_const:
                    const_member_ids.append(elemkey)
                    const_count += 1
                else:
                    dtype_members.append(elemkey)
                    typemember_count += 1


        # when finished, commit the datatype and optional const group
        type_name = name_base + list(rtypePair.values())[0]

        if const_count > 0:
            ctype['memberList'] = json.dumps(const_member_ids)
            ctype['typeName'] = type_name + '_Constants'
            ctype['typeKind'] = list(rtypePair.keys())[0] + '-const'
            typeid = dbase.datatype_insert(ctype)
            dtype['inherits'] = json.dumps([typeid])

        if typemember_count > 0:
            dtype['memberList'] = json.dumps(dtype_members)
            dtype['typeName'] = type_name
            dtype['typeKind'] = list(rtypePair.keys())[0]
            dbase.datatype_insert(dtype)
        else:
            # if a data type has no members, create a default 
            dummy_id = [self.placeholder_member_id]
            dtype['memberList'] = json.dumps(dummy_id)
            dtype['typeName'] = type_name
            dtype['typeKind'] = list(rtypePair.keys())[0]
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

    # this inserts a member record into database for placeholder type:
    # "uint8 structure_needs_at_least_one_member"
    def insert_placeholder_member(self, dbase, tags):
        # members: idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, tags, flags, notes
        line_members = {'memberName': 'structure_needs_at_least_one_member', 'typeName': 'uint8', 'typePath': '', 'attributes': '', 'idkeyRef': '', 'valdefs': '', 'tags': tags, 'flags': '', 'notes': ''}
        #line_members['idkeyRef'] = str(idltypes.typeNameToTypeNumber(line_members['typeName'], 'ros'))
        primTypeNumber = idltypes.typeNameToTypeNumber(line_members['typeName'], 'ros')
        if primTypeNumber != -1:
            line_members['typeName'] = idltypes.typeNumberToTypeName(primTypeNumber, 'idl')
        line_members['idkeyRef'] = str(primTypeNumber)
        elemkey = dbase.member_insert(line_members)
        return elemkey
