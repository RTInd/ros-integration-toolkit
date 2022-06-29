#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
import os, platform
import json
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import scrolledtext
from sqldb import sql3db, hashutil
from idlp import idltypex
from xmlp import xmltypex
from rosp import rosparser
from cxxp import cxxcodex
from cfgx import cfgsettings
from pathlib import Path

class TypeRepoUI(tk.Tk):
	def __init__(self):
		super().__init__()
		# config file save/restore
		self.MyConfig = cfgsettings.CfgSettings(os.path.dirname(os.path.realpath(__file__)))

		# vars
		self.typeTreeRef = {}		# dict of type info loaded-from-file or scanned
		self.filterName = ''		# filters for typeName, typePath, keywords
		self.filterPath = ''
		self.filterKeys = ''
		self.my_cwd = os.path.dirname(os.path.realpath(__file__))
		self.scanFilePath = ''				# path to scan for data type files
		self.scanDBaseFilePath = ''			# path to write scan database result
		self.exportFilePath = os.path.dirname(os.path.realpath(__file__))			# path to export the output files
		# export filename vars
		self.exportFirstTypeSelected = ''	# type path_name selected first
		self.exportFileNameDefault = 'selected_type'	# default export filename (when no type is selected)
		self.exportFileNameBase = self.exportFileNameDefault	# base name of export file
		self.exportFileNameSuffix = ''							# suffix for export file to indicate which export target.
		self.checkedState = False			# toggle to check/uncheck all
		self.typeTreeSortReverse = False	# toggle to sort normal/reverse order
		self.dbFileName = ''				# name of database file to open
		self.dbFileNames = []				# list of database files opened

		# images
		self.box_checked = tk.PhotoImage('checked', file='./images/checked1.gif')
		self.box_unchecked = tk.PhotoImage('unchecked', file='./images/unchecked1.gif')

		# build and init the elements
		self.title("Integration Toolkit")
		self.geometry('{}x{}'.format(1200, 450))

		# add a menu bar
		self.m = tk.Menu(self)
		self.m_file=tk.Menu(self.m)
		self.m.add_cascade(menu=self.m_file, label="File")
		self.m_file.add_command(label="Open db...", command=lambda: self.event_generate("<<OpenFileDialog>>"))
		self.m_file.add_command(label="Unload all", command=lambda: self.event_generate("<<UnloadAllFromTree>>"))
		self['menu']=self.m

		# main containers
		self.top_frame = ttk.Frame(self, width=420, height=100)
		self.typetree_frame = ttk.Frame(self, width=420)
		self.status_frame = ttk.Frame(self, width=420, borderwidth=2, relief='sunken')
		self.preview_frame = ttk.Frame(self, borderwidth=2, relief='sunken')

		# layouts of main containers
		self.grid_rowconfigure(1, weight=1)
		self.grid_columnconfigure(1, weight=1)
		self.top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
		self.typetree_frame.grid(row=1, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
		self.status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
		self.preview_frame.grid(column=1, row=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

		# top frame: tabbed notebook w/tabs for 'Query' and 'Scan'
		self.tabControl = ttk.Notebook(self.top_frame)
		self.tabScan = ttk.Frame(self.tabControl)
		self.tabQuery = ttk.Frame(self.tabControl)
		self.tabEdit = ttk.Frame(self.tabControl)
		#self.tabSettings = ttk.Frame(self.tabControl)
		self.tabControl.add(self.tabQuery, text =f'{"Query & Export": ^20s}')
		self.tabControl.add(self.tabScan, text =f'{"Scan for Types": ^20s}')
		self.tabControl.add(self.tabEdit, text =f'{"Edit": ^20s}')
		#self.tabControl.add(self.tabSettings, text =f'{"Settings": ^20s}')

		# add content to tabs
		# Scan tab
		self.scanTabLabel = ttk.Label(self.tabScan, text='Scan your local filesystem for Data Type definition files')
		self.scanPathValue = tk.StringVar()
		self.scanPathValue.set(self.MyConfig.cfgVal['scanPath'])
		self.scanPath = ttk.Label(self.tabScan, textvar=self.scanPathValue, borderwidth=2, relief='groove', padding=3)
		self.scanPathButton = ttk.Button(self.tabScan, text="Scan Path..",  command=lambda: self.event_generate("<<SelectPathDialog>>"))
		self.scanTagsLabel = ttk.Label(self.tabScan, text='Tags:')
		self.scanTagsValue = tk.StringVar()
		self.scanTags = ttk.Entry(self.tabScan, textvariable=self.scanTagsValue)
		self.scanTypeLabel = ttk.Label(self.tabScan, text='FileTypes:')
		self.scanRosVar = tk.BooleanVar(value=True)
		self.scanTypeRos = ttk.Checkbutton(self.tabScan, text='ROS(msg/srv/action)', variable=self.scanRosVar, onvalue=True)
		#self.scanIdlVar = tk.BooleanVar(value=False)
		#self.scanTypeIdl = ttk.Checkbutton(self.tabScan, text='IDL', variable=self.scanIdlVar, onvalue=True)
		#self.scanXmlVar = tk.BooleanVar(value=False)
		#self.scanTypeXml = ttk.Checkbutton(self.tabScan, text='XML', variable=self.scanXmlVar, onvalue=True)
		# path to write database file
		self.scanDBasePathValue = tk.StringVar()
		self.scanDBasePathValue.set(self.my_cwd)
		self.scanDBasePath = ttk.Label(self.tabScan, textvar=self.scanDBasePathValue, borderwidth=2, relief='groove', padding=3)
		self.scanDBasePathButton = ttk.Button(self.tabScan, text="Output Path..",  command=lambda: self.event_generate("<<SelectDBasePathDialog>>"))
		# name of database file
		self.scanDBaseFileNameLabel = ttk.Label(self.tabScan, text='.db File Name:')
		self.scanDBaseFileNameValue = tk.StringVar()
		self.scanDBaseFileNameValue.set('')
		self.scanDBaseFileName = ttk.Entry(self.tabScan, textvariable=self.scanDBaseFileNameValue)

		self.scanLaunchButton = ttk.Button(self.tabScan, text="Start Scan", command=lambda: self.event_generate("<<StartScan>>"))

		# Query & Export tab
		# Left side: Query
		# labels
		self.queryTabLabel = ttk.Label(self.tabQuery, text='Search & export data types in your choice of format')
		self.queryIncLabel = ttk.Label(self.tabQuery, text='FILTER Include:')
		self.queryTNameLabel = ttk.Label(self.tabQuery, text='typeName: ')
		self.queryTPathLabel = ttk.Label(self.tabQuery, text='typePath: ')
		self.queryKeyWordLabel = ttk.Label(self.tabQuery, text='tag: ')
		# entry boxes
		self.nameQueryVar = tk.StringVar()
		self.nameQueryVar.trace("w", lambda name, index, mode, nameQueryVar=self.nameQueryVar: self.searchNameCallback('name', self.nameQueryVar))
		self.queryIncName = ttk.Entry(self.tabQuery, textvariable=self.nameQueryVar)

		self.pathQueryVar = tk.StringVar()
		self.pathQueryVar.trace("w", lambda name, index, mode, pathQueryVar=self.pathQueryVar: self.searchNameCallback('path', self.pathQueryVar))
		self.queryIncPath = ttk.Entry(self.tabQuery, textvariable=self.pathQueryVar)

		self.keysQueryVar = tk.StringVar()
		self.keysQueryVar.trace("w", lambda name, index, mode, keysQueryVar=self.keysQueryVar: self.searchNameCallback('keys', self.keysQueryVar))
		self.queryIncKeys = ttk.Entry(self.tabQuery, textvariable=self.keysQueryVar)

		# Right side: Export
		# labels
		self.exportTopLabel = ttk.Label(self.tabQuery, text='Export the selected types to a file')
		self.exportTypeLabel = ttk.Label(self.tabQuery, text='File Type:')

		# dictionary of export type labels and args
		self.exportArgLabels = {
			'idl': 'IDL Types File', 
			'idlcmake': 'Connext Pro C++11 Application', 
			'xml': 'XML Types File (Admin Console)', 
			'connector': 'Connector Python Application', 
			'routsvc': 'Routing Service Config File', 
			'recsvc': 'Recording Service Config File' 
			# 'persistsvc': 'Persistence Service Config File', 
			# 'queuesvc': 'Queuing Service Config File', 
			#'webintsvc': 'Web Integration Service Config File', 
			#'dbaseintsvc': 'Database Integration Service Config File', 
			#'prototyper': 'Prototyper Config File'} 
			#'xmlappcreate': 'XML-Based App Creation Config File'
		}

		# combobox to select export type
		self.cboxExportType = ttk.Combobox(self.tabQuery, values=list(self.exportArgLabels.values()),
			state='readonly',
			width=40)
		self.cboxExportType.set(self.exportArgLabels['idl'])

		# path and button
		self.exportPathButton = ttk.Button(self.tabQuery, text="Export to..",  command=lambda: self.event_generate("<<SelectExportPathDialog>>"))
		self.exportPathValue = tk.StringVar()
		self.exportPathValue.set(self.MyConfig.cfgVal['exportPath'])
		self.exportPath = ttk.Label(self.tabQuery, textvar=self.exportPathValue, borderwidth=2, relief='groove', padding=3)
		self.exportFileNameLabel = ttk.Label(self.tabQuery, text='File Name:')
		self.exportFileNameValue = tk.StringVar()
		self.exportFileName = ttk.Entry(self.tabQuery, textvariable=self.exportFileNameValue)

		self.buttonExpTypeInfo = ttk.Button(self.tabQuery, text='Create file', command=lambda: self.event_generate("<<ExportTypeFile>>"))

		# Edit tab
		self.editTabLabel = ttk.Label(self.tabEdit, text='Edit the TAGS for the selected types')
		self.currentTagsLabel = ttk.Label(self.tabEdit, text='Current Tags:')
		self.currentTagsVar = tk.StringVar()		# this holds the tags list
		self.currentTags = ttk.Label(self.tabEdit, textvariable=self.currentTagsVar, borderwidth=2, relief='groove', padding=3, anchor=tk.W)
		self.changeTagsLabel = ttk.Label(self.tabEdit, text='Change Tags:')
		self.changeTags = ttk.Entry(self.tabEdit)
		self.buttonAppendTags = ttk.Button(self.tabEdit, text='Append Tags', command=lambda: self.event_generate("<<AppendTagsToTypes>>"))
		self.buttonRemoveTags = ttk.Button(self.tabEdit, text='Remove Tags', command=lambda: self.event_generate("<<RemoveTagsInTypes>>"))
		self.buttonUpdateDBaseTags = ttk.Button(self.tabEdit, text='Write to Database', command=lambda: self.event_generate("<<UpdateDatabaseWithTags>>"))

		# Settings tab
		#self.settingsTabLabel = ttk.Label(self.tabSettings, text='Settings to control code generation')
		#self.setUnderscoreVar = tk.StringVar()
		#self.settingsAddUnderscore = ttk.Checkbutton(self.tabSettings, text="ROS2: Append underscore to Type Name", variable=self.setUnderscoreVar)
		#self.setDdsPathVar = tk.StringVar()
		#self.settingsAddDdsToPath = ttk.Checkbutton(self.tabSettings, text="ROS2: Add 'dds_' to Type Path ('*_msgs::msg::dds_::*')", variable=self.setDdsPathVar)
		#self.setStringSize = ttk.Entry(self.tabSettings)
		#self.setStringSizeLabel = ttk.Label(self.tabSettings, text='Max length of Strings')
		#self.setSequenceSize = ttk.Entry(self.tabSettings)
		#self.setSequenceSizeLabel = ttk.Label(self.tabSettings, text='Max length of Sequences')
		#self.setIdlVer4 = tk.StringVar()
		#self.settingsIdlVer4 = ttk.Radiobutton(self.tabSettings, text="Basic types as IDLv4 ('int32')", variable=self.setIdlVer4, value=0, command=self.SettingsIdlVerCallback)
		#self.settingsIdlPreV4 = ttk.Radiobutton(self.tabSettings, text="Basic types as Pre-v4 ('long')", variable=self.setIdlVer4, value=1, command=self.SettingsIdlVerCallback)
		#self.setIdlVer4.set('0')
		#self.setUnderscoreVar.set('1')
		#self.setDdsPathVar.set('1')

		# layout of top frame
		self.top_frame.grid_columnconfigure(0, weight=1)
		self.tabControl.grid(row=0, columnspan=4, sticky=(tk.W, tk.E))
		self.tabControl.grid_columnconfigure(0, weight=1)
		self.tabQuery.grid_columnconfigure(2, weight=1)
		self.tabScan.grid_columnconfigure(4, weight=1)

		self.scanTabLabel.grid(column=0, row=0, columnspan=4, sticky=tk.W)
		self.scanPathButton.grid(column=0, row=1)
		self.scanPath.grid(column=1, row=1)
		self.scanTagsLabel.grid(column=0, row=2)
		self.scanTags.grid(column=1, row=2, sticky=(tk.W))
		self.scanTypeLabel.grid(column=0, row=3)
		self.scanTypeRos.grid(column=1, row=3, sticky=(tk.W))
		#self.scanTypeIdl.grid(column=2, row=3, sticky=(tk.W))
		#self.scanTypeXml.grid(column=3, row=3, sticky=(tk.W))
		self.scanDBasePathButton.grid(column=0, row=4)
		self.scanDBasePath.grid(column=1, row=4)
		self.scanDBaseFileNameLabel.grid(column=0, row=5)
		self.scanDBaseFileName.grid(column=1, row=5)
		self.scanLaunchButton.grid(column=4, row=4, sticky=(tk.E), ipady=10, ipadx=10)

		self.tabQuery.grid_columnconfigure(2, weight=1)
		self.queryTabLabel.grid(column=0, row=0, columnspan=2, sticky=(tk.W, tk.E))
		self.queryIncLabel.grid(column=0, row=1, sticky=(tk.E))
		self.queryTNameLabel.grid(column=0, row=2, sticky=(tk.E))
		self.queryTPathLabel.grid(column=0, row=3, sticky=(tk.E))
		self.queryKeyWordLabel.grid(column=0, row=4, sticky=(tk.E,tk.N))
		self.queryIncName.grid(column=1, row=2, sticky=(tk.W))
		self.queryIncPath.grid(column=1, row=3, sticky=(tk.W))
		self.queryIncKeys.grid(column=1, row=4, sticky=(tk.W, tk.N))
		self.exportTopLabel.grid(column=3, row=2, columnspan=2, sticky=tk.W)
		self.exportTypeLabel.grid(column=3, row=3, sticky=tk.E)
		self.cboxExportType.grid(column=4, row=3, sticky=(tk.E, tk.W))
		self.exportPathButton.grid(column=3, row=4, sticky=(tk.E))
		self.exportPath.grid(column=4, row=4, sticky=(tk.E, tk.W))
		self.exportFileNameLabel.grid(column=3, row=5, sticky=(tk.E, tk.W))
		self.exportFileName.grid(column=4, row=5, sticky=(tk.E, tk.W))
		self.buttonExpTypeInfo.grid(column=4, row=0, sticky=tk.E, ipady=10, ipadx=10)

		# edit tab layout
		self.tabEdit.grid_columnconfigure(3, weight=1)
		self.editTabLabel.grid(column=0, row=0, columnspan=4, sticky=tk.W)
		self.currentTagsLabel.grid(column=0, row=1)
		self.currentTags.grid(column=1, row=1, sticky=tk.W)
		self.changeTagsLabel.grid(column=0, row=2)
		self.changeTags.grid(column=1, row=2, sticky=(tk.W))
		self.buttonAppendTags.grid(column=2, row=1, sticky=(tk.W), ipady=10, ipadx=10)
		self.buttonRemoveTags.grid(column=3, row=1, sticky=(tk.W), ipady=10, ipadx=10)
		self.buttonUpdateDBaseTags.grid(column=4, row=4, sticky=(tk.E), ipady=10, ipadx=10)

		# settings tab layout
		#self.settingsTabLabel.grid(column=0, row=0, columnspan=4, sticky=tk.W)
		#self.settingsAddDdsToPath.grid(column=0, row=1, columnspan=4, sticky=tk.W)
		#self.settingsAddUnderscore.grid(column=0, row=2, columnspan=4, sticky=tk.W)
		#self.setStringSize.grid(column=0, row=3, sticky=tk.W)
		#self.setStringSizeLabel.grid(column=1, row=3, sticky=tk.W)
		#self.setSequenceSize.grid(column=0, row=4, sticky=tk.W)
		#self.setSequenceSizeLabel.grid(column=1, row=4, sticky=tk.W)
		#self.settingsIdlVer4.grid(column=0, row=5, sticky=tk.W)
		#self.settingsIdlPreV4.grid(column=0, row=6, sticky=tk.W)

		# center frame widget: TreeView of data types
		self.typeTree = ttk.Treeview(self.typetree_frame, columns=('#1', '#2', '#3', '#4'))
		self.typeTree.heading('#0', text='Export')
		self.typeTree.heading('#1', text='TypeName')
		self.typeTree.heading('#2', text='TypePath')
		self.typeTree.heading('#3', text='Tags')
		self.typeTree.heading('#4', text='Members')
		self.typeTree.column('#0', width=7, anchor=tk.W)
		self.typeTree.column('#1', width=50, anchor=tk.W)
		self.typeTree.column('#2', width=50, anchor=tk.W)
		self.typeTree.column('#3', width=50, anchor=tk.W)
		self.typeTree.column('#4', width=50, anchor=tk.W)

		# test: try adding a color
		self.typeTree.tag_configure('oddrow', background='white')
		self.typeTree.tag_configure('evenrow', background='white')	# FIXME: lightblue, make this alternate correctly after column sort
		self.typeTree.tag_configure('errorrow', background='yellow')

		# add a scrollbar
		self.typetree_frame.grid_columnconfigure(0, weight=1)
		self.typetree_frame.grid_rowconfigure(1, weight=1)
		self.treeScroll = ttk.Scrollbar(self.typetree_frame, orient=tk.VERTICAL, command=self.typeTree.yview)
		self.typeTree.configure(yscroll=self.treeScroll.set)

		# bind to any clicks in TreeView
		self.typeTree.bind('<Button>', self.on_mouse_click)

		# layout of center frame:
		self.typeTree.grid(column=0, row=1, sticky=(tk.S, tk.W, tk.E, tk.N))
		self.treeScroll.grid(column=1, row=1, sticky=(tk.S, tk.N))

		# status frame: status messages
		self.statusText = tk.StringVar()		# text message in lower frame
		self.StatusA = ttk.Label(self.status_frame, textvariable=self.statusText, font=('Courier', '10', 'bold'))
		self.StatusA.grid(row=0, columnspan=2)
		self.statusText.set("Open a database file or scan your filesystem for data types")

		# preview frame: scrollable text window
		self.preview_frame.grid_columnconfigure(0, weight=1)
		self.preview_frame.grid_rowconfigure(0, weight=1)
		self.previewText = tk.Text(self.preview_frame, borderwidth=1, relief="sunken", wrap="none")
		self.pvTextVsb = tk.Scrollbar(self.preview_frame, orient="vertical", command=self.previewText.yview)
		self.pvTextHsb = tk.Scrollbar(self.preview_frame, orient="horizontal", command=self.previewText.xview)
		self.previewText.configure(yscrollcommand=self.pvTextVsb.set, xscrollcommand=self.pvTextHsb.set)
		self.previewText.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
		self.pvTextVsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
		self.pvTextHsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
		self.previewText.insert(tk.END, 'This is a type preview pane.\nSelected types will appear here.')

		# gripper for resizing the window
		self.grip = ttk.Sizegrip(self)
		self.grip.grid(row=4, column=1, sticky=tk.SE)

		# icon for window (Windows hosts only)
		if platform.system() == 'Windows':
			self.iconbitmap("images/RTI_Launcher_Dock-Icon.ico")

		# bind functions to events
		self.bind("<<OpenFileDialog>>", self.launchOpenFileDialog)
		self.bind("<<UnloadAllFromTree>>", self.unloadAllFromTree)
		self.bind("<<SelectPathDialog>>", self.launchSelectPathDialog)
		self.bind("<<SelectDBasePathDialog>>", self.launchSelectDBasePathDialog)
		self.bind("<<StartScan>>", self.launchScanOperation)
		self.bind("<<ExportTypeFile>>", self.exportDataTypeFile)
		self.bind("<<SelectExportPathDialog>>", self.launchSelectExportPathDialog)
		self.bind("<<TreeviewSelect>>", self.previewSelectedType)
		self.bind("<<AppendTagsToTypes>>", self.appendTagsToSelectedTypes)
		self.bind("<<RemoveTagsInTypes>>", self.removeTagsInSelectedTypes)
		self.bind("<<UpdateDatabaseWithTags>>", self.updateDatabaseTagsForSelectedTypes)
		self.bind("<<ComboboxSelected>>", self.comboboxExportTypeChanged)

		self.comboboxExportTypeChanged()	# force update to current selection.
		self.setExportFileNameInEntryBox()

		# finally, load the last-loaded database(s) (if allowed)
		if self.MyConfig.cfgVal['reloadLastDbOnStartup'] == True:
			if len(self.MyConfig.cfgVal['lastLoadedDbFiles']) > 0:
				dbFilenamesToRemoveFromSet = set()
				for dbToLoad in self.MyConfig.cfgVal['lastLoadedDbFiles']:
					try:
						self.databaseOpenAndLoadFile(dbToLoad)
					except:
						# error; add this filename to remove from the set
						print("not found: {}".format(dbToLoad))
						dbFilenamesToRemoveFromSet.add(dbToLoad)
				
				# clean the set if needed
				if len(dbFilenamesToRemoveFromSet) > 0:
					for removeMe in dbFilenamesToRemoveFromSet:
						self.MyConfig.cfgVal['lastLoadedDbFiles'].remove(removeMe)
					self.MyConfig.updateFile()

	# ------------------------------------------------------------------------------------
	# count the number of 'checked' boxes in current tree display
	def getCountOfCheckedTypes(self):
		checkedCount = 0
		self.treeTypes = self.typeTree.get_children()
		treeCount = len(self.treeTypes)
		for tt in self.treeTypes:
			if self.typeTree.item(tt)['image'][0] == 'checked':
				checkedCount += 1
		return checkedCount, treeCount

	# update the status pane with counts of types loaded, viewed, and selected
	def updateStatusPaneWithCounts(self):
		checkedCount, treeCount = self.getCountOfCheckedTypes()
		self.statusText.set("Displaying {} of {} Types, {} types selected".format(treeCount, len(self.typeTreeRef), checkedCount))

	# return a list of lists[ID,typeName,pathName,dbFileName] of the checked types
	def getListOfSelectedTypeIds(self):
		rtnList = []
		typesInView = self.typeTree.get_children()
		for tt in typesInView:
			if self.typeTree.item(tt)['image'][0] == 'checked':
				ttItem = []
				ttItem.append(tt)							# ID hash
				ttItem.append(self.typeTreeRef[tt][0])		# typeName
				ttItem.append(self.typeTreeRef[tt][1])		# typePath
				ttItem.append(self.dbFileNames[int(self.typeTreeRef[tt][5])])	# dbFileName
				rtnList.append(ttItem)
		return rtnList

	# use filters to copy from the typeTreeRef to the tree
	def updateTypeTreeWithFilters(self):
		# clear the existing tree
		self.typeTree.delete(*self.typeTree.get_children())

		# go through each item in typeTreeRef; see if it passes the filter spec
		evenRow = True
		for dtId in self.typeTreeRef:
			add_to_tree = True

			# filter by name
			if len(self.filterName) > 0:
				if self.typeTreeRef[dtId][0].find(self.filterName) == -1:
					add_to_tree = False

			# filter by path
			if len(self.filterPath) > 0:
				if self.typeTreeRef[dtId][1].find(self.filterPath) == -1:
					add_to_tree = False

			# filter by tag(s)
			if len(self.filterKeys) > 0:
				# filter: if multiple words, OR is implied unless '&' between groups
				filterANDgroups = self.filterKeys.split('&')
				for filterGroup in filterANDgroups:
					if add_to_tree == True:
						filterORterms = filterGroup.split()
						tag_filter_matched = False
						for filterTerm in filterORterms:
							if self.typeTreeRef[dtId][2].find(filterTerm) != -1:
								tag_filter_matched = True
						add_to_tree = tag_filter_matched

			if add_to_tree == True:
				if self.typeTreeRef[dtId][4] == 'UNDEF':
					self.typeTree.insert('', tk.END, dtId, values=self.typeTreeRef[dtId][:-1], image=self.box_unchecked, tags=('errorrow',))
				else:
					if self.typeTreeRef[dtId][-1] == 'checked':
						if evenRow == True:
							self.typeTree.insert('', tk.END, dtId, values=self.typeTreeRef[dtId][:-1], image=self.box_checked, tags=('evenrow',))
						else:
							self.typeTree.insert('', tk.END, dtId, values=self.typeTreeRef[dtId][:-1], image=self.box_checked, tags=('oddrow',))
					else:
						if evenRow == True:
							self.typeTree.insert('', tk.END, dtId, values=self.typeTreeRef[dtId][:-1], image=self.box_unchecked, tags=('evenrow',))
						else:
							self.typeTree.insert('', tk.END, dtId, values=self.typeTreeRef[dtId][:-1], image=self.box_unchecked, tags=('oddrow',))
					evenRow = not evenRow

	# open and load a named database file
	def databaseOpenAndLoadFile(self, databaseFileName):
		if len(databaseFileName) == 0:
			return
		self.dbFileName = databaseFileName
		self.dbFileNames.append(self.dbFileName)
		dbFileIndex = str(len(self.dbFileNames)-1)

		mydb = sql3db.SQL3Util(self.dbFileName)
		# get a dict of: idkey:[name, path, keys, countOfMembers]
		dbFileTypeTree = mydb.datatypes_reftree()

		# merge the new file content with the typeTreeRef
		for dtKey in dbFileTypeTree:
			# list order: 0:typeName, 1:typePath, 2:keywords, 3:memberCount, 4:memberErr
			# append: 5:dbFileIndex, 6:'unchecked'
			dbFileTypeTree[dtKey].append(dbFileIndex)			
			dbFileTypeTree[dtKey].append('unchecked')

			if dtKey in self.typeTreeRef:
				# this type already in refTree; merge the keywords
				fileTypeVal = dbFileTypeTree[dtKey]
				refTypeVal = self.typeTreeRef[dtKey]
				#old_tags = set(json.loads(refTypeVal[2]))
				#new_tags = set(json.loads(fileTypeVal[2]))
				old_tags = set(refTypeVal[2].split())
				new_tags = set(fileTypeVal[2].split())
				for tag in new_tags:
					old_tags.add(tag)
				refTypeVal[2] = ' '.join(list(old_tags))
				self.typeTreeRef[dtKey] = refTypeVal
			else:
				self.typeTreeRef[dtKey] = dbFileTypeTree[dtKey]

		# now update the displayed tree (using filters)
		self.updateTypeTreeWithFilters()
		self.updateStatusPaneWithCounts()
		# close the database
		mydb.database_close()
	
	# callback for IDL version to export
	def SettingsIdlVerCallback(self):
		print("YoYoYo")

	# dialog for selecting a database file to open
	def launchOpenFileDialog(self, *args):
		# open the selected db file, read into temporary list
		databaseFileName = fd.askopenfilename(title='Open database (.db) file', initialdir=self.MyConfig.cfgVal['dbLoadPath'], filetypes=(('sqlite database files', '*.db'), ('all files', '*.*')))
		self.databaseOpenAndLoadFile(databaseFileName)
		if self.MyConfig.cfgVal['reloadLastDbOnStartup'] == True:
			self.MyConfig.cfgVal['lastLoadedDbFiles'].append(databaseFileName)
		self.MyConfig.cfgVal['dbLoadPath'] = str(Path(databaseFileName).parent)
		self.MyConfig.updateFile()

	# unload all loaded databases from tree, and clear the last-loaded file list
	def unloadAllFromTree(self, *args):
		self.typeTreeRef.clear()
		self.typeTree.delete(*self.typeTree.get_children())
		self.MyConfig.cfgVal['lastLoadedDbFiles'].clear()
		self.MyConfig.updateFile()

	# dialog for choosing a scan path
	def launchSelectPathDialog(self, *args):
		self.scanFilePath = os.path.realpath(fd.askdirectory(title='select', initialdir=self.MyConfig.cfgVal['scanPath']))
		self.scanPathValue.set(self.scanFilePath)
		self.MyConfig.cfgVal['scanPath'] = self.scanFilePath
		self.MyConfig.updateFile()

	# dialog for choosing a database write path
	def launchSelectDBasePathDialog(self, *args):
		self.scanDBaseFilePath = os.path.realpath(fd.askdirectory(title='select', initialdir=self.MyConfig.cfgVal['scanDbStorePath']))
		self.scanDBasePathValue.set(self.scanDBaseFilePath)
		if not os.path.exists(self.scanDBaseFilePath):
			os.makedirs(self.scanDBaseFilePath)
		self.MyConfig.cfgVal['scanDbStorePath'] = self.scanDBaseFilePath
		self.MyConfig.updateFile()

	# Launch the scan operation
	def launchScanOperation(self, *args):
		if self.scanDBaseFileNameValue.get() == '':
			self.statusText.set('ERROR: must set name of the database file to write')
			return
		# FIXME: this needs to ensure the path and filename/ext format is correct.
		dbFilePathToWrite = os.path.realpath('{}/{}.db'.format(self.scanDBasePathValue.get(), self.scanDBaseFileNameValue.get()))
		rosparser.scan_paths_for_datatype_files([self.scanPathValue.get()], ['.msg', '.srv', '.action'], [self.scanTagsValue.get()], dbFilePathToWrite)

		# now load the database
		self.databaseOpenAndLoadFile(dbFilePathToWrite)

		# also add this database to the cfgVal list (for auto-loading next time)
		self.MyConfig.cfgVal['lastLoadedDbFiles'].append(dbFilePathToWrite)
		self.MyConfig.updateFile()


	# open database, get / return type list by ID
	def getTypesFromDatabase(self, typeKeyId, dbToOpen):
		# open the database
		mydb = sql3db.SQL3Util(dbToOpen)
		# get the type:
		foundRec = mydb.get_record_tree_by_typename_or_idkey('', '', typeKeyId)
		# close the database
		mydb.database_close()
		return foundRec

	# Export dataType/config file --------------------------------------------------------
	def exportDataTypeFile(self, *args):
		typesToExport = self.getListOfSelectedTypeIds()

		# test: merge all types into a single collection
		typeInfoToExport = []
		for typexp in typesToExport:
			fileNameCreated = ''
			typeRec = self.getTypesFromDatabase(typexp[0], typexp[3])
			# a list of lists is returned
			for typeItem in reversed(typeRec):
				# each list has a tuple at [0] and lists(with one tuple each) at [1:]
				# is this type already in the export array?
				itemIsNotInOutput = True
				for checkItem in typeInfoToExport:
					if checkItem[0][0] == typeItem[0][0]:
						itemIsNotInOutput = False
						break
				if itemIsNotInOutput:
					typeInfoToExport.append(typeItem)
		
		fileNameToCreate = os.path.abspath(self.exportPathValue.get() + '/' + self.exportFileNameValue.get())
		fileNameCreated = ''
		if self.cboxExportType.get() == self.exportArgLabels['idl']:
			fileNameCreated = idltypex.export_idl_type_file(typeInfoToExport, fileNameToCreate)
		elif self.cboxExportType.get() == self.exportArgLabels['idlcmake']:
			fileNameCreated = cxxcodex.export_idl_cxx11_app(typeInfoToExport, fileNameToCreate, typesToExport)
		elif self.cboxExportType.get() == self.exportArgLabels['xml']:
			fileNameCreated = xmltypex.export_xml_type_file(typeInfoToExport, fileNameToCreate)
		elif self.cboxExportType.get() == self.exportArgLabels['connector']:
			fileNameCreated = xmltypex.export_xml_connector_cfg_file(typeInfoToExport, fileNameToCreate, typesToExport)
		elif self.cboxExportType.get() == self.exportArgLabels['routsvc']:
			fileNameCreated = xmltypex.export_xml_routsvc_cfg_file(typeInfoToExport, fileNameToCreate, typesToExport)
		elif self.cboxExportType.get() == self.exportArgLabels['recsvc']:
			fileNameCreated = xmltypex.export_xml_recsvc_cfg_file(typeInfoToExport, fileNameToCreate, typesToExport)
		#elif self.cboxExportType.get() == self.exportArgLabels['persistsvc']:
		#	print('PERSISTSVC')
		#elif self.cboxExportType.get() == self.exportArgLabels['queuesvc']:
		#	print('QUEUESVC')
		#elif self.cboxExportType.get() == self.exportArgLabels['webintsvc']:
		#	fileNameCreated = xmltypex.export_xml_webintsvc_cfg_file(typeInfoToExport, self.exportFileNameValue.get(), typesToExport)
		#elif self.cboxExportType.get() == self.exportArgLabels['dbaseintsvc']:
		#	print('DBASEINTSVC')
		#elif self.cboxExportType.get() == self.exportArgLabels['prototyper']:
		#	fileNameCreated = xmltypex.export_xml_prototyper_cfg_file(typeInfoToExport, self.exportFileNameValue.get(), typesToExport)
		#elif self.cboxExportType.get() == self.exportArgLabels['xmlappcreate']:
		#	print('XML APP CREATION')

		# update status pane
		if len(fileNameCreated) > 0:
			self.statusText.set('Wrote to file: {}'.format(fileNameCreated))

	# Output file type combobox has been changed; update the export file name suffix
	def comboboxExportTypeChanged(self, *args):
		if self.cboxExportType.get() == self.exportArgLabels['idl']:
			self.exportFileNameSuffix = '_types.idl' 
		elif self.cboxExportType.get() == self.exportArgLabels['idlcmake']:
			self.exportFileNameSuffix = '_types.idl' 
		elif self.cboxExportType.get() == self.exportArgLabels['xml']:
			self.exportFileNameSuffix = '_types.xml' 
		elif self.cboxExportType.get() == self.exportArgLabels['connector']:
			self.exportFileNameSuffix = '_connector.xml' 
		elif self.cboxExportType.get() == self.exportArgLabels['routsvc']:
			self.exportFileNameSuffix = '_routsvc.xml' 
		elif self.cboxExportType.get() == self.exportArgLabels['recsvc']:
			self.exportFileNameSuffix = '_recsvc.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['persistsvc']:
		#	self.exportFileNameSuffix = '_persistsvc.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['queuesvc']:
		#	self.exportFileNameSuffix = '_queuesvc.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['webintsvc']:
		#	self.exportFileNameSuffix = '_webintsvc.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['dbaseintsvc']:
		#	self.exportFileNameSuffix = '_dbaseintsvc.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['prototyper']:
		#	self.exportFileNameSuffix = '_prototyper.xml' 
		#elif self.cboxExportType.get() == self.exportArgLabels['xmlappcreate']:
		#	self.exportFileNameSuffix = '_xmlapp.xml'
		else:
			self.exportFileNameSuffix = '_unknown.txt'

		# call a function to update the filename here
		self.setExportFileNameInEntryBox()

		# now update the preview
		self.previewSelectedType()

	# update the export filename in the GUI 'Entry' box
	# The format is to be: SelectedTypeName_countOfSelectedTypes_4CharHashOfTypeIds_NameSuffix.ext
	# Note this is just an autogen name suggestion; user can edit this directly in Entry box.
	def setExportFileNameInEntryBox(self, *args):
		# get selected types
		typeList = self.getListOfSelectedTypeIds()
		# count of types selected
		checkedCount = len(typeList)
		if checkedCount > 1:
			typeCountStr = '_{}'.format(checkedCount)
		else:
			typeCountStr = ''

		if checkedCount > 0:
			# hash of the typeIds of selected types
			listOfTypeIds = []
			for typeItem in typeList:
				listOfTypeIds.append(typeItem[0])
			groupTypeId = '_{}'.format(hashutil.hex_from_hash_base64(hashutil.hash_list_of_strings(listOfTypeIds))[0:3])
		else:
			groupTypeId = ''
		expFileName = '{}{}{}{}'.format(self.exportFileNameBase, typeCountStr, groupTypeId, self.exportFileNameSuffix)
		self.exportFileNameValue.set(expFileName)

	# handle search entries
	def searchNameCallback(self, qfield, queryVar):
		if qfield == 'name':
			self.filterName = queryVar.get()
		elif qfield == 'path':
			self.filterPath = queryVar.get()
		elif qfield == 'keys':
			self.filterKeys = queryVar.get()
		# now update the tree and status area
		self.updateTypeTreeWithFilters()
		self.updateStatusPaneWithCounts()
		self.editTabTagSetUpdate()

	# dialog for choosing an export destination path
	def launchSelectExportPathDialog(self, *args):
		self.exportFilePath = os.path.realpath(fd.askdirectory(title='select', initialdir=self.MyConfig.cfgVal['exportPath']))
		self.exportPathValue.set(self.exportFilePath)
		if not os.path.exists(self.exportFilePath):
			os.makedirs(self.exportFilePath)
		self.MyConfig.cfgVal['exportPath'] = self.exportFilePath
		self.MyConfig.updateFile()


	# handler for mouse clicks in TreeView
	def on_mouse_click(self, event):
		treeRegion = self.typeTree.identify('region', event.x, event.y)
		if treeRegion == "heading":
			colNum = int(self.typeTree.identify_column(event.x).replace('#', '')) - 1
			if colNum >= 0:
				tmpSort = [(self.typeTree.set(k, colNum), k) for k in self.typeTree.get_children('')]
				tmpSort.sort(reverse=self.typeTreeSortReverse)
				self.typeTreeSortReverse = not self.typeTreeSortReverse
				# rearrange in sorted order
				for idx, (val, k) in enumerate(tmpSort):
					self.typeTree.move(k, '', idx)
			else:
				# toggle all displayed: all-checked / all-unchecked
				self.checkedState = not self.checkedState
				treeAll = self.typeTree.get_children()
				for tRow in treeAll:
					if self.checkedState:
						self.typeTreeRef[tRow][-1] = 'unchecked'
						self.typeTree.item(tRow, values=self.typeTreeRef[tRow][:-1], image=self.box_unchecked)
						self.exportFileNameBase = self.exportFileNameDefault
					else:
						self.typeTreeRef[tRow][-1] = 'checked'
						self.typeTree.item(tRow, values=self.typeTreeRef[tRow][:-1], image=self.box_checked)
						self.exportFileNameBase = self.typeTreeRef[tRow][0]

				# update the export filename
				self.setExportFileNameInEntryBox()

		elif treeRegion == 'tree':
			# a row's select/deselect column was clicked
			rowId = self.typeTree.identify_row(event.y)
			if self.typeTree.item(rowId)['image'][0] == 'checked':
				self.typeTreeRef[rowId][-1] = 'unchecked'
				self.typeTree.item(rowId, values=self.typeTreeRef[rowId][:-1], image=self.box_unchecked)
				# if this selection brings the total selected to 0, revert exportFileNameBase to default
				checkedCount, toss = self.getCountOfCheckedTypes()
				if checkedCount == 0:
					self.exportFileNameBase = self.exportFileNameDefault

			elif self.typeTree.item(rowId)['image'][0] == 'unchecked':
				self.typeTreeRef[rowId][-1] = 'checked'
				self.typeTree.item(rowId, values=self.typeTreeRef[rowId][:-1], image=self.box_checked)
				# if this selection brings the total selected to 1, update the exportFileNameBase
				checkedCount, toss = self.getCountOfCheckedTypes()
				if checkedCount == 1:
					self.exportFileNameBase = self.typeTreeRef[rowId][0]

				# update the export filename
				self.setExportFileNameInEntryBox()

		#elif treeRegion == 'cell':		# no longer used.

		# update the count in the status pane
		self.updateStatusPaneWithCounts()
		self.editTabTagSetUpdate()

	# preview the selected type in the preview pane
	def previewSelectedType(self, *args):
		typeKeyId = self.typeTree.focus()
		if len(typeKeyId) > 0:
			dbToOpen = self.dbFileNames[int(self.typeTreeRef[typeKeyId][5])]
			foundRec = self.getTypesFromDatabase(typeKeyId, dbToOpen)

			if self.cboxExportType.get() == self.exportArgLabels['idl']	or self.cboxExportType.get() == self.exportArgLabels['idlcmake']:
				typeText = idltypex.type_to_string_list(foundRec)
			else:
				typeText = xmltypex.type_to_string_list(foundRec)
			self.previewText.delete('0.0', tk.END)
			self.previewText.insert(tk.END, '\n'.join(typeText))

	# build a set of TAGS from current display tree, update edit tab
	def editTabTagSetUpdate(self):
		tagSet = set()
		treeAll = self.typeTree.get_children()
		for tRow in treeAll:
			if self.typeTree.item(tRow)['image'][0] == 'checked':
				itemTagList = self.typeTreeRef[tRow][2].split()
				for itemTag in itemTagList:
					tagSet.add(itemTag)
		tagSetString = ' '.join(list(tagSet))
		self.currentTagsVar.set("{}".format(tagSetString))

	# update the selected types with new TAGS
	def appendTagsToSelectedTypes(self, *args):
		tagSet = set()
		newTagList = self.changeTags.get().split()
		treeAll = self.typeTree.get_children()
		for tRow in treeAll:
			if self.typeTree.item(tRow)['image'][0] == 'checked':
				itemTagList = self.typeTreeRef[tRow][2].split()
				for itemTag in itemTagList:
					tagSet.add(itemTag)
				for newTag in newTagList:
					tagSet.add(newTag)
				newTagString = ' '.join(list(tagSet))
				self.typeTreeRef[tRow][2] = newTagString
				itemRowNum = self.typeTree.index(tRow)
				self.typeTree.delete(tRow)
				self.typeTree.insert('', itemRowNum, tRow, values=self.typeTreeRef[tRow][:-1], image=self.box_checked)


	# remove TAGS from the selected types
	def removeTagsInSelectedTypes(self, *args):
		tagSet = set()
		newTagList = self.changeTags.get().split()
		treeAll = self.typeTree.get_children()
		for tRow in treeAll:
			if self.typeTree.item(tRow)['image'][0] == 'checked':
				itemTagList = self.typeTreeRef[tRow][2].split()
				# get existing set of tags
				for itemTag in itemTagList:
					tagSet.add(itemTag)
				# remove new tags
				for newTag in newTagList:
					tagSet.discard(newTag)
				newTagString = ' '.join(list(tagSet))
				self.typeTreeRef[tRow][2] = newTagString
				itemRowNum = self.typeTree.index(tRow)
				self.typeTree.delete(tRow)
				self.typeTree.insert('', itemRowNum, tRow, values=self.typeTreeRef[tRow][:-1], image=self.box_checked)

	# update the database with the tags for the selected types
	def updateDatabaseTagsForSelectedTypes(self, *args):
		# this creates a dict of: { dbFileNames { idKey:'json-stringlist-of-tags',,, },, }
		updateItems = {}
		treeAll = self.typeTree.get_children()
		for tRow in treeAll:
			if self.typeTree.item(tRow)['image'][0] == 'checked':
				thisTypesDBFile = self.dbFileNames[int(self.typeTreeRef[tRow][5])]
				if thisTypesDBFile not in updateItems:
					updateItems[thisTypesDBFile] = {}
				updateItems[thisTypesDBFile][tRow] = json.dumps(self.typeTreeRef[tRow][2].split())

		# now update the database(s)
		for itemDbFileName in updateItems:
			itemDb = sql3db.SQL3Util(itemDbFileName)
			for itemRowId in updateItems[itemDbFileName]:
				itemDb.update_tags(itemRowId, updateItems[itemDbFileName][itemRowId])
			itemDb.database_commit()
			itemDb.database_close()

# --------------------------------------------------
if __name__ == "__main__":
	app = TypeRepoUI()
	app.mainloop()


