#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
rosEmptyFiller = {
    'eType': 'uint8', 'eRef': 77, 'eSize': '', 'eName': 'structure_needs_at_least_one_member', 'eDefault': ''
}

idlroskeywords = [
    'abstract', 'any', 'alias', 'attribute', 'bitfield', 'bitmask', 'bitset', 'boolean',
    'case', 'char', 'component', 'connector', 'const', 'consumes', 'context', 'custom', 
    'default', 'double', 'exception', 'emits', 'enum', 'eventtype', 'factory', 'FALSE', 
    'finder', 'fixed', 'float', 'getraises', 'home', 'import', 'in', 'inout', 
    'interface', 'local', 'long', 'manages', 'map', 'mirrorport', 'module', 'multiple', 
    'native', 'Object', 'octet', 'oneway', 'out', 'primarykey', 'private', 'port', 
    'porttype', 'provides', 'public', 'publishes', 'raises', 'readonly', 'setraises', 'sequence', 
    'short', 'string', 'struct', 'supports', 'switch', 'TRUE', 'truncatable', 'typedef', 
    'typeid', 'typename', 'typeprefix', 'unsigned', 'union', 'uses', 'ValueBase', 'valuetype', 
    'void', 'wchar', 'wstring', 'bool', 'byte', 'int8', 'uint8', 'int16', 
    'uint16', 'int32', 'uint32', 'int64', 'uint64', 'float32', 'float64'
]

# returns 1--100 if reserved or ROS primitive type, or -1 if a custom typename
def checkTypeId(typeName):
    for t in typeName.split(' '):
        if t in idlroskeywords:
            return str(idlroskeywords.index(t))
    return '-1'

# this is a placeholder ATM ------------------------------
# IDL type table
idlTypeLookupTable = { 
        #  1: boolean
        1: ['boolean'],
        #  2: char
        2: ['char'],
        #  3: 8-bit signless (byte/octet)
        3: ['octet'],
        #  4: 8-bit signed
        4: ['int8'],
        #  5: 8-bit unsigned
        5: ['uint8'],
        #  6: wchar
        6: ['wchar'],
        #  7: 16-bit signed
        7: ['int16', 'short'],
        #  8: 16-bit unsigned
        8: ['uint16', 'unsigned short'],
        #  9: 32-bit signed
        9: ['int32', 'long'],
        # 10: 32-bit unsigned
        10: ['uint32', 'unsigned long'],
        # 11: 64-bit signed
        11: ['int64', 'long long'],
        # 12: 64-bit unsigned
        12: ['uint64', 'unsigned long long'],
        # 13: 32-bit float
        13: ['float'],
        # 14: 64-bit float
        14: ['double'],
        # 15: 128-bit float
        15: ['long double'],
        # 16: string
        16: ['string'],
        # 17: wstring
        17: ['wstring']
}

# XML type table
xmlTypeLookupTable = { 
        #  1: boolean
        1: ['boolean'],
        #  2: char
        2: ['char8'],
        #  3: 8-bit signless (byte/octet)
        3: ['byte'],
        #  4: 8-bit signed
        4: ['int8'],
        #  5: 8-bit unsigned
        5: ['uint8'],
        #  6: wchar
        6: ['char16'],
        #  7: 16-bit signed
        7: ['int16'],
        #  8: 16-bit unsigned
        8: ['uint16'],
        #  9: 32-bit signed
        9: ['int32'],
        # 10: 32-bit unsigned
        10: ['uint32'],
        # 11: 64-bit signed
        11: ['int64'],
        # 12: 64-bit unsigned
        12: ['uint64'],
        # 13: 32-bit float
        13: ['float32'],
        # 14: 64-bit float
        14: ['float64'],
        # 15: 128-bit float
        15: ['float128'],
        # 16: string
        16: ['string'],
        # 17: wstring
        17: ['wstring']
}


# ROS type table
rosTypeLookupTable = { 
        #  1: boolean
        1: ['bool'],
        #  2: char
        # deprecated in ROS, use uint8
        #  3: 8-bit signless (byte/octet)
        # deprecated in ROS, use int8
        #  4: 8-bit signed
        4: ['int8', 'byte'],
        #  5: 8-bit unsigned
        5: ['uint8', 'char'],
        #  6: wchar
        # not used in ROS
        #  7: 16-bit signed
        7: ['int16'],
        #  8: 16-bit unsigned
        8: ['uint16'],
        #  9: 32-bit signed
        9: ['int32'],
        # 10: 32-bit unsigned
        10: ['uint32'],
        # 11: 64-bit signed
        11: ['int64'],
        # 12: 64-bit unsigned
        12: ['uint64'],
        # 13: 32-bit float
        13: ['float32'],
        # 14: 64-bit float
        14: ['float64'],
        # 15: 128-bit float
        # not used in ROS
        # 16: string
        16: ['string'],
        # 17: wstring
        17: ['wstring']
}


# given a type name and format (idl, xml, ros),
# returns a primitive type number or -1 if unknown type name
def typeNameToTypeNumber(typeName, typeFormat):
    if typeFormat == 'ros':
        typeTable = rosTypeLookupTable
    elif typeFormat == 'idl':
        typeTable = idlTypeLookupTable
    elif typeFormat == 'xml':
        typeTable = xmlTypeLookupTable
    else:
        print('typeNameToTypeNumber: unknown format({})'.format(typeFormat))
        return -2
    # find the type
    for typeNumLine in typeTable:
        if typeName in typeTable[typeNumLine]:
            return typeNumLine
    return -1

# given a type number and format (idl, xml, ros)
# returns a data type name for that format
def typeNumberToTypeName(typeNumber, typeFormat):
    if typeFormat == 'ros':
        typeTable = rosTypeLookupTable
    elif typeFormat == 'idl':
        typeTable = idlTypeLookupTable
    elif typeFormat == 'xml':
        typeTable = xmlTypeLookupTable
    else:
        print('typeNameToTypeNumber: unknown format({})'.format(typeFormat))
        return 'unknownFormat{}'.format(typeFormat)

    rtnType = typeTable.get(typeNumber)
    if rtnType == None:
        return 'NoTypeMatch({})'.format(typeNumber)
    else:
        return rtnType[0]

