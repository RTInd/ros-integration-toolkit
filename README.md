# ros-integration-toolkit
Tool to improve ROS 2 systems by creating interoperable Connext enhancements.

This toolkit is a GUI application with facilities to:  
1. Scan a chosen file system path for data type definition files (presently ROS type (.msg, .srv, .action))
2. Normalize the file contents and store the data types and members in a database (SQLite3)
3. Search and select data types from the database
4. Export source, build, and configuration files for RTI Connext applications and ecosystem components.

This toolkit requires a standard install of python3, which includes `sqldb` and `tkinter` support.
No other add-on packages are required.   A starter database is included (in `dbfiles/ros2h.db`) which
was scanned from an unmodified ROS 2 'Humble Hawksbill' source installation.

## Launching the Toolkit
Launch from a command line using python 3, as in:

    python3 scan_ui.py

A GUI application will be displayed.  The right side of the application is a type preview pane, and the left
side is a tabbed interface for Scanning, Querying, and Editing the data type info, as well as a list view of
the currently-loaded data types from the database file(s).   Click on the list column headers to sort.

## Menus and Tabs

**File Menu** has options to unload the currently-loaded databases, and to load additional databases into the
GUI viewer.  Note that multiple databases can be loaded.

**Scan for Types Tab**  
Use this tab to scan your local file system for ROS data type definition files (currently supporting files 
ending in `.msg`, `.srv`, or `.action`).

 - **Scan Path..** sets the directory location to begin the scan; all files and folders in this path are scanned recursively.
 - **Tags:** adds a text 'tag' entry to the scanned data types.  Tags are used to help speed searches in large data sets.
 - **File Types**: presently supporting ROS data type files only.  More file types are in development.
 - **Output Path** selects where to write the resulting database file.
 - **.db File Name** the name assigned to the resulting database file.
 - **Start Scan** launches the scan of the filesystem per the above settings.

**Query & Export Tab**  
Use this tab to filter the displayed list of types, and to select export options and locations.  
Filters are case-sensitive.  
Export File Name is automatically generated when selecting data types, but can be entered directly by the user.  
Export options include:
 - **IDL Types File**: Exports the selected types as IDL (Interface Description Language), can be used with RTIDDSGen to generate typesupport code in a variety of programming languages.
 - **XML Types File**: Exports the selected types as XML, can be used with RTI Admin Console and other RTI ecosystem components.
 - **Routing Service Config File**: Creates a configuration XML file for RTI Routing Service, using the selected types, in a generic 2-way topic bridge, ready to be customized by the user to set the appropriate topic direction and domains.
 - **Recording Service Config File**: Creates a configuration XML file for RTI Recording Service for the selected topics.
 - **Connector Python Application**: Creates a configuration XML and Python source file, ready-to-run with RTI Connector to publish the selected data types, and ready for user customization such as adding subscribers or setting / getting the topic data values.
 - **Connext Pro C++11 Application**: Creates a ready-to-build C++11 Connext application for the selected types.

 Note that in most of the above cases, some editing by the user is required to fit their specific application.
 The intent is to get the user onto a buildable/running system using their selected data types as quickly as 
 possible -- typically in a few minutes.


**Edit Tab**  
Use this tab to add/remove tags from the selected data types, and write them back to their respective database files.
This can be helpful to accelerate searching for specific data types in large type databases.


## Questions / Comments
Please visit the RTI Community pages for ROS at: https://community.rti.com/ros for more information or to post a question or comment.  
RTI customers can also open a tech support incident or contact their local RTI representatives.  
