#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
# idltypex.py -- export IDL data type info from database record list
import json
from pathlib import Path

# export (print) a single IDL file of the passed-in type collection
def export_idl_type(trec):
    idlout = []
    for item in trec:
        typedefLines = []
        ind = 0
        indstep = 2
        modpath = item[0][2].split('/')     # typePath
        midx = 0
        for mod in modpath:
            idlout.append('{}module {} {{'.format(' ' * ind, modpath[midx]))
            ind += indstep
            midx += 1
        modkind = item[0][3]
        if 'msg' in modkind:
            modkind = 'msg'
        elif 'srv' in modkind:
            modkind = 'srv'
        elif 'act' in modkind:
            modkind = 'action'
        idlout.append('{}module {} {{'.format(' ' * ind, modkind))
        ind += indstep
        idlout.append('{}module dds_ {{'.format(' ' * ind))
        ind += indstep

        if '-const' in item[0][3]:          # typeKind
            idlout.append('{}module {} {{'.format(' ' * ind, item[0][1]))
        else:
            idlout.append('{}struct {}_ {{'.format(' ' * ind, item[0][1]))
        ind += indstep
        # output the members
        for elem in item[1:]:
            eTypeName = elem[0][2]
            eTypePath = elem[0][3]
            if len(eTypePath) > 0:
                # 2022Jun24: eTypeName = '{}::{}::dds_::{}_'.format(eTypePath, modkind, eTypeName)
                eTypeName = '{}::{}::dds_::{}_'.format(eTypePath, 'msg', eTypeName)
            valdefs = ''
            if elem[0][6] != '':        # valdefs
                try:
                    valdefs = json.loads(elem[0][6])
                except:
                    print('loading trouble json[6] with: {}'.format(elem[0]))
            if 'const' in valdefs:
                if eTypeName == 'string':
                    idlout.append('{}const {} {}_="{}";'.format(' ' * ind, eTypeName,elem[0][1],valdefs['const']))
                else:
                    idlout.append('{}const {} {}_={};'.format(' ' * ind, eTypeName,elem[0][1],valdefs['const']))
            else:
                annoLine = '{}'.format(' ' * ind)
                # 2022Jun24: ROS2 default values have some with test values that cause trouble.  Disable for now.
                #if 'default' in valdefs:
                #    # multi-value default initializers are not supported in Connext
                #    defValStr = str(valdefs['default'])
                #    if ',' not in defValStr:
                #        annoLine += '@default({}) '.format(valdefs['default'])
                if 'range' in valdefs and 'min' in valdefs and 'max' in valdefs:
                    annoLine += '@range(min={}, max={}) '.format(valdefs['min'], valdefs['max'])
                else:
                    if 'min' in valdefs:
                        annoLine += '@min=({}) '.format(valdefs['min'])
                    if 'max' in valdefs:
                        annoLine += '@max=({}) '.format(valdefs['max'])

                if '@' in annoLine:
                    idlout.append('{}'.format(annoLine))

                # is there an attrib (array, sequence, string size) for this member?
                if elem[0][4] != '':
                    dbAttrib = json.loads(elem[0][4])
                    if len(dbAttrib) == 1:
                        # 1 attrib == string, sequence, or array
                        a0size = ''
                        if dbAttrib['0'][0] == 's':
                            # string
                            if dbAttrib['0'][1:] != '-1':
                                a0size = '<' + dbAttrib['0'][1:] + '>'
                            idlout.append('{}{}{} {};'.format(' ' * ind, eTypeName, a0size, elem[0][1]))

                        elif dbAttrib['0'][0] == 'q':
                            # sequence
                            if dbAttrib['0'][1:] != '-1':
                                a0size = ',' + dbAttrib['0'][1:]
                            idlout.append('{}sequence<{}{}> {};'.format(' ' * ind, eTypeName, a0size, elem[0][1]))

                        elif dbAttrib['0'][0] == 'a':
                            # array (always bounded)
                            idlout.append('{}{} {}[{}];'.format(' ' * ind, eTypeName, elem[0][1], dbAttrib['0'][1:]))

                        else:
                            print('!!!!!!!!!!!!!!!!! Unknown attrib[0]: {}'.format(elem[0]))

                    elif len(dbAttrib) == 2:
                        a0size = ''
                        a1size = ''
                        if dbAttrib['0'][0] == 'q':
                            if dbAttrib['0'][1:] != '-1':
                                a0size = ',' + dbAttrib['0'][1:]

                            if dbAttrib['1'][0] == 's':
                                # sequence of strings
                                if dbAttrib['1'][1:] != '-1':
                                    a1size = '<' + dbAttrib['1'][1:] + '>'
                                    if dbAttrib['0'][1:] == '-1':
                                        a0size = ' '
                                idlout.append('{}sequence<{}{}{}> {};'.format(' ' * ind, eTypeName, a1size, a0size, elem[0][1]))

                            elif dbAttrib['1'][0] == 'q':
                                # sequence of sequences of non-string type (NEEDS TYPEDEF)
                                if dbAttrib['1'][1:] != '-1':
                                    a1size = ',' + dbAttrib['1'][1:]
                                typedefName = '{}__{}'.format(eTypeName, a1size)
                                typedefLines.append('typedef sequence<{}{}> {};'.format(eTypeName, a1size, typedefName))
                                idlout.append('{}sequence<{}{}> {};'.format(' ' * ind, typedefName, a0size, elem[0][1]))

                            elif dbAttrib['1'][0] == 'a':
                                # sequence of arrays of non-string type (NEEDS TYPEDEF)
                                typedefName = '{}__{}'.format(eTypeName, dbAttrib['1'][1:])
                                typedefLines.append('typedef {} {}[{}];'.format(eTypeName, typedefName, dbAttrib['1'][1:]))
                                idlout.append('{}sequence<{}{}> {};'.format(' ' * ind, typedefName, a0size, elem[0][1]))

                            else:
                                print('!!!!!!!!!!!!Unknown attrib[0]: {}'.format(elem[0]))

                        elif dbAttrib['0'][0] == 'a':
                            if dbAttrib['0'][1:] != '-1':
                                a0size = ',' + dbAttrib['0'][1:]
                            else:
                                print('!!!!!!!!!!!!! error: unbounded arrays are not supported: {}'.format(elem[0]))

                            if dbAttrib['1'][0] == 's':
                                # array of strings -- NOT SUPPORTED
                                print('!!!!!!!!!!!! Unknown|unsupported attrib[0]: {}'.format(elem[0]))

                            elif dbAttrib['1'][0] == 'q':
                                # array of sequences of non-string type
                                if dbAttrib['1'][1:] != '-1':
                                    a1size = ',' + dbAttrib['1'][1:]
                                idlout.append('{}sequence<{}{}> {}[{}];'.format(' ' * ind, eTypeName, a1size, elem[0][1], a0size))

                            elif dbAttrib['1'][0] == 'a':
                                # array of arrays of non-string type (NOT ALLOWED)
                                print('!!!!!!!!! NOT SUPPORTED: array of arrays: {}'.format(elem[0]))
                            else:
                                print('Unknown|unsupported attrib[0]: {}'.format(elem[0]))
                        else:
                            print('!!!!!!!!!!!! Unknown attrib[0]: {}'.format(elem[0]))

                    elif len(dbAttrib) == 3:
                        a0size = ''
                        a1size = ''
                        a2size = ''
                        if dbAttrib['2'][1:] != '-1':
                            a2size = '<' + dbAttrib['2'][1:] + '>'

                        if dbAttrib['0'][0] == 'q':
                            if dbAttrib['0'][1:] != '-1':
                                a0size = ',' + dbAttrib['0'][1:]
                            
                            if dbAttrib['1'][0] == 'q':
                                # sequence of sequence of strings (needs typedef)
                                if dbAttrib['1'][1:] != '-1':
                                    a1size = ',' + dbAttrib['1'][1:]

                                typedefName = '{}__{}__{}'.format(eTypeName, a2size, a1size)
                                typedefLines.append('typedef sequence<{}{}{}> {};'.format(eTypeName, a2size, a1size, typedefName))
                                idlout.append('{}sequence<{}{}> {};'.format(' ' * ind, typedefName, a0size, elem[0][1]))

                            elif dbAttrib['1'][0] == 'a':
                                # sequence of arrays of strings: NOT SUPPORTED
                                print('!!!!!!!!! NOT SUPPORTED: sequence of arrays of strings: {}'.format(elem[0]))

                        elif dbAttrib['0'][0] == 'a':
                            if dbAttrib['0'][1:] != '-1':
                                a0size = ',' + dbAttrib['0'][1:]
                            if dbAttrib['1'][0] == 'q':
                                # array of sequences of strings: NOT CERTAIN IF THIS IS SUPPORTED
                                if dbAttrib['1'][1:] != '-1':
                                    a1size = ',' + dbAttrib['1'][1:]
                                idlout.append('{}sequence<{}{}{}> {}[{}];'.format(' ' * ind, eTypeName, a2size, a1size, elem[0][1], a0size))

                            else:
                                print('Unknown|unsupported attrib[0]: {}'.format(elem[0]))

                        else:
                            print('Unknown attrib[0]: {}'.format(elem[0]))

                else:
                    idlout.append('{}{} {};'.format(' ' * ind, eTypeName, elem[0][1]))

        ind -= indstep
        while ind >= 0:
            idlout.append('{}}};'.format(' ' * ind))
            ind -= indstep

    return idlout

# export (create/write) a single IDL file of the passed-in type collection
def export_idl_type_file(trec, typeFileName, typeNameList=[]):
    # convert types to IDL
    idlTypeFile = export_idl_type(trec)

    # write IDL to file
    if not typeFileName.endswith('.idl'):
        typeFileName = typeFileName + '.idl'
    f = open(typeFileName, "w")
    for line in idlTypeFile:
        try:
            f.write(line + '\n')
        except Exception:
            pass
    f.close()
    return str(typeFileName)

  
# return a list containing the IDL of the passed-in type collection
def type_to_string_list(trec):
    return export_idl_type(trec)
