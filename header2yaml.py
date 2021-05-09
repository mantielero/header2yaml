from tree_sitter import Language, Parser
from pprint import pprint
import textwrap, re
from yaml import load, dump

#C_LANGUAGE = Language('build/my-languages.so', 'c')
CPP_LANGUAGE = Language('treesitter/my-languages.so', 'cpp')

NIM_KEYWORDS = ["addr", "and", "as", "asm", "bind", "block", "break",
                "case", "cast", "concept", "const", "continue", "converter",
                "defer", "discard", "distinct", "div", "do", "elif", "else",
                "end", "enum", "except", "export", "finally", "for", "from",
                "func", "if", "import", "in", "include", "interface", "is",
                "isnot", "iterator", "let", "macro", "method", "mixin", "mod",
                "nil", "not", "notin", "object", "of", "or", "out", "proc", "ptr",
                "raise", "ref", "return", "shl", "shr", "static", "template",
                "try", "tuple", "type", "using", "var", "when", "while", "xor",
                "yield"]

types = {
    "void *": "pointer",
    "long": "clong",
    "unsigned long": "culong",
    "short": "cshort",
    "int": "cint",
    "size_t": "csize_t",
    "long long": "clonglong",
    "long double": "clongdouble",
    "float": "cfloat",
    "double": "cdouble",
    "char *": "cstring",
    "char": "cchar",
    "signed char": "cschar",
    "unsigned char": "cuchar",
    "unsigned short": "cushort",
    "unsigned int": "cuint",
    "unsigned long long": "culonglong",
    "char**": "cstringArray",
    "uint8_t": "uint8_t",
    "uint16_t": "uint16_t",
    "bool" : "bool"
}

def get_children(level,node):
    yield  level, node
    k = node.child_count 
    for n in node.children:
        yield from get_children(level+1, n)

def walker(cursor):
    """Recursively follows all nodes in the structure"""
    depth = 0
    _lista = []
    for n, node in get_children(depth, cursor.node):
        _lista.append((n, node))
    return _lista
    
def read(data, node):
    return data[node.start_byte:node.end_byte].decode("utf-8").strip()

def cleanInclude(name):
    if name[0] in ['"','<'] and name[-1] in ['"','>']:
        name = name[1:-1]
    if name[-2:].lower() == ".h":
        name = name[0:-2]
    if name[-4:].lower() == ".hxx":
        name = name[0:-4]
    return name

def get_includes(parsed, data):
    includes = []
    for level, node in parsed:
        if node.type == "preproc_include":
            for i in node.children:
                if i.type in ["system_lib_string", "string_literal"]:
                    includes.append(read(data,i))
    return includes


def genComment(data, node):
    
    _tmp = read(data,node)
    #print(_tmp)
    if _tmp[0:2] == "/*":
        _tmp = _tmp[2:]
    if _tmp[-2:] == "*/":
        _tmp = _tmp[0:-2]
    if _tmp[0:2] == "//":
        _tmp = _tmp[2:]
    _tmp = _tmp.replace("\t", " ")
    if len(_tmp) > 0:
        if _tmp[-1] == ":":
            _tmp = "'" + _tmp + "'"
    return _tmp

directives        = [ "#ifndef", "#ifdef", 
                      "#if", "#else", "#elif", "#endif", 
                      "#define", "#include"]
logical_operators = ["||", "&&", "!"]
symbols           = ["[", "]", "{", "}", "=", "...", "*"]

reinit = ["preproc_def", "preproc_include", "preproc_call", "declaration",
          "preproc_if", "preproc_elif", "preproc_else", "preproc_function_def",
          "preproc_ifdef", "comment"]

excluded = ['', 'ERROR', "translation_unit", "#ifndef", "#ifdef", "preproc_call",
            "preproc_if", "preproc_elif", "preproc_else", "preproc_include", 
            "preproc_def", "preproc_ifdef"
]

def getChidrenTypes(node):
    l = []
    for n in node.children:
        l.append(n.type)    
    return l

def getAllTypesUnder(parsed, i):
    if i == 0:
        return []
    level,node = parsed[i]
    lst = []
    while True:
        i += 1
        l,n = parsed[i]
        if l <= level:
            break
        else:
            lst.append(n.type)
    #print(lst)
    return lst
