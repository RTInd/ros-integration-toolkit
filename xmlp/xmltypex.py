#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
# xmltypex.py -- export XML data type info from database record list
import json
from sqldb import types as idltypes
from pathlib import Path

# export (print) a single XML file of the passed-in type collection
def export_xml_type(trec):
    xmlout = []
    xmlout.append('<types>')
    for item in trec:
        # xmlout = []
        typedefLines = []
        ind = 2
        indstep = 2
        modpath = item[0][2].split('/')     # typePath
        midx = 0
        for mod in modpath:
            xmlout.append('{}<module name="{}">'.format(' ' * ind, modpath[midx]))
            ind += indstep
            midx += 1
        modkind = item[0][3]
        if 'msg' in modkind:
            modkind = 'msg'
        elif 'srv' in modkind:
            modkind = 'srv'
        elif 'act' in modkind:
            modkind = 'action'
        xmlout.append('{}<module name="{}">'.format(' ' * ind, modkind))
        ind += indstep
        xmlout.append('{}<module name="dds_">'.format(' ' * ind))
        ind += indstep

        if '-const' in item[0][3]:          # typeKind
            xmlout.append('{}<module name="{}">'.format(' ' * ind, item[0][1]))
        elif item[0][1].endswith('_'):
            xmlout.append('{}<struct name="{}">'.format(' ' * ind, item[0][1]))
        else:
            xmlout.append('{}<struct name="{}_">'.format(' ' * ind, item[0][1]))
        ind += indstep

        # insert new xml output code (from IDL out) ----------------------------------------------------------
        # output the members
        for elem in item[1:]:
            eTypeName = elem[0][2]
            eTypePath = elem[0][3]

            # if the idkeyRef shows it's a primitive value, convert to XML primitive typename
            if len(eTypePath) > 0:
                eTypeName = '{}::{}::dds_::{}_'.format(eTypePath, modkind, eTypeName)
            isBasicType = len(elem[0][5]) < 3
            if isBasicType:
                eTypeName = idltypes.typeNumberToTypeName(int(elem[0][5]), 'xml')

            # extract any const or default values
            valdefs = ''
            if elem[0][6] != '':        # valdefs
                try:
                    valdefs = json.loads(elem[0][6])
                except:
                    print('formatting error for valdefs with: {}'.format(elem[0]))
                    break
            isConst = 'const' in valdefs

            # start the line
            xmlOutLine = '{}'.format(' ' * ind)

            # const or member?
            if isConst:
                xmlOutLine += '<const '
            else:
                xmlOutLine += '<member '

            # if sequence, specify max length here

            # member name
            xmlOutLine += 'name="{}" '.format(elem[0][1])

            # get any attributes that show use/length of array, sequence, string
            dbAttrib = {}
            if elem[0][4] == '':
                if isConst:
                    if eTypeName == 'boolean' and (valdefs['const'] == 'TRUE' or valdefs['const'] == 'FALSE'):
                        valdefs['const'] = valdefs['const'].lower()
                    xmlOutLine += 'type="{}" value="{}"/>'.format(eTypeName, valdefs['const'])
                else:
                    if isBasicType:
                        xmlOutLine += 'type="{}"/>'.format(eTypeName)
                    else:
                        xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}"/>'.format(eTypeName)
            else:
                dbAttrib = json.loads(elem[0][4])
                if len(dbAttrib) == 1:
                    # 1 attrib == string, sequence, or array
                    if dbAttrib['0'][0] == 's':
                        # string
                        xmlOutLine += 'stringMaxLength="{}" type="{}"/>'.format(dbAttrib['0'][1:], eTypeName)
                    elif dbAttrib['0'][0] == 'q':
                        # sequence
                        if isBasicType:
                            xmlOutLine += 'sequenceMaxLength="{}" type="{}"/>'.format(dbAttrib['0'][1:], eTypeName)
                        else:
                            xmlOutLine += 'sequenceMaxLength="{}" type="nonBasic" nonBasicTypeName="{}"/>'.format(dbAttrib['0'][1:], eTypeName)
                    elif dbAttrib['0'][0] == 'a':
                        # array
                        if isBasicType:
                            xmlOutLine += 'type="{}" arrayDimensions="{}"/>'.format(eTypeName, dbAttrib['0'][1:])
                        else:
                            # FIXME: not certain if you can have arrays of nonbasic types.
                            xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}" arrayDimensions="{}"/>'.format(eTypeName, dbAttrib['0'][1:])
                    else:
                        print('!!!!!!!!!!!!!!!!! Unknown attrib[0]: {}'.format(elem[0]))

                elif len(dbAttrib) == 2:
                    if dbAttrib['0'][0] == 'q':
                        if dbAttrib['1'][0] == 's':
                            # sequence of strings
                            xmlOutLine += 'sequenceMaxLength="{}" stringMaxLength="{}" type="{}"/>'.format(dbAttrib['0'][1:], dbAttrib['1'][1:], eTypeName)
                        elif dbAttrib['1'][0] == 'q':
                            # sequence of sequences of non-string type (NEEDS TYPEDEF)
                            typedefName = '{}__{}'.format(eTypeName, dbAttrib['1'][1:])
                            typedefLines.append('<typedef name="{}" type="{}" sequenceMaxLength="{}"/>'.format(typedefName, eTypeName, dbAttrib['1'][1:]))
                            xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}" sequenceMaxLength="{}"/>'.format(eTypeName, dbAttrib['0'][1:])
                        elif dbAttrib['1'][0] == 'a':
                            # sequence of arrays of non-string type (NEEDS TYPEDEF)
                            typedefName = '{}__{}'.format(eTypeName, dbAttrib['1'][1:])
                            typedefLines.append('<typedef name="{}" type="{}" dimensions="{}"/>'.format(typedefName, eTypeName, dbAttrib['1'][1:]))
                            xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}" sequenceMaxLength="{}"/>'.format(eTypeName, dbAttrib['0'][1:])
                        else:
                            print('!!!!!!!!!!!!Unknown attrib[0]: {}'.format(elem[0]))

                    elif dbAttrib['0'][0] == 'a':
                        if dbAttrib['1'][0] == 'q':
                            # array of sequences of non-string type
                            if isBasicType:
                                xmlOutLine += 'type="{}", arrayDimensions="{}" sequenceMaxLength="{}"/>'.format(eTypeName, dbAttrib['0'][1:], dbAttrib['1'][1:])
                            else:
                                xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}" arrayDimensions="{}" sequenceMaxLength="{}"/>'.format(eTypeName, dbAttrib['0'][1:], dbAttrib['1'][1:])
                        else:
                            print('Unknown|unsupported attrib[0]: {}'.format(elem[0]))
                    else:
                        print('!!!!!!!!!!!! Unknown attrib[0]: {}'.format(elem[0]))

                elif len(dbAttrib) == 3:
                    if dbAttrib['0'][0] == 'q' and dbAttrib['1'][0] == 'q' and dbAttrib['2'][0] == 's':
                        # sequence of sequence of strings (needs TYPEDEF)  not sure if this is allowed
                        typedefName = '{}__{}'.format(eTypeName, dbAttrib['1'][1:])
                        typedefLines.append('<typedef name="{}" stringMaxLength="{}" type="{}" sequenceMaxLength="{}"/>'.format(typedefName, dbAttrib['2'][1:], eTypeName, dbAttrib['1'][1:]))
                        xmlOutLine += 'type="nonBasic" nonBasicTypeName="{}" sequenceMaxLength="{}"/>'.format(eTypeName, dbAttrib['0'][1:])
                    else:
                        print('!!!!!!!!!!!!!! Unknown attrib[0]: {}'.format(elem[0]))
                else:
                    print('!!!!!!!!!!!! Unknown attrib: {}'.format(elem[0]))

            xmlout.append(xmlOutLine)

        ind -= indstep
        if '-const' in item[0][3]:
            xmlout.append('{}</module>'.format(' ' * ind))
        else:
            xmlout.append('{}</struct>'.format(' ' * ind))
        ind -= indstep
        while ind >= 2:
            xmlout.append('{}</module>'.format(' ' * ind))
            ind -= indstep

    xmlout.append('</types>')
    return xmlout
  
