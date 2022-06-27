#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
import sqlite3
import json
from . import hashutil, types

class SQL3Util():

    def __init__(self, dbName):
        self.dbName = dbName
        self.connection = sqlite3.connect(self.dbName)
        self.cursor = self.connection.cursor()

    # close the database
    def database_close(self):
        self.connection.close()

    # commit any changes
    def database_commit(self):
        self.connection.commit()

    # create the tables for datatypes, typemembers
    def create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS datatypes (idkey TEXT PRIMARY KEY, typeName TEXT, typePath TEXT, typeKind TEXT, inherits TEXT, memberList TEXT, tags TEXT, flags TEXT, notes TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS typemembers (idkey TEXT PRIMARY KEY, memberName TEXT, typeName TEXT, typePath TEXT, attributes TEXT, idkeyRef TEXT, valdefs TEXT, tags TEXT, flags TEXT, notes TEXT)")

    # insert this type (dict) into the datatypes table, merge the TAGS if row already exists
    # columns: idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags, notes
    def datatype_insert(self, typeinfo):
        # hash the non-TAG contents to create a unique ID
        idkey = hashutil.hash_datatype(typeinfo)
        # fetch the record if it exists
        dTypeList = self.cursor.execute('SELECT tags FROM datatypes WHERE idkey=?', (idkey,)).fetchall()
        tagSet = set(typeinfo['tags'])
        if len(dTypeList) > 0:
            # should be only 1 record
            if len(dTypeList) > 1:
                print("ERROR ------ sql3db.py line 28-ish: {}".format(dTypeList))

            # add the current tag to the TAGS retrieved
            for tagP in dTypeList:
                for tagM in tagP:
                    tagN = json.loads(tagM)
                    for tag in tagN:
                        tagSet.add(tag)

        tagString = json.dumps(list(tagSet))

        self.cursor.execute("INSERT or REPLACE INTO datatypes (idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                            (idkey, typeinfo['typeName'], typeinfo['typePath'], typeinfo['typeKind'], typeinfo['inherits'], typeinfo['memberList'], tagString, typeinfo['flags'], typeinfo['notes']))
        return idkey

    # insert this data member into the 'typemembers' table, merge the TAGS if row already exists
    # columns: idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, tags, flags, notes
    def member_insert(self, member):
        # Hash contents to get the member IDKEY
        idkey = hashutil.hash_member(member)
        tagSet = set(member['tags'])
        # fetch the record if it exists
        tMemberList = self.cursor.execute('SELECT tags FROM typemembers WHERE idkey=?', (idkey,)).fetchall()
        if len(tMemberList) > 0:
            # should be only 1 record
            if len(tMemberList) > 1:
                print("ERROR ------ sql3db.py line 53-ish: {}".format(tMemberList))

            # add the current tag to the TAGS retrieved
            for tagP in tMemberList:
                for tagM in tagP:
                    tagN = json.loads(tagM)
                    for tag in tagN:
                        tagSet.add(tag)
        tagString = json.dumps(list(tagSet))

        self.cursor.execute("INSERT OR REPLACE INTO typemembers (idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, tags, flags, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                            (idkey, member['memberName'], member['typeName'], member['typePath'], member['attributes'], member['idkeyRef'], member['valdefs'], tagString, member['flags'], member['notes']))
        return idkey

    # recursive finder: return a collection of records and their dependencies that match a typeName
    def get_record_tree_by_typename_or_idkey_recurs(self, tags, typeRef, idkey=0):
        if idkey != 0:            # if an IDKEY was passed, use it first
            dTypeList = self.cursor.execute('SELECT idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags FROM datatypes WHERE idkey=?', (idkey,)).fetchall()
        elif '/' in typeRef:
            # otherwise, find by path/type name (such as 'std_msgs/')
            tparts = typeRef.split('/')
            typeName = tparts[-1]
            typeGroup = tparts[0]
            dTypeList = self.cursor.execute('SELECT idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags FROM datatypes WHERE typeName=? AND typePath=?', (typeName,typeGroup,)).fetchall()
        else:
            # else find by type name only
            typeName = typeRef
            dTypeList = self.cursor.execute('SELECT idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags FROM datatypes WHERE typeName=?', (typeName,)).fetchall()

        if dTypeList == None:
            return []
        if len(tags) != 0:      # filter-out any rows with non-matching tags
            tmpList = []
            for dType in dTypeList:
                tagmatch = False
                for tag in tags:
                    if tag in dType[6]:
                        tagmatch = True
                if tagmatch == True:
                    tmpList.append(dType)
            dTypeList = tmpList
            
        typeGroup = []
        rtnVal = []
        const_id = ''

        for dType in dTypeList:
            typeGroup.append(dType)

            # flag any inherited types or modules for export
            if dType[4]:
                const_id = json.loads(dType[4])[0]

            # work on the list of members
            elemIdList = json.loads(dType[5])
            for elemId in elemIdList:
                # get each member, add to list.  TAGS should match from here on.
                elemInfo = self.cursor.execute('SELECT idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, flags, notes FROM typemembers WHERE idkey=?',(elemId,)).fetchall()
                if len(elemInfo) > 0:
                    typeGroup.append(elemInfo)
                else:
                    # Not found?
                    print('data type ID: {} not found'.format(elemId))


        rtnVal.append(typeGroup)

        # if there was a possible '_Constants' module; query it by recursion
        if const_id != '':
            recRtn = self.get_record_tree_by_typename_or_idkey_recurs(tags, '', const_id)
            if len(recRtn) > 0:
                rtnVal.append(recRtn[0])

        # loop-through the typemembers to see if another recursion is needed
        for item in rtnVal:
            for elem in item[1:]:
                needidkey = elem[0][5]
                if len(needidkey) > 2:
                    # is this ID already in the rtnVal array?
                    putIntoRtn = True
                    for dt in rtnVal:
                        if dt[0][0] == needidkey:
                            putIntoRtn = False
                    if putIntoRtn:
                        recRtn = self.get_record_tree_by_typename_or_idkey_recurs(tags, '', needidkey)
                        if len(recRtn) > 0:
                            for typeBlock in recRtn:
                                rtnVal.append(typeBlock)
        return rtnVal


    def get_record_tree_by_typename_or_idkey(self, tags, typeRef, idkey=0):
        # call the recursive finder
        rtnVal = self.get_record_tree_by_typename_or_idkey_recurs(tags, typeRef, idkey)

        # remove duplicates (FIXME: prevent duplicates from happening)
        hashset = set()
        for item in reversed(rtnVal):
            if item[0][0] in hashset:
                rtnVal.remove(item)
            else:
                hashset.add(item[0][0])

        return rtnVal


    # find a type record by name(may have path elements).  Returns record IDKey list
    def path_record_find_by_name_path(self, tagmatch, typeName, typePath=''):
        if typePath == '':
            dbRtn = self.cursor.execute('SELECT idkey, tags FROM datatypes WHERE typeName=?', (typeName,)).fetchall()
        else:
            dbRtn = self.cursor.execute('SELECT idkey, tags FROM datatypes WHERE typeName=? AND typePath=?', (typeName,typePath,)).fetchall()
        
        # do the tags match?
        rtnVal = []
        for dbId, dbTag in dbRtn:
            dbtags = json.loads(dbTag)
            if all(tags in dbtags for tags in tagmatch):
                rtnVal.append(dbId)
        return rtnVal

    # go through the typemembers & try to fix any unknown idKeyRef(-1)
    def resolve_member_trefs(self, tags):
        # get all typemembers, process only those with idKeyRef == '-1'
        allMembers = self.cursor.execute('SELECT idkey, typeName, typePath, idKeyRef, flags FROM typemembers').fetchall()
        for idkey, typeName, typePath, idKeyTag, flags in allMembers:
            # if a tag was used, then filter out any non-matches
            if idKeyTag == '-1':
                # first, search by typePath and typeName
                findIdx = self.path_record_find_by_name_path(tags, typeName, typePath)
                if len(findIdx) == 0:
                    # Grr.. some ros2 type references use the wrong path or capitalization, but ROS2 doesn't seem to mind.
                    # try another search for the type name only (remove the path).
                    findIdx = self.path_record_find_by_name_path(tags, typeName)
                    if len(findIdx) == 0:
                        # this typename is STILL not resolved.  Try a case-insensitive search?
                        # FIXME

                        # set a flag in this datatype member that it has an unresolved type
                        self.cursor.execute('SELECT flags FROM typemembers WHERE idkey=?', (idkey,))
                        memberFlagSet = set(self.cursor.fetchall())
                        memberFlagSet.add('UNRES')
                        self.cursor.execute('UPDATE typemembers SET flags=? WHERE idkey=?', (json.dumps(list(memberFlagSet)), idkey,))
                        print('No match found for {}:{}/{}'.format(idkey, typePath, typeName))
                    else:
                        if len(findIdx) > 1:
                            # multiple results have been returned, ask the user for help
                            printPath = typePath
                            if 'IMPLIEDPATH' in flags:
                                printPath = '(no-path)'
                            print("FIXME: ambiguous path/name({}/{}) in source file (under {}) returns {} possible matches:".format(printPath, typeName, typePath, len(findIdx)))
                            for idk in findIdx:
                                tmpDType = self.cursor.execute('SELECT typeName, typePath FROM datatypes WHERE idkey=?', (idk,)).fetchall()[0]
                                print('   ID: {}, {}/{}'.format(idk, tmpDType[1], tmpDType[0]))
                            print("   This can be resolved by editing the source file to add a definitive path prefix")

                        else:
                            # We've found a potential match for this type reference,
                            # IF the typePath was implied by being in the same path as the parent -- OK to use
                            if 'IMPLIEDPATH' in flags:
                                self.cursor.execute('UPDATE typemembers SET idkeyRef=? WHERE idkey=?', (findIdx[0], idkey,))
                            else:
                                # IF not implied from parent -- this requires edits to the source file
                                # ** Let the user know of the trouble, and of the potential solution
                                print('FIXME: data member references: "{}/{}", but that type cannot be found'.format(typePath, typeName))
                                newPathType = self.cursor.execute('SELECT typeName, typePath FROM datatypes WHERE idkey=?', (findIdx[0],)).fetchall()[0]
                                print('       a potential solution is "{}/{}", please update the source file'.format(newPathType[1], newPathType[0]))
                        
                else:
                    # should have just 1 returned idkey; too many tags in use?
                    if len(findIdx) > 1:
                        print("WARN: path/name:({}/{}) with tags({}), returns {} matches:".format(typePath, typeName, tags, len(findIdx)))
                        for idk in findIdx:
                            tmpDType = self.cursor.execute('SELECT typeName, typePath FROM datatypes WHERE idkey=?', (idk,)).fetchall()[0]
                            print('   ID: {}, {}/{}'.format(idk, tmpDType[1], tmpDType[0]))
                        print("   Defaulting to use the first match in the above list")

                    # update the idkeyref for this member
                    self.cursor.execute('UPDATE typemembers SET idkeyRef=? WHERE idkey=?', (findIdx[0], idkey,))

    # step through the datatypes, check each member for valid ID, set flag if trouble
    def datatypes_flag_member_errors(self):
        # get all the members, find any that have UNDEF ID's
        undefMembers = []
        memberList = self.typemembers_readall()
        for thisMember in memberList:
            if thisMember[5] == '-1':
                #print('MemberUndef: {}:{}/{} {}'.format(thisMember[0], thisMember[3], thisMember[2], thisMember[1]))
                undefMembers.append(thisMember[0])

        if len(undefMembers) > 0:
            # step through each type, see if it has any undefMembers
            typeList = self.datatypes_readall()
            for thisType in typeList:
                typeMembers = json.loads(thisType[5])
                for memberId in typeMembers:
                    if memberId in undefMembers:
                        #print("FlagUndefTypeMember in {}/{}".format(thisType[2], thisType[1]))
                        # add an 'UNRES' flag to the type record
                        typeFlags = []
                        if len(thisType[7]) > 0:
                            typeFlags = list(json.loads(thisType[7]))
                        typeFlags.append('UNRES')
                        self.cursor.execute('UPDATE datatypes SET flags=? WHERE idkey=?', (json.dumps(typeFlags), thisType[0],))
            self.database_commit()


    def datatypes_readall(self):
        return self.cursor.execute("SELECT idkey, typeName, typePath, typeKind, inherits, memberList, tags, flags, notes FROM datatypes").fetchall()

    def typemembers_readall(self):
        return self.cursor.execute("SELECT idkey, memberName, typeName, typePath, attributes, idkeyRef, valdefs, flags, notes FROM typemembers").fetchall()

    # this supports the GUI, returning a list of [idkey, name, path, keys, count of members(non-recurs)]
    def datatypes_treevalues(self):
        rtnList = []
        tmpTree = self.cursor.execute("SELECT idkey, typeName, typePath, memberList, tags FROM datatypes").fetchall()
        for dType in tmpTree:
            rtnItem = [dType[0], dType[1], dType[2], dType[4], str(len(memberList)).zfill(2)]
            rtnList.append(rtnItem)
        return rtnList

    # this supports the GUI, returning a dict of idkey: [name, path, keys, count of members(non-recurs), err]
    def datatypes_reftree(self):
        rtnDict = {}
        tmpTree = self.cursor.execute("SELECT idkey, typeName, typePath, memberList, tags, flags, typeKind FROM datatypes").fetchall()
        for dType in tmpTree:
            keyString = ' '.join(json.loads(dType[4]))
            memberError = ''
            if len(dType[5]) > 0:
                memberError = 'UNDEF'
            if dType[6].startswith('msg'):
                rosPattern = '/msg'
            elif dType[6].startswith('srv'):
                rosPattern = '/srv'
            elif dType[6].startswith('act'):
                rosPattern = '/action'
            else:
                rosPattern = ''
            fullTypePath = '{}{}'.format(dType[2], rosPattern)
            rtnDict[dType[0]] = [dType[1],fullTypePath, keyString, str(len(json.loads(dType[3]))).zfill(2), memberError]
        return rtnDict

    # update a row's TAGS, by idKey
    def update_tags(self, idKey, newTags):
        self.cursor.execute('UPDATE datatypes SET tags=? WHERE idkey=?', (newTags, idKey,))

