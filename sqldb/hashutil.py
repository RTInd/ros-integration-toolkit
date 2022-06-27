#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
from hashlib import blake2b
import base64, json

# return a 96-bit, BASE64-encoded 16-char hash of the passed-in member(dict); type or const
# all members: idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, tags, flags, notes
# create a hash from: memberName, typeName, typePath, attributes, idkeyRef, valdefs,       flags
def hash_member(member):
    h = blake2b(digest_size=12)
    if len(member['memberName']) > 0:
        h.update(member['memberName'].encode())
    if len(member['typeName']) > 0:
        h.update(member['typeName'].encode())
    if len(member['typePath']) > 0:
        h.update(member['typePath'].encode())
    if len(member['attributes']) > 0:
        h.update(member['attributes'].encode())
    if len(member['idkeyRef']) > 0:
        h.update(member['idkeyRef'].encode())
    if len(member['valdefs']) > 0:
        h.update(member['valdefs'].encode())
    if len(member['flags']) > 0:
        h.update(member['flags'].encode())
    baseval = base64.b64encode(h.digest())
    return baseval.decode()

# return a 96-bit, BASE64-encoded 16-char hash of the passed-in datatype(dict); type or Constants
# datatypes: idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags, notes
# create hash from: typeName, typePath, typeKind, inherits, memberList,       flags
def hash_datatype(dtype):
    h = blake2b(digest_size=12)
    if len(dtype['typeName']) > 0:
        h.update(dtype['typeName'].encode())
    if len(dtype['typePath']) > 0:
        h.update(dtype['typePath'].encode())
    if len(dtype['typeKind']) > 0:
        h.update(dtype['typeKind'].encode())
    if len(dtype['inherits']) > 0:
        h.update(dtype['inherits'].encode())
    if len(dtype['memberList']) > 0:
        h.update(dtype['memberList'].encode())
    if len(dtype['flags']) > 0:
        h.update(dtype['flags'].encode())
    baseval = base64.b64encode(h.digest())
    return baseval.decode()

# return a hex string from a BASE64 encoded value 
# (expected to be 16-char string input; 96-bit hash)
def hex_from_hash_base64(hashval):
    hexval = base64.b64decode(hashval)
    return hexval.hex()

# given a list of strings (presumably containing 16-char hashId's),
# hash these together & return a 16-char hash string
def hash_list_of_strings(stringList):
    h = blake2b(digest_size=12)
    for hString in stringList:
        h.update(hString.encode())
    baseval = base64.b64encode(h.digest())
    return baseval.decode()