# file exporters
# XML data type definitions file -----------------------------------------------------
def export_xml_type_file(trec, typeFileName, typeNameList=[]):
    # wrap the types in header and footer
    xmlTypeFile = []
    xmlTypeFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    xmlTypeFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_dds_topic_types.xsd">')
    xmlTypeFile.extend(export_xml_type(trec))
    xmlTypeFile.append('</dds>')

    # write to file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in xmlTypeFile:
        f.write(line + '\n')
    f.close()
    return str(typeFileName)



# RTI Connector XML config file ----------------------------------------------------------
def export_xml_connector_cfg_file(trec, typeFileName, typeNameList):
    # wrap the types in header and footer
    connectorFile = []
    connectorFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    connectorFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    connectorFile.append('    xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_dds_topic_types.xsd">')
    connectorFile.append('  <qos_library name="QosLibrary">')
    connectorFile.append('    <qos_profile name="DefaultProfile" base_name="BuiltinQosLibExp::Generic.StrictReliable" is_default_qos="true">')
    connectorFile.append('      <participant_qos>')
    connectorFile.append('        <transport_builtin>')
    connectorFile.append('          <mask>UDPV4 | SHMEM</mask>')
    connectorFile.append('        </transport_builtin>')
    connectorFile.append('      </participant_qos>')
    connectorFile.append('      <datawriter_qos>')
    connectorFile.append('        <property>')
    connectorFile.append('          <value>')
    connectorFile.append('            <element>')
    connectorFile.append('              <name>dds.data_writer.history.memory_manager.fast_pool.pool_buffer_max_size</name>')
    connectorFile.append('              <value>4096</value>')
    connectorFile.append('            </element>')
    connectorFile.append('          </value>')
    connectorFile.append('        </property>')
    connectorFile.append('      </datawriter_qos>')
    connectorFile.append('    </qos_profile>')
    connectorFile.append('  </qos_library>')
    # get XML data type info
    connectorFile.extend(export_xml_type(trec))
    connectorFile.append('  <domain_library name="MyDomainLibrary">')
    connectorFile.append('    <domain name="MyDomain" domain_id="0">')
    # register the typenames
    for tTmp in typeNameList:
        connectorFile.append('      <register_type name="{}::msg::dds_::{}_" type_ref="{}::msg::dds_::{}_"/>'.format(tTmp[2],tTmp[1],tTmp[2],tTmp[1]))
        connectorFile.append('      <topic name="rt/topic_{}" register_type_ref="{}::msg::dds_::{}_"/>'.format(tTmp[1], tTmp[2], tTmp[1]))
    connectorFile.append('    </domain>')
    connectorFile.append('  </domain_library>')
    connectorFile.append('  <domain_participant_library name="MyParticipantLibrary">')
    connectorFile.append('    <domain_participant name="MyDPart" domain_ref="MyDomainLibrary::MyDomain">')
    # create publishers/dataWriters
    for tTmp in typeNameList:
        connectorFile.append('      <publisher name="dds{}Pub">'.format(tTmp[1]))
        connectorFile.append('        <data_writer name="dds{}Writer" topic_ref="rt/topic_{}" />'.format(tTmp[1], tTmp[1]))
        connectorFile.append('      </publisher>')
    # also create subscribers/dataReaders
    #for tTmp in typeNameList:
    #    connectorFile.append('      <subscriber name="dds{}Sub">'.format(tTmp[1]))
    #    connectorFile.append('        <data_reader name="dds{}Reader" topic_ref="rt/topic_{}" />'.format(tTmp[1], tTmp[1]))
    #    connectorFile.append('      </subscriber>')
    connectorFile.append('    </domain_participant>')
    connectorFile.append('  </domain_participant_library>')
    connectorFile.append('</dds>')

    # write to XML config file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in connectorFile:
        f.write(line + '\n')
    f.close()

    # now create a python application example (publish-only)
    with open('./xmlp/exports/connector_pub.py.txt') as fr:
        frbuf = fr.readlines()
    fr.close()

    idx = 0
    while idx < len(frbuf):
        # <%$<GroupXMLFileName>$%> = replace with the Connector XML file name
        if '<%$<GroupXMLFileName>$%>' in frbuf[idx]:
            frbuf[idx] = frbuf[idx].replace('<%$<GroupXMLFileName>$%>', Path(typeFileName).name)

        # <%$<ListPubWriters>$%> = place to insert pub/writers for each data type.
        elif '<%$<ListPubWriters>$%>' in frbuf[idx]:
            frbuf.pop(idx)
            for typName in typeNameList:
                # typName[0=idKey, 1=typeName, 2=typePath, 3=dbFileName]
                frbuf.insert(idx, '    {}_Writer = connector.get_output("dds{}Pub::dds{}Writer")\n'.format(typName[1],typName[1],typName[1]))
                idx += 1

        # <%$<ListWriteOps>$%> = place to insert write() calls for each datawriter
        elif '<%$<ListWriteOps>$%>' in frbuf[idx]:
            frbuf.pop(idx)
            for typName in typeNameList:
                frbuf.insert(idx, '        {}_Writer.write()\n'.format(typName[1]))
                idx += 1
        idx += 1

    # write the app source code file
    pyFileName = typeFileName.replace('.xml', '_app.py')
    fw = open(pyFileName, "w")
    for line in frbuf:
        fw.write(line)
    fw.close

    return typeFileName

