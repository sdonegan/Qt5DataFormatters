# Qt5DataFormatters

Qt5DataFormatters contains a set of [lldb data formatters](http://lldb.llvm.org/varformats.html) (specifically synthetic children and summary providers) for various Qt5 data structures, implemented using lldb's Python API. The following Qt5 objects have been implemented:

+ QVector (synthetic children + summary)
+ QList (synthetic children + summary)
+ QMap (synthetic children + summary)
+ QString (summary)

To enable these data formatters when using lldb, simply enter the following into your .lldbinit file:

    command script import /path/to/Qt5DataFormatters.py

## License ##
Qt5DataFormatters is open-source and available under a BSD license. See LICENSE.txt file that comes with the project for more information.