#def checkNextType(node,i)
#def condition(node):

def isCallExpression(parsed, i):
    line = parsed[i][1].start_point[0]
    try:
        if parsed[i+1][1].type in ["labeled_statement", "statement_identifier", "ERROR"]:
            return False

        if not parsed[i][1].type in ["type_identifier", "primitive_type", "sized_type_specifier"]:
            return False
        #j = i
        while True:
            if parsed[i][1].type in ["identifier", "call_expression"]:
                return True
            if parsed[i][1].start_point[0] > line:
                break
            i += 1           
        return False
    except:
        return False

def gotoNext(typ, parsed, i):
    while True:
        i += 1
        try:
            if parsed[i][1].type in ["parameter_list", "parenthesized_expression", "cast_expression", "argument_list"]:
                break
        except:
            break
    return i


def addFunction(data, indent, currentClass, generalQualifier):
    tmp = ""
    _indent = indent.get()   
    tmp += f"{_indent}- function:\n"
    _indent = indent.inc()  
    tmp += f'{_indent}idx: {data["idx"]}\n'

    if len(data["qualifiers"]) > 0:
        tmp += f"{_indent}funcQualifier:\n"
        _indent = indent.inc()   
        for q in data["qualifiers"]:
            tmp += f"{_indent}- {q}\n"
        _indent = indent.dec() 

    if data["return"] != None:
        tmp += f'{_indent}return: {data["return"]}\n'
    if len(data["returnQualifiers"]) > 0:
        tmp += f"{_indent}returnQualifiers:\n" 
        _indent = indent.inc()   
        for q in data["returnQualifiers"]:
            tmp += f"{_indent}- {q}\n" 
        _indent = indent.dec()  
    tmp += f'{_indent}id: {data["id"]}\n'

    if len(currentClass) > 0:
        tmp += f'{_indent}class:\n'
        _indent = indent.inc()
        for c in currentClass:
            tmp += f'{_indent}- {c}\n'
        _indent = indent.dec()

    if len(generalQualifier) > 0:
        tmp += f'{_indent}qualifiers:\n'
        _indent = indent.inc()
        for q in generalQualifier:
            tmp += f'{_indent}- {q}\n'
        _indent = indent.dec()

    if len(data["params"]) > 0:
        tmp += f"{_indent}params:\n"
        _indent = indent.inc()           
        for p in data["params"]:
            tmp += f'{_indent}- {p["id"]}:\n'
            tmp += f'{_indent}  type: {p["type"]}\n'
            tmp += f'{_indent}  isPrimitive: {p["isPrimitive"]}\n'
            if p["default"] != None:
                tmp += f'{_indent}  default: {p["default"]}\n'

            if len(p["qualifier"]) > 0:
                tmp += f"{_indent}  qualifier:\n"                        
                for q in p["qualifier"]:
                    tmp += f"{_indent}  - {q}\n" 
        _indent = indent.dec() 

    _indent = indent.dec()   
    if data["funcDecl"] != None:

        if "\n" in data["funcDecl"]:
            tmp += f"{_indent}funcDecl: >\n" 
            tmp += textwrap.indent(txt, spaces * indent.LEVEL + "  ")
            tmp += '\n'                        
        else:
            tmp += f'{_indent}funcDecl: "{_funcDecl}"\n'
    #
    return tmp

