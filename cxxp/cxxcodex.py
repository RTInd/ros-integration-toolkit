#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
# cxxcodex.py -- export C++11 class wrapper and application code
# using data types / IDL from database.
import os, shutil
from pathlib import Path
from idlp import idltypex

# export (create/write) a buildable project (source, CMake, IDL) given a list of types.
# The resulting file structure will be:
# <export_dir>:         CMakeLists.txt, USER_QOS_PROFILES.xml
# <export_dir>/src/<typefilename>_app:  <typefilename>.cxx 
# <export_dir>/src/typeclass: cros2_<typename>_support.cxx/hpp for each type, plus cros2_common.cxx/hpp
# <export_dir>/src/generated: <typefilename>.idl
def export_idl_cxx11_app(trec, typeFileName, typeNameList):
    # create directories if they don't already exist
    tf = Path(typeFileName)
    tfDir = Path(tf.parents[0])
    Path(tfDir, 'src').mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'src/typeclass').mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'src/generated').mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'src/{}_app'.format(tf.stem)).mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'resources').mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'resources/cmake').mkdir(parents=True, exist_ok=True)
    Path(tfDir, 'build').mkdir(parents=True, exist_ok=True)

    # convert types to IDL and write to file
    idlTypeFile = idltypex.export_idl_type(trec)
    idlFileToWrite = Path(tfDir, 'src/generated', tf.name)
    f = open(idlFileToWrite, "w")
    for line in idlTypeFile:
        try:
            f.write(line + '\n')
        except Exception:
            pass
    f.close()

    # create class wrapper file(s)
    # <$%<TypeNameUpperCase>%$> --> the data typename (no path) in lower-case letters
    # <$%<TypeNamePreserveCase>%$> --> the data typename (no path), preserve case
    # <%$<IDLFileName>$%> --> generated or user-named IDL filename
    # <$%<RosPathAndTypeName>%$> --> the full ROS/DDS path and type name
    # <%$<IDLFileNameOnly>$%> --> just the IDL filename (no path, no extension)
    # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
    for typName in typeNameList:
        # read & modify template wrap.cxx file
        fr = open('./cxxp/classwrapexample.cxx.txt', "r")
        frbuf = fr.read()
        fr.close()
        rosPathAndTypeName = '{}::msg::dds_::{}_'.format(typName[2], typName[1])
        frbuf = frbuf.replace('<$%<TypeNameLowerCase>%$>', typName[1].lower())
        frbuf = frbuf.replace('<$%<TypeNameUpperCase>%$>', typName[1].upper())
        frbuf = frbuf.replace('<$%<TypeNamePreserveCase>%$>', typName[1])
        frbuf = frbuf.replace('<$%<RosPathAndTypeName>%$>', rosPathAndTypeName)
        # write type-specific wrap.cxx file
        cwFileName = Path(tfDir, 'src/typeclass', 'cros2_{}_support.cxx'.format(typName[1].lower()))
        fw = open(cwFileName, "w")
        fw.write(frbuf)
        fw.close

        # read & modify template wrap.hpp file
        fr = open('./cxxp/classwrapexample.hpp.txt', "r")
        frbuf = fr.read()
        fr.close()
        rosPathAndTypeName = '{}::msg::dds_::{}_'.format(typName[2], typName[1])
        frbuf = frbuf.replace('<$%<TypeNameLowerCase>%$>', typName[1].lower())
        frbuf = frbuf.replace('<$%<TypeNameUpperCase>%$>', typName[1].upper())
        frbuf = frbuf.replace('<$%<TypeNamePreserveCase>%$>', typName[1])
        frbuf = frbuf.replace('<$%<RosPathAndTypeName>%$>', rosPathAndTypeName)
        frbuf = frbuf.replace('<%$<IDLFileNameOnly>$%>', tf.stem)
        # write type-specific wrap.hpp file
        cwFileName = Path(tfDir, 'src/typeclass', 'cros2_{}_support.hpp'.format(typName[1].lower()))
        fw = open(cwFileName, "w")
        fw.write(frbuf)
        fw.close

    shutil.copyfile('./cxxp/cros2_common.cxx.txt', Path(tfDir, 'src/typeclass', 'cros2_common.cxx'))
    shutil.copyfile('./cxxp/cros2_common.hpp.txt', Path(tfDir, 'src/typeclass', 'cros2_common.hpp'))

    # create example app source file
    with open('./cxxp/example_app.cxx.txt') as fr:
        frbuf = fr.readlines()
    fr.close()

    # <%$<CommentListDataTypes>$%> --> insert list of types used in this app
    # <%$<ListIncludeFiles>$%> --> insert list of include files (cros2_xxx_support.hpp files)
    # <%$<InstantiateClasses>$%> --> insert instantiations of data type support class wrappers
    # <%$<CallPublishMethods>$%> --> insert instantiations of data type support class wrappers
    idx = 0
    while idx < len(frbuf):
        if '<%$<IDLFileNameOnly>$%>' in frbuf[idx]:
            frbuf[idx] = frbuf[idx].replace('<%$<IDLFileNameOnly>$%>', tf.stem)

        elif '<%$<CommentListDataTypes>$%>' in frbuf[idx]:
            # insert (as part of C-comment block) a list of the data types used in this example
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                rosPathAndTypeName = ' * {}::msg::dds_::{}_\n'.format(typName[2], typName[1])
                frbuf.insert(idx, rosPathAndTypeName)
                idx += 1

        elif '<%$<ListIncludeFiles>$%>' in frbuf[idx]:
            # insert the class wrapper include files
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                classWrapperIncludeFile = '#include "cros2_{}_support.hpp"\n'.format(typName[1].lower())
                frbuf.insert(idx, classWrapperIncludeFile)
                idx += 1

        elif '<%$<InstantiateClasses>$%>' in frbuf[idx]:
            # insert the class instantiations
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                frbuf.insert(idx, '    cros2{} my{}Comms(std::string("topic_{}"), (CROS2_PUB_ON | CROS2_SUB_ON), participant, &waitset);\n'.format(typName[1], typName[1], typName[1].lower()))
                idx += 1

        elif '<%$<CallPublishMethods>$%>' in frbuf[idx]:
            # insert calls to the publish() methods
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                frbuf.insert(idx, '        my{}Comms.publish();\n'.format(typName[1]))
                idx += 1
        idx += 1

    # write the app source code file
    cwFileName = Path(tfDir, 'src/{}_app'.format(tf.stem), '{}_app.cxx'.format(tf.stem))
    fw = open(cwFileName, "w")
    for line in frbuf:
        fw.write(line)
    fw.close


    # create CMakeLists.txt file if it doesn't already exist
    # if it does exist, create CMakeLists_typefilename.txt
    # FIXME: figure out how to merge contents of CMakeLists.txt files.
    with open('./cxxp/CMakeLists.txt.txt') as fr:
        frbuf = fr.readlines()
    fr.close()
    idx = 0
    while idx < len(frbuf):
        if '<%$<IDLFileNameOnly>$%>' in frbuf[idx]:
            frbuf[idx] = frbuf[idx].replace('<%$<IDLFileNameOnly>$%>', tf.stem)

        elif '<%$<ListSourceFilesCMake>$%>' in frbuf[idx]:
            # insert a list of the source files (class wrappers and generated
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                frbuf.insert(idx, '  src/typeclass/cros2_{}_support.cxx\n'.format(typName[1].lower()))
                idx += 1
            frbuf.insert(idx, '  src/typeclass/cros2_common.cxx\n')
            idx += 1
            frbuf.insert(idx, '  src/generated/{}.cxx\n'.format(tf.stem))
            idx += 1
            frbuf.insert(idx, '  src/generated/{}Plugin.cxx\n'.format(tf.stem))
            idx += 1
        idx += 1

    # write the CMakeLists.txt file
    cwFileName = Path(tfDir, 'CMakeLists.txt')
    fw = open(cwFileName, "w")
    for line in frbuf:
        fw.write(line)
    fw.close

    # copy the CMake support files to the project dir
    shutil.copyfile('./cxxp/cmake/ConnextDdsAddExample.cmake', Path(tfDir, 'resources/cmake', 'ConnextDdsAddExample.cmake'))
    shutil.copyfile('./cxxp/cmake/ConnextDdsArgumentChecks.cmake', Path(tfDir, 'resources/cmake', 'ConnextDdsArgumentChecks.cmake'))
    shutil.copyfile('./cxxp/cmake/ConnextDdsCodegen.cmake', Path(tfDir, 'resources/cmake', 'ConnextDdsCodegen.cmake'))
    shutil.copyfile('./cxxp/cmake/FindRTIConnextDDS.cmake', Path(tfDir, 'resources/cmake', 'FindRTIConnextDDS.cmake'))

    # copy USER_QOS_PROFILES.xml file if it doesn't already exist
    shutil.copyfile('./cxxp/USER_QOS_PROFILES.xml.txt', Path(tfDir, 'USER_QOS_PROFILES.xml'))

    return str(typeFileName)

  
