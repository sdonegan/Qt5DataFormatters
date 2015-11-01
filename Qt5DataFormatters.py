"""
Copyright (c) 2015 Sean Donegan

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
*other materials provided with the distribution.

The name of Sean Donegan may not be used to endorse or promote products derived
from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


import lldb


class QVectorSyntheticProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.start = None
        self.data_type = None
        self.data_size = None

    def num_children(self):
        num_children = self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('size').GetValueAsUnsigned(0)
        return num_children

    def num_children_impl(self):
        return self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('size').GetValueAsUnsigned(0)

    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index):
        if index < 0:
            return None
        if index >= self.num_children():
            return None
        try:
            offset = (index * self.data_size) + self.valobj.GetChildMemberWithName('d').GetChildMemberWithName(
                'offset').GetValueAsUnsigned(0)
            return self.start.CreateChildAtOffset('[' + str(index) + ']', offset, self.data_type)
        except:
            return None

    def extract_type(self):
        list_type = self.valobj.GetType().GetUnqualifiedType()
        if list_type.IsReferenceType():
            list_type = list_type.GetDereferencedType()
        if list_type.GetNumberOfTemplateArguments() > 0:
            data_type = list_type.GetTemplateArgumentType(0)
        else:
            data_type = None
        return data_type

    def update(self):
        try:
            self.start = self.valobj.GetChildMemberWithName('d')
            self.data_type = self.extract_type()
            self.data_size = self.data_type.GetByteSize()
        except:
            pass

    def has_children(self):
        return True


class QListSyntheticProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.dptr = None
        self.start = None
        self.array_type = None
        self.data_type = None
        self.data_size = None

    def num_children(self):
        end = self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('end').GetValueAsUnsigned(0)
        begin = self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('begin').GetValueAsUnsigned(0)
        num_children = end - begin
        return num_children

    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index):
        if index < 0:
            return None
        if index >= self.num_children():
            return None
        try:
            child_data = self.start.GetPointeeData(index)
            val = self.start.CreateValueFromData('temp', child_data, self.array_type)
            child_at_zero = val.GetChildAtIndex(0)
            child_val = None
            if self.data_size > 8:
                child_val = child_at_zero.CreateChildAtOffset('[' + str(index) + ']', 0, self.data_type)
            else:
                child_val = child_at_zero.Cast(self.data_type)
            return child_val
        except:
            return None

    def extract_type(self):
        list_type = self.valobj.GetType().GetUnqualifiedType()
        if list_type.IsReferenceType():
            list_type = list_type.GetDereferencedType()
        if list_type.GetNumberOfTemplateArguments() > 0:
            data_type = list_type.GetTemplateArgumentType(0)
        else:
            data_type = None
        return data_type

    def update(self):
        try:
            self.dptr = self.valobj.GetChildMemberWithName('d')
            self.start = self.dptr.GetChildMemberWithName('array')
            self.array_type = self.start.GetType()
            self.data_type = self.extract_type()
            self.data_size = self.data_type.GetByteSize()
        except:
            pass

    def has_children(self):
        return True


class QMapSyntheticProvider:
    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.garbage = False
        self.root_node = None
        self.header = None
        self.data_type = None

    def num_children(self):
        return self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('size').GetValueAsUnsigned(0)

    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index):
        if index < 0:
            return None
        if index >= self.num_children():
            return None
        if self.garbage:
            return None
        try:
            offset = index
            current = self.header
            while offset > 0:
                current = self.increment_node(current)
                offset -= 1
            child_data = current.Dereference().Cast(self.data_type).GetData()
            return current.CreateValueFromData('[' + str(index) + ']', child_data, self.data_type)
        except:
            return None

    def extract_type(self):
        map_type = self.valobj.GetType().GetUnqualifiedType()
        target = self.valobj.GetTarget()
        if map_type.IsReferenceType():
            map_type = map_type.GetDereferencedType()
        if map_type.GetNumberOfTemplateArguments() > 0:
            first_type = map_type.GetTemplateArgumentType(0)
            second_type = map_type.GetTemplateArgumentType(1)
            close_bracket = '>'
            if second_type.GetNumberOfTemplateArguments() > 0:
                close_bracket = ' >'
            data_type = target.FindFirstType(
                'QMapNode<' + first_type.GetName() + ', ' + second_type.GetName() + close_bracket)
        else:
            data_type = None
        return data_type

    def node_ptr_value(self, node):
        return node.GetValueAsUnsigned(0)

    def right(self, node):
        return node.GetChildMemberWithName('right')

    def left(self, node):
        return node.GetChildMemberWithName('left')

    def parent(self, node):
        parent = node.GetChildMemberWithName('p')
        parent_val = parent.GetValueAsUnsigned(0)
        parent_mask = parent_val & ~3
        parent_data = lldb.SBData.CreateDataFromInt(parent_mask)
        return node.CreateValueFromData('parent', parent_data, node.GetType())

    def increment_node(self, node):
        max_steps = self.num_children()
        if self.node_ptr_value(self.right(node)) != 0:
            x = self.right(node)
            max_steps -= 1
            while self.node_ptr_value(self.left(x)) != 0:
                x = self.left(x)
                max_steps -= 1
                if max_steps <= 0:
                    self.garbage = True
                    return None
            return x
        else:
            x = node
            y = self.parent(x)
            max_steps -= 1
            while self.node_ptr_value(x) == self.node_ptr_value(self.right(y)):
                x = y
                y = self.parent(y)
                max_steps -= 1
                if max_steps <= 0:
                    self.garbage = True
                    return None
            if self.node_ptr_value(self.right(x)) != self.node_ptr_value(y):
                x = y
            return x

    def update(self):
        try:
            self.garbage = False
            self.root_node = self.valobj.GetChildMemberWithName('d').GetChildMemberWithName(
                'header').GetChildMemberWithName('left')
            self.header = self.valobj.GetChildMemberWithName('d').GetChildMemberWithName('mostLeftNode')
            self.data_type = self.extract_type()
        except:
            pass

    def has_children(self):
        return True


def qvector_summary_provider(valobj, dict):
    return 'size=' + str(valobj.GetNumChildren())


def qlist_summary_provider(valobj, dict):
    return 'size=' + str(valobj.GetNumChildren())


def qmap_summary_provider(valobj, dict):
    return 'size=' + str(valobj.GetNumChildren())


def make_string_from_pointer_with_offset(valobj, offset, length):
    strval = '"'
    try:
        data_array = valobj.GetPointeeData(0, length).uint16
        for X in range(offset, length):
            v = data_array[X]
            if v == 0:
                break
            strval += unichr(v)
    except:
        pass
    strval += '"'
    return strval.encode('utf-8')


def get_max_size(value):
    _max_size_ = None
    try:
        debugger = value.GetTarget().GetDebugger()
        _max_size_ = int(lldb.SBDebugger.GetInternalVariableValue('target.max-string-summary-length',
                                                                  debugger.GetInstanceName()).GetStringAtIndex(0))
    except:
        _max_size_ = 512
    return _max_size_


def qstring_summary_provider(value, dict):
    try:
        d = value.GetChildMemberWithName('d')
        offset = d.GetChildMemberWithName('offset').GetValueAsUnsigned() / 2
        size = get_max_size(value)
        return make_string_from_pointer_with_offset(d, offset, size)
    except:
        print '?????????????????????????'
        return value


def __lldb_init_module(debugger, dict):
    debugger.HandleCommand('type summary add -F Qt5DataFormatters.qstring_summary_provider "QString"')
    debugger.HandleCommand('type synthetic add -l Qt5DataFormatters.QVectorSyntheticProvider -x "^QVector<.+>$"')
    debugger.HandleCommand('type summary add -F Qt5DataFormatters.qvector_summary_provider -e -x "^QVector<.+>$"')
    debugger.HandleCommand('type synthetic add -l Qt5DataFormatters.QListSyntheticProvider -x "^QList<.+>$"')
    debugger.HandleCommand('type summary add -F Qt5DataFormatters.qlist_summary_provider -e -x "^QList<.+>$"')
    debugger.HandleCommand('type synthetic add -l Qt5DataFormatters.QMapSyntheticProvider -x "^QMap<.+, .+>$"')
    debugger.HandleCommand('type summary add -F Qt5DataFormatters.qmap_summary_provider -e -x "^QMap<.+, .+>$"')