def getParams(data, parsed, i):
    _params = []
    paramLevel = parsed[i][0]
    _type = None
    _id   = None
    while True:
        if not parsed[i+1][0] > paramLevel:
            break
        i += 1
        level, node = parsed[i]                    
        paramType = node.type
        if paramLevel + 1 == level and paramType == ")":
            break


        if paramType in ["parameter_declaration","optional_parameter_declaration"]:
            lvl = level

            _type      = None
            _id        = None
            _default   = None
            _qualifier = []
            _isPrimitive = "false"
            _flagOptional = False

            # Read all params
            while True:
                i += 1
                level, node = parsed[i]

                if node.type in ["primitive_type", "type_identifier", "sized_type_specifier"] and _type == None:
                    _type = read(data, node)
                    if node.type == "primitive_type":
                        _isPrimitive = "true"
                elif node.type == "const":
                    _qualifier.append("const")
                elif set(node.type)  == set(["*"]) or set(node.type) == set(["&"]):
                    _qualifier.append(node.type)
                elif node.type == "compound_statement":
                    _qualifier.append(read(data,node))   # {}
                elif node.type == "identifier":
                    _id = read(data, node)

                elif node.type == "=":
                    _flagOptional = True
                
                elif _flagOptional:
                    if node.type == "string_literal":
                        _default = read(data, node)
                    elif node.type == "number_literal":
                        _default = read(data, node)                                    
                    else:
                        print("TODO: to review this case: optional_parameter_declaration. Line: ", parsed[i][1].start_point[0])

                if _id == None:
                    _id = '-nil-'

                if node.type in [",", ")"]:
                    _params.append({ "id": _id, 
                                     "type":_type,
                                     "default": _default,
                                     "qualifier": [],
                                     "isPrimitive": _isPrimitive
                                    })
                    _type      = None
                    _id        = None
                    _default   = None
                    _qualifier = []
                    _isPrimitive = "false"
                    _flagOptional = False
                    if node.type == ")":
                        break
    return _params, i

def isFunction(data, parsed, i):
    line = parsed[i][1].start_point[0]    
    typ = parsed[i][1].type
    #if line > 294:
        #print("isFunction>>>", line, typ)
    if typ in ["function_declarator", "function_definition"]:
        #print("True1")
        return True
    elif typ == "declaration":
        #print("True2")        
        for k in ["cast_expression"]:
            if  k in getAllTypesUnder(parsed, i+1):             
                return True
    elif typ == "field_declaration":
        #print("True3")        
        for k in ["parameter_list"]:
            if  k in getAllTypesUnder(parsed, i+1):
                
                return True
    elif isCallExpression(parsed, i):
        #print("True4")         
        for k in ["type_identifier", "primitive_type", "sized_type_specifier"]:
            if k == parsed[i][1].type:
               
                return True
        #return True
    #print("5")
    #if line > 294:
    #    print("###", line, typ)
    return False


def getFunction(data, parsed, i, idx, isFriend ):

    level, node = parsed[i]
    line = node.start_point[0]

    checkFuncDecl = False
    if "compound_statement" in getAllTypesUnder(parsed, i):
        checkFuncDecl = True

    # Check if the function defines an operator
    k = re.compile("operator[ ]*([\*\=\+\-\,\<\>\|\&\/\%\^\!\~\(\)\[\]]{1,3})[ ]*")
    _tmp = read(data,node)
    _operator = None
    if "operator " in _tmp:
        _res = k.findall(_tmp)
        if len(_res) == 1:
            _operator = "`" + _res[0] + "`"

    _data = {"idx" : idx,
             "id": None,
             "qualifiers": [],
             "return": None,
             "returnQualifiers": [],
             "params" : [],
             "funcDecl": None
             }

    # isExplicit
    functionQualifiers = []
    if "explicit_function_specifier" in getChidrenTypes(node):
        _data["qualifiers"].append("explicit")
        i += 1
        _, n = parsed[i]
        assert n.type == "explicit_function_specifier"
        i += 1
        _, n = parsed[i]  
        assert n.type == "explicit"              

    if isFriend:
        functionQualifiers.append("friend")
        isFriend = False

    # Return value or function definition
    _return = None
    while not node.type in ["function_declarator", "field_identifier", "cast_expression", "expression_statement"]:
        if node.type in ["type_identifier", "sized_type_specifier", "primitive_type"] and _return == None:
            _data["return"] = read(data, node)
        elif set(node.type) == set(["&"]):
            _data["returnQualifiers"].append(node.type)
        i += 1
        level, node = parsed[i]            
        if node.start_point[0] > line:
            break

    # Get function name
    if node.type in ["function_declarator", "field_identifier", "cast_expression"]: 
        # Get the function name
        while True:
            i += 1
            level, node = parsed[i]
            #print("->", i, parsed[i][1].start_point[0])
            if node.type in ["identifier", "field_identifier", "destructor_name", "expression_statement"] and _data["id"] == None:
                _data["id"] = read(data, node)
                if _data["id"] == "operator":
                    i += 1
                    level, node = parsed[i]
                    _data["id"] = "`" + _operator + "`"
                break
            elif node.type == "inline":
                data["qualifiers"].append("inline")  
            elif node.type == "const":
                data["qualifiers"].append("const")                                      
            elif node.type in ["function_definition", "compound_statement", 
                                "(",")", "{", "}"]:
                pass
            elif node.type in ["parameter_list", "parenthesized_expression", "cast_expression", "argument_list"]:
                break

        # Go to the start of the parameters declaration
        while not parsed[i][1].type in ["parameter_list", "parenthesized_expression", "cast_expression", "argument_list"]:
            i += 1                   

        # Read the params
        #i = gotoNext("parameter_list", parsed, i)
        _params, i = getParams(data, parsed, i)
        _data["params"] = _params

        #compound_statement
        if checkFuncDecl:
            while True:
                i += 1
                level, node = parsed[i]
                if node.type in ["compound_statement", "compound_literal_expression"]:
                    _data["funcDecl"] = read(data, node)
                    #_lvl = level
                    break
            #while parsed[i][0] > _lvl:
            #    i += 1

    return _data