# return a list containing the XML of the passed-in type collection
def type_to_string_list(trec):
    return export_xml_type(trec)

# RTI Routing Service XML config file ----------------------------------------------------------
def export_xml_routsvc_cfg_file(trec, typeFileName, typeNameList):
    # wrap the types in header and footer
    configFile = []
    configFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    configFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    configFile.append('     xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_routing_service.xsd">')
    # QoS library
    configFile.append('  <qos_library name="QosLibrary">')
    configFile.append('    <qos_profile name="DefaultProfile" base_name="BuiltinQosLibExp::Generic.BestEffort" is_default_qos="true">')
    configFile.append('      <participant_qos>')
    configFile.append('        <transport_builtin>')
    configFile.append('          <mask>UDPV4 | SHMEM</mask>')
    configFile.append('        </transport_builtin>')
    configFile.append('      </participant_qos>')
    configFile.append('    </qos_profile>')
    configFile.append('  </qos_library>')
    # data type info 
    configFile.extend(export_xml_type(trec))
    # routing service
    configFile.append('  <routing_service name="MyRoutingService">')
    configFile.append('    <domain_route name="DomainRoute" enabled="true">')
    configFile.append('      <participant name="1">')
    configFile.append('        <domain_id>0</domain_id>')
    configFile.append('      </participant>')
    configFile.append('      <participant name="2">')
    configFile.append('        <domain_id>1</domain_id>')
    configFile.append('      </participant>')
    # route all types from 1 to 2
    configFile.append('      <session name="Session" enabled="true">')
    configFile.append('        <topic_route name="OneToTwo">')
    configFile.append('          <input participant="1">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('            <registered_type_name>{}::msg::dds_::{}_</registered_type_name>'.format(tTmp[2], tTmp[1]))
        configFile.append('            <topic_name>rt/topic_{}</topic_name>'.format(idx))
    configFile.append('          </input>')
    configFile.append('          <output>')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('            <registered_type_name>{}::msg::dds_::{}_</registered_type_name>'.format(tTmp[2], tTmp[1]))
        configFile.append('            <topic_name>rt/topic_{}</topic_name>'.format(idx))
    configFile.append('          </output>')
    configFile.append('        </topic_route>')
    configFile.append('      </session>')
    configFile.append('    </domain_route>')
    configFile.append('  </routing_service>')
    configFile.append('</dds>')

    # write to file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in configFile:
        f.write(line + '\n')
    f.close()
    return typeFileName

# RTI Recording Service XML config file ----------------------------------------------------------
def export_xml_recsvc_cfg_file(trec, typeFileName, typeNameList):
    # wrap the types in header and footer
    configFile = []
    configFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    configFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    configFile.append('     xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_recording_service.xsd">')
    # QoS library
    configFile.append('  <qos_library name="QosLibrary">')
    configFile.append('    <qos_profile name="DefaultProfile" base_name="BuiltinQosLibExp::Generic.BestEffort" is_default_qos="true">')
    configFile.append('      <participant_qos>')
    configFile.append('        <transport_builtin>')
    configFile.append('          <mask>UDPV4 | SHMEM</mask>')
    configFile.append('        </transport_builtin>')
    configFile.append('      </participant_qos>')
    configFile.append('    </qos_profile>')
    configFile.append('  </qos_library>')
    # data type info 
    configFile.extend(export_xml_type(trec))
    # recording service
    configFile.append('  <recording_service name="MyRecordingService">')
    configFile.append('    <domain_participant name="MyRecSvcParticipant">')
    configFile.append('      <domain_id>0</domain_id>')
    configFile.append('      <participant_qos base_name="QosLibrary::DefaultProfile"/>')
    for tTmp in typeNameList:
        configFile.append('      <registered_type_name>{}::msg::dds_::{}_</registered_type_name>'.format(tTmp[2], tTmp[1]))
    configFile.append('    </domain_participant>')
    configFile.append('    <session default_participant_ref="MyRecSvcParticipant">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('      <topic name="rt/topic_{}">'.format(idx))
        configFile.append('        <registered_type_name>{}::msg::dds_::{}_</registered_type_name>'.format(tTmp[2], tTmp[1]))
        configFile.append('      </topic>')
    configFile.append('    </session>')
    configFile.append('  </recording_service>')
    configFile.append('</dds>')

    # write to file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in configFile:
        f.write(line + '\n')
    f.close()
    return typeFileName

# RTI Web Integration Service XML config file ----------------------------------------------------------
def export_xml_webintsvc_cfg_file(trec, typeFileName, typeNameList):
    # wrap the types in header and footer
    configFile = []
    configFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    configFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    configFile.append('     xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_web_integration_service.xsd">')
    # data type info 
    configFile.extend(export_xml_type(trec))
    # QoS library
    configFile.append('  <qos_library name="QosLibrary">')
    configFile.append('    <qos_profile name="DefaultProfile" base_name="BuiltinQosLibExp::Generic.BestEffort" is_default_qos="true">')
    configFile.append('      <participant_qos>')
    configFile.append('        <transport_builtin>')
    configFile.append('          <mask>UDPV4 | SHMEM</mask>')
    configFile.append('        </transport_builtin>')
    configFile.append('      </participant_qos>')
    configFile.append('    </qos_profile>')
    configFile.append('  </qos_library>')
    # domain
    configFile.append('  <domain_library name="WebIntSvcDomainLibrary">')
    configFile.append('    <domain name="WebIntDomain" domain_id="0">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('      <register_type name="{}::msg::dds_::{}_" type_ref="{}::msg::dds_::{}_" />'.format(tTmp[2], tTmp[1], tTmp[2], tTmp[1]))
        configFile.append('      <topic name="topic_{}" register_type_ref="{}::msg::dds_::{}_" />'.format(idx, tTmp[2], tTmp[1]))
    configFile.append('    </domain>')
    configFile.append('  </domain_library>')
    # web integration service
    configFile.append('  <web_integration_service name="webIntExample">')
    configFile.append('    <application name="exampleApp">')
    configFile.append('      <domain_participant name="MyParticipant"')
    configFile.append('            domain_ref="WebIntSvcDomainLibrary::WebIntDomain" >')
    configFile.append('        <publisher name="MyPublisher">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('          <data_writer name="My{}Writer" topic_ref="topic_{}" />'.format(tTmp[1], idx))
    configFile.append('        </publisher>')
    configFile.append('        <subscriber name="MySubscriber">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('          <data_reader name="My{}Reader" topic_ref="topic_{}" />'.format(tTmp[1], idx))
    configFile.append('        </subscriber>')
    configFile.append('        <participant_qos base_name="QosLibrary::DefaultProfile" />')
    configFile.append('      </domain_participant>')
    configFile.append('    </application>')
    configFile.append('  </web_integration_service>')
    configFile.append('</dds>')

    # write to file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in configFile:
        f.write(line + '\n')
    f.close()
    return typeFileName

# RTI Prototyper XML config file ----------------------------------------------------------
def export_xml_prototyper_cfg_file(trec, typeFileName, typeNameList):
    # wrap the types in header and footer
    configFile = []
    configFile.append('<?xml version="1.0" encoding="UTF-8"?>')
    configFile.append('<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    configFile.append('     xsi:noNamespaceSchemaLocation="http://community.rti.com/schema/6.1.0/rti_dds_profiles.xsd">')
    # QoS library
    configFile.append('  <qos_libraryname="qosLibrary">')
    configFile.append('    <qos_profilename="TransientDurability" is_default_qos="true">')
    configFile.append('      <datawriter_qos>')
    configFile.append('        <durability>')
    configFile.append('          <kind>TRANSIENT_LOCAL_DURABILITY_QOS</kind>')
    configFile.append('        </durability>')
    configFile.append('        <reliability>')
    configFile.append('          <kind>RELIABLE_RELIABILITY_QOS</kind>')
    configFile.append('        </reliability>')
    configFile.append('        <history>')
    configFile.append('          <kind>KEEP_LAST_HISTORY_QOS</kind>')
    configFile.append('          <depth>20</depth>')
    configFile.append('        </history>')
    configFile.append('      </datawriter_qos>')
    configFile.append('      <datareader_qos>')
    configFile.append('        <durability>')
    configFile.append('          <kind>TRANSIENT_LOCAL_DURABILITY_QOS</kind>')
    configFile.append('        </durability>')
    configFile.append('        <reliability>')
    configFile.append('          <kind>RELIABLE_RELIABILITY_QOS</kind>')
    configFile.append('        </reliability>')
    configFile.append('        <history>')
    configFile.append('          <kind>KEEP_LAST_HISTORY_QOS</kind>')
    configFile.append('          <depth>10</depth>')
    configFile.append('        </history>')
    configFile.append('      </datareader_qos>')
    configFile.append('    </qos_profile>')
    configFile.append('  </qos_library>')
    # data type info 
    configFile.extend(export_xml_type(trec))
    # domain
    configFile.append('  <domain_library name="MyDomainLibrary">')
    configFile.append('    <domain name="MyProtoDomain" domain_id="0">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('      <register_type name="{}::msg::dds_::{}_" kind="dynamicData" type_ref="{}::msg::dds_::{}_" />'.format(tTmp[2], tTmp[1], tTmp[2], tTmp[1]))
        configFile.append('      <topic name="topic_{}" register_type_ref="{}::msg::dds_::{}_"/>'.format(idx, tTmp[2], tTmp[1]))
    configFile.append('    </domain>')
    configFile.append('  </domain_library>')
    # participant
    configFile.append('  <participant_library name="MyParticipantLibrary">')
    configFile.append('    <domain_participant name="PublicationParticipant" domain_ref="MyDomainLibrary::MyProtoDomain">')
    configFile.append('      <publisher name="MyPublisher">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('        <data_writer name="{}Writer" topic_ref="topic_{}">'.format(tTmp[1], idx))
        configFile.append('          <datawriter_qos name="{}_writer_qos" base_name="qosLibrary::TransientDurability"/>'.format(tTmp[1]))
        configFile.append('        </data_writer>')
    configFile.append('      </publisher>')
    configFile.append('    </domain_participant>')
    configFile.append('    <domain_participant name="SubscriptionParticipant" domain_ref="MyDomainLibrary::MyProtoDomain">')
    configFile.append('      <subscriber name="MySubscriber">')
    for idx, tTmp in enumerate(typeNameList):
        configFile.append('        <data_reader name="{}Reader" topic_ref="topic_{}">'.format(tTmp[1], idx))
        configFile.append('          <datareader_qos name="{}_reader_qos" base_name="qosLibrary::TransientDurability"/>'.format(tTmp[1]))
        configFile.append('        </data_reader>')
    configFile.append('      </subscriber>')
    configFile.append('    </domain_participant>')
    configFile.append('  </participant_library>')
    configFile.append('</dds>')

    # write to file
    if not typeFileName.endswith('.xml'):
        typeFileName = typeFileName + '.xml'
    f = open(typeFileName, "w")
    for line in configFile:
        try:
            f.write(line + '\n')
        except Exception:
            pass
    f.close()
    return typeFileName