class Indenter:
    def __init__(self):
        self.spaces = "  "
        self.LEVEL = 0

    def inc(self, n= 1):
        self.LEVEL += 1 * n
        return self.spaces * self.LEVEL

    def dec(self, n=1):
        self.LEVEL -= 1 * n
        return self.spaces * self.LEVEL

    def get(self):
        return self.spaces * self.LEVEL


def log(parsed, data, fromLine=0, n=0):
    i = 0
    k = 0
    #print(parsed)
    while True:
        i += 1
        if parsed[i][1].start_point[0] >= fromLine:
            k += 1
            print("==>",parsed[i][1].start_point[0], i,  parsed[i][0], parsed[i][1].type, read(data, parsed[i][1]))
            if k > n:
                break

def process(parsed, data, header):
    indent = Indenter()
    nested = 0
    idx = 0
    tmp = ""
    i = 0
    txt = ""
    levelDelta = 0
    conditionLevel = 0
    access = None
    currentClass = []
    generalQualifier = set([]) # public, private, protected
    isFriend = False
    isFriendLevel = -1
    #log(parsed, data, 74, 80)
    #data = []
    while True:
        level, node = parsed[i]
        typ = node.type
        #print("== ", i, ">>",node.start_point[0],typ, read(data, node)[0:15])

        if typ in ["labeled_statement"]:
            pass
        
        elif level <= conditionLevel and conditionLevel != 0:
            conditionLevel = 0
            _indent = indent.dec()
            tmp += f'{_indent}block:\n'
            _indent = indent.inc()

        # Dealing with directives
        if typ in ["#ifndef", "#ifdef"]:
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "identifier"

            _indent = indent.get()
            tmp += f'{_indent}- CONDITION:\n'
            _indent = indent.inc()
            key = "defined"
            if typ == "#ifndef":
                key = "not_defined"
            tmp += f'{_indent}{key}: {read(data,node)}\n'
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1
            tmp += f'{_indent}block:\n'            
            _indent = indent.inc()

        elif typ == "#endif":
            _indent = indent.dec(2)

        elif typ == "preproc_directive":
            val = read(data,node)
            if val == "#endif":
                _indent = indent.dec(2)
            else:
                print("WARNING: not covered: preproc_directive:", val)

        elif typ == "preproc_if":
            _LEVEL = indent.LEVEL

            level, node = parsed[i]
            _lvl = level
            checkLevel = level           
            typ2 = node.type
            assert typ2 == "#if"  
            _indent = indent.inc()                     
            tmp += f'{_indent}- IF:\n'
            _indent = indent.inc()
            #----
            i += 1
            tmp += f'{_indent}raw: {read(data, parsed[i][1])}\n'    
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1            
            # Find first "binary_expression"
            while parsed[i][1].type != "binary_expression":
                i += 1
            _lvl = parsed[i][0] + 1
            i += 1
            while parsed[i][0] >= _lvl:
                i += 1
            #    i += 1
            tmp += f'{_indent}block:\n' 
            _indent = indent.inc()

        elif typ == "preproc_elif":
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "#elif"
            _indent = indent.dec(2)                      
            tmp += f'{_indent}- ELIF:\n'
            #LEVEL += 1
            _indent = indent.inc()
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1            

        elif typ == "preproc_else":
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "#else"  
            _indent = indent.dec(2)                   
            tmp += f'{_indent}- ELSE:\n'
            _indent = indent.inc() 
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1            

        elif typ == "preproc_include":
            # get key
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "#include"
            #_key = "include"
            
            # get value
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 in ["system_lib_string", "string_literal"]
            _value = read(data,node)
            _indent = indent.get() 
            tmp += f'{_indent}- include: {_value}\n'            
            _indent = indent.inc()
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1
            _indent = indent.dec()
        
        elif typ == "preproc_def":
            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "#define"
            _indent = indent.get()            
            tmp += f'{_indent}- define:\n' 

            i += 1
            level, node = parsed[i]
            typ2 = node.type
            assert typ2 == "identifier"
            _indent = indent.inc()  
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1                         
            tmp += f'{_indent}id: {read(data,node)}\n'
            _indent = indent.dec()             

            level, node = parsed[i+1]
            typ2 = node.type
            if typ2 == "preproc_arg":
                i += 1
                tmp += f'{_indent}arg: {read(data,node)}\n'
        
        # extern "C"{
        elif typ == "extern" and parsed[i+1][1].type == "string_literal": # Four different behaviours depending on context
            i += 1
            level, node = parsed[i]

            typ2 = node.type            
            assert typ2 == "string_literal"            
            _indent = indent.get() 
            _txt = read(data,node)

            level, node = parsed[i+1]

            while node.type in ["{", '}', '"']:
                if node.type != '"':
                    _txt += node.type
                i += 1
                level, node = parsed[i+1]           

            if _txt == '"C"{':
                tmp += f"{_indent}- extern: '{_txt}'\n"
                _indent = indent.inc() 
                tmp += f'{_indent}idx: {idx}\n'
                idx += 1                  
                _indent = indent.dec() 

        elif typ == "preproc_function_def":
            _indent = indent.get() 
            tmp += f"{_indent}- funcDefine:\n"
            
            i += 1
            level, node = parsed[i]  
            levelPreproc = level
            _indent = indent.inc() 

            assert node.type == "#define"

            i += 1
            level, node = parsed[i]  
            tmp += f"{_indent}id: {read(data, node)}\n"

            i += 1
            level, node = parsed[i]
            if node.type == "preproc_params":
                tmp += f"{_indent}params:\n"

                _indent = indent.inc()                 
                while True:
                    if parsed[i+1][1].type == "preproc_arg" or parsed[i+1][0] <= levelPreproc:  
                        break
                    i += 1
                    level, node = parsed[i]
                    if node.type == "identifier":
                        tmp += f"{_indent}- {read(data,node)}\n"
                _indent = indent.dec()                   
                i += 1
                level, node = parsed[i]
                if node.type == "preproc_arg":
                    tmp += f"{_indent}definition: '{read(data,node)}'\n"

            _indent = indent.dec()   


        elif typ == "friend":
            isFriend = True
            isFriendLevel = level            


        elif isFunction(data, parsed, i):            
            _d = getFunction( data, parsed, i, idx, isFriend )
            idx += 1 
            isFriend = False

            _tmp = ""
            if _d != None:
                _tmp = addFunction(_d, indent, currentClass, generalQualifier)

            tmp += _tmp

        #print("...")
        elif typ == "comment":
            isMultiline = False            
            txt = genComment(data, node)

            if txt[0:2] == "/*" or "\n" in txt:
                isMultiline = True

            _indent = indent.get()   
            if isMultiline:
                tmp += f'{_indent}- comment: >\n'
                tmp += textwrap.indent(txt, spaces* indent.LEVEL + "  ")
                tmp += '\n'
            else:
                if len(txt) > 0:
                    if txt[0] != "'" and txt[-1] != "'":
                        txt = "'" + txt + "'"
                tmp += f"{_indent}- comment: {txt}\n"

        
        elif typ == "preproc_defined":
            _indent = LEVEL * spaces            
            i += 1
            level, node = parsed[i]
            _level = level
            _type = None
            assert node.type == "defined"
            #if :
            _type = "isDefined"

            _id = None
            while True:
                i += 1                  
                level, node = parsed[i]
                if node.type == "identifier":
                    _id = read(data, node)
                    break
            tmp += f'{_indent}- {_type}: {_id}\n'            


        elif typ == "type_definition":
            raw = read(data, node)
            lvl = parsed[i][0]

            i += 1
            level, node = parsed[i]
            
            _indent = indent.get()
            assert node.type == "typedef"
            tmp += f'{_indent}- typedef:\n'
            _indent = indent.inc()
            tmp += f'{_indent}idx: {idx}\n'
            idx += 1               


            if parsed[i+1][1].type == "primitive_type":
                i += 1
                level, node = parsed[i]
                _indent = indent.get()                 
                tmp += f'{_indent}id: {read(data,node)}\n'

            if parsed[i+1][1].type == "function_declarator":
                i += 1
                level, node = parsed[i]
                _indent = indent.get()               
                tmp += f'{_indent}funcDecl: {read(data,node)}\n'
                #tmp += f'{_indent}raw: {raw}\n'

            # Read the remaining stuff (TODO: maybe it could be parsed better if needed)
            while parsed[i+1][0] > lvl:
                if parsed[i+1][1].type == "const":
                    _indent = indent.inc()
                    tmp += f'{_indent}qualifiers:\n'
                    _indent = indent.inc()
                    tmp += f'{_indent}- const\n'
                    _indent = indent.dec(2)
                i += 1  

            _indent = indent.dec()

        # ---------- CLASES
        elif typ == "field_declaration_list":
            #_indent = indent.inc()
            tmp += f'{_indent}block:\n'
            _indent = indent.inc()                    


        elif typ == "class_specifier": # This is for forward declaration
            _line = parsed[i][1].start_point[0]
            while True:
                i += 1
                if parsed[i][1].type == "type_identifier":
                    break
            #_data = {"className": read(data,parsed[i][1])}
            _className = read(data,parsed[i][1])

            # Continue reading items on the first line (looking for inheritance)
            _base = None
            isForwardDecl = False
            while parsed[i][1].start_point[0] == _line:  
                i += 1
                if parsed[i][1].type == "base_class_clause":
                    _base = read(data, parsed[i][1])
                if parsed[i][1].type == ";":
                    isForwardDecl = True
                    break

            if isForwardDecl:
                tmp += f'{indent.get()}- class:\n'
                _indent = indent.inc()       
                tmp += f'{_indent}idx: {idx}\n'
                idx += 1                        
                tmp += f'{_indent}id: {_className}\n'                
                tmp += f'{_indent}isForwardDecl: true\n'
                _indent = indent.dec()
                if _base != None:
                    _indent = indent.inc()
                    tmp += f'{_indent}base: {_base}\n'                 
            else:
                currentClass.append(_className)
                if _base != None:
                    currentClass.append(_base)


        elif typ in ["access_specifier", "statement_identifier"]:  
            _access = read(data, node)
            _access = _access.replace(":", "")            
            if "protected" in generalQualifier:
                generalQualifier.remove("protected")
            if "private" in generalQualifier:
                generalQualifier.remove("private")
            if "public" in generalQualifier:
                generalQualifier.remove("public")

                
            generalQualifier.add(_access)

        elif typ == "declaration":

            """
                tmp += f'{_indent}- declaration:\n'
                _indent = indent.inc()
                tmp += f'{_indent}idx: {idx}\n'
                idx += 1                   
                tmp += f'{_indent}id: {_functionID}\n'                
                tmp += f'{_indent}return: {_returnType}\n'
                tmp += f'{_indent}returnQualifiers: {_returnQualifiers}\n'
                _indent = indent.dec()
            """
            pass

        elif typ == "storage_class_specifier":
            lvl = level
            while True:
                i += 1
                level, node = parsed[i]
                if level <= lvl:
                    break

        elif typ in ["type_identifier", "primitive_type", "sized_type_specifier"]:      
            #print("---")
            line = node.start_point[0]
            #print("ll>", line) 
    
            level, node = parsed[i]
            lvl = level                      

            _type = read(data,node)
            _qualifiers = []
            _id = None
            while node.start_point[0] == line: #parsed[i][1].type != "identifier":
                i += 1
                level, node = parsed[i]
                #print(node.type)
                if set(node.type) == set(["*"]):
                    _qualifiers.append(node.type)
                if node.type in ["identifier", "field_identifier"]:
                    _id = read(data, parsed[i][1])
                    break

            if _id != None:
                _indent = indent.get() 
                tmp += f'{_indent}- declaration:\n' 

                _indent = indent.inc()
                tmp += f'{_indent}idx: {idx}\n'
                idx += 1                   
                tmp += f'{_indent}id: {_id}\n'            
                tmp += f'{_indent}type: {_type}\n'
                if len(_qualifiers) > 0:
                    tmp += f'{_indent}qualifiers:\n'                
                    _indent = indent.inc()
                    for q in _qualifiers:
                        tmp += f'{_indent}- {q}\n'
                    LEVEL -= 1
                _indent = indent.dec() 


        elif typ in [ ";", "(", ")", "{", "}", ',', ":", "\n", "ERROR", "public",
                      "translation_unit", "preproc_ifdef", "friend_declaration", 
                      "type_qualifier", "const", "field_declaration"]:
            pass

        # Unhandled types
        else:
            print("WARNING: unhandled", node.type, read(data, node))


        i += 1
        if i > len(parsed) - 1:
            break            

    return tmp

def show(parsed, data):
    for level, node in parsed:
        print( f"{'   ' * level}{level}: {node.type}" )
        print( data[node.start_byte:node.end_byte])


def parseFile(filename, passC=True):
    folder, header = os.path.split(filename)
    destination = header.lower()
    destination = os.path.splitext(destination)[0] + ".yaml"
    print(destination)

    try:
        fp = open(filename, "r")
        txt = fp.read()
        fp.close()

        data = bytes(txt, "utf8")

        parser = Parser()
        parser.set_language(CPP_LANGUAGE)
        tree = parser.parse(bytes(txt, "utf8") )
        cursor = tree.walk()

        parsed = walker(cursor)
        includes = get_includes(parsed, data)

        txt = process(parsed, data, header)
        print("Writting: ", destination)
        fp = open(destination, "w")

        fp.write( f"- filename: {filename}\n" )
        #if passC:
        #    fp.write( f'passC: "-I{folder}"\n' )

        fp.write(txt )
            #print(f"{'  ' * nested}{value}")
        fp.close()
        return includes        
    except FileNotFoundError:
        print("ERROR: File not found: ", filename)

#------------------------------
if __name__ == "__main__":
    import os
    #fileHeader = "/usr/share/arduino/hardware/archlinux-arduino/avr/cores/arduino/Arduino.h"
    #fileHeader = "/usr/share/arduino/hardware/archlinux-arduino/avr/cores/arduino/WString.h"
    fileHeader = "/usr/include/opencascade/gp_Ax3.hxx"    
    print(fileHeader)

    folder, header = os.path.split(fileHeader)
    includes = parseFile(fileHeader)

    # Process the other files
    for incl in includes:
        if incl[0] == '"':
            newHeader = incl[1:-1]
            newHeader = os.path.join(folder, newHeader)
            print(newHeader)
            parseFile(newHeader,passC=False)

"""
TODO:
void attachInterrupt(uint8_t interruptNum, void (*userFunc)(void), int mode);

proc attachInterrupt*(interruptNum: uint8_t; userFunc: proc (); mode: cint)


TODO
int atexit(void (*func)()) __attribute__((weak));


TODO: lista inicializadores de miembro
https://docs.microsoft.com/es-es/cpp/cpp/constructors-cpp?view=msvc-160#member-initializer-lists
"""