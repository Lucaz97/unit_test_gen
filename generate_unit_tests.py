
from pycparser import c_ast, parse_file, c_generator, c_parser
from subprocess import Popen, PIPE, STDOUT
from collections import OrderedDict
import os
import argparse


# array printer template
array_printer = """
void func() {{
for(int _i = 0; _i < {size}; _i++) {{
    printf("%x ", {name}[_i]);
}}
printf("\\n");
}}
"""

class CFG:
    def __init__(self, args):
        self.tmp_folder = args.tmp_folder
        # make dir if does not exist
        if not os.path.exists(self.tmp_folder):
            os.makedirs(self.tmp_folder)
        self.top = args.top
        self.filename = args.file
        self.hierarchical_calls = []
        self.calls_table = {}
        self.params_table = {}
        self.nodes_table = {}
        self.params_pointers_table = {}
        self.structs_table = {}
       
#--------------------------------------------------------------------------------------#
#                          FUNCTION CALL VISITOR CLASS                                 #
#--------------------------------------------------------------------------------------#
class FuncCallVisitor(c_ast.NodeVisitor):
    # this visitor needs to know the name of itself before
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg

    def visit_FuncCall(self, node):
        #print(self.name, " calls", node.name.name)
        cfg.calls_table[self.name].append(node.name.name)


#--------------------------------------------------------------------------------------#
#                             HIERARCHY VISITOR CLASS                                  #
#--------------------------------------------------------------------------------------#
class HierarchyVisitor(c_ast.NodeVisitor):
    def __init__(self, cfg):
        self.cfg = cfg

    def visit_FuncDef(self, node):
        #print('%s at %s' % (node.decl.name, node.decl.coord))
        self.cfg.nodes_table[node.decl.name] = node
        self.cfg.calls_table[node.decl.name] = []
        self.cfg.params_table[node.decl.name] = []
        if node.decl.type.args:
            self.cfg.params_table[node.decl.name] = [(param.type, param.name) for param in node.decl.type.args]
            self.cfg.params_pointers_table[node.decl.name] = 1 in [1 if isinstance(param.type, c_ast.PtrDecl) or isinstance(param.type, c_ast.ArrayDecl) else 0 for param in node.decl.type.args]
        v = FuncCallVisitor(node.decl.name, self.cfg)
        v.visit(node)


#--------------------------------------------------------------------------------------#
#                                 POINTER DATA CLASS                                   #
#--------------------------------------------------------------------------------------#
class PointerData():
    def __init__(self):
        self.byte_offset = 0     # this is in bytes
        self.byte_size = 0  # this is in bytes
        self.base = 0
        self.type_size = 0 # this is in bytes for each element
        self.element_offset = 0  # this is byte_offset/type_size
        self.element_size = 0 # this is in ellements



########################################################################################
#                                   EXPLORE CALLS                                      #
########################################################################################
def explore_calls(top, hierarchical_calls, cfg): # gets called with different top and hierarchical, hence cannot take those from cfg
    for func in cfg.calls_table[top]:
        if func in cfg.calls_table:
            explore_calls(func, hierarchical_calls, cfg)
        if func not in hierarchical_calls:
            hierarchical_calls.append(func)
    if top not in hierarchical_calls:
        hierarchical_calls.append(top)
    return hierarchical_calls




########################################################################################
#                                   FIX REPEATS                                        #
########################################################################################
def fix_repeat(string):
    # string be like [0x0, 0x1, 0x2, 0x3, 0x4, 0x5 <repeats 11 times>, 0x10, 0x11, 0x12, 0x13]
    # we need to expand the repeat
    if "repeat" not in string:
        return string
    item_to_fix = ""
    fixed = ""
    if "," not in string:
        # string is {0x0 <repeats 64 times>}
        to_expand = string[1:].split(" ")[0]+ " ,"
        expanded = to_expand * int(string.split("repeats")[1].split("times>")[0])
        fixed = "[" + expanded[:-1] + "]" # remove last comma
        return fixed
    for element in string.split(","):
        if "repeats" in element:
            item_to_fix = element
            fixed += "{expanded}"
        else:
            fixed += element
            fixed += ","
    if "times>]" in item_to_fix:
        # the repeat is at the end
        to_expand = item_to_fix.split("<repeats")[0] + ","
        times = int(item_to_fix.split("repeats")[1].split("times>")[0])
        expanded = to_expand * times
        fixed = fixed.format(expanded=expanded)
        fixed = fixed[:-1]+"]"
    else:
        fixed = fixed[:-1]
        to_expand = item_to_fix.split("<repeats")[0] + ","
        if "[" in to_expand: # this is the first element
            to_expand = to_expand[1:]
            append ="["
        else:
            append = ""
        times = int(item_to_fix.split("repeats")[1].split("times>")[0])
        expanded = to_expand * times
        fixed = fixed.format(expanded=expanded)
        fixed = append + fixed
    # print(fixed.format(expanded=expanded))
    return fixed


########################################################################################
#                                  BUILD UNIT TEST                                     #
#######################################################################################
def build_unit_test(func, cfg):
    print("Building unit test for ", func)

    # compile the file with gcc
    print(" ".join(["clang","-ggdb", "-g3", "-O0", "-fsanitize=address",cfg.filename, "-o", f"{cfg.tmp_folder}to_debug"]), flush=True)
    p= Popen(["clang","-ggdb", "-g3", "-O0", "-fsanitize=address",cfg.filename, "-o", f"{cfg.tmp_folder}to_debug"])
    p.wait()
    # get param values
    # build gdb script
    pointers_table = OrderedDict() # associates a pointer to its characteristics 

    if cfg.params_pointers_table[func]:
        # we need to run gdb twice, first time to get the addresses and sizes of memory locations and second time to print those out
        # get addresses
        with open(f"{cfg.tmp_folder}" + func + "_gdb.py", "w") as f:
            print("import gdb", file =f)
            print(f"""gdb.execute("set print elements unlimited")""", file=f)
            print(f"""gdb.execute("file {cfg.tmp_folder}to_debug")""", file=f)
            print(f"""gdb.execute("break {func}")""", file =f)
            print("""gdb.execute("run")""", file =f)

            generator = c_generator.CGenerator()
            for param in cfg.params_table[func]:
                if isinstance(param[0], c_ast.PtrDecl) or isinstance(param[0], c_ast.ArrayDecl):
                    print(f"""gdb.execute("p (void) __asan_describe_address({param[-1]})")""", file =f)
                    ptr_type = generator.visit(param[0].type)
                    if "[" in ptr_type:
                        ptr_type = ptr_type.split("[")[0]
                    print(f"""gdb.execute('printf "sizeof {param[-1]} %d\\\\n", sizeof({ptr_type})')""", file =f)
                    pointers_table[param[-1]] = PointerData()
            print("""gdb.execute("quit")""", file =f)

        #run debug 
        p = Popen(["gdb"], stdout=PIPE, stdin=PIPE, stderr=PIPE, bufsize=0, text=True)
        stdout_data, stderr_data = p.communicate(input=f"\n\nsource {cfg.tmp_folder}{func}_gdb.py\n")
        
        with open(f"{cfg.tmp_folder}" + func + "_gdb_fsan.log", "w") as f:
            dbg_out = stdout_data.replace(", \n", ",")
            dbg_out += "STDERR\n"
            dbg_out += stderr_data.replace(", \n", ",")
            print(dbg_out, file=f) # this is just for debugging
        print(cfg.params_table)
        print(pointers_table)
        keys_list = list(pointers_table.keys())
        idx = 0 # tracks pointer number
        for line in dbg_out.split("\n"):
            
            if "sizeof" in line: 
                name = line.split(" ")[1]
                type_size = int(line.split(" ")[2])
                pointers_table[name].type_size = type_size
            # 3 cases for offset size and base: local array global array dynamic array
            elif "global variable" in line:
                #print(line)
                # 0x00000074bb80 is located 0 bytes inside of global variable 'array' defined in 'global.c' (0x74bb80) of size 80
                offset = int(line.split("located ")[1].split(" bytes")[0])
                size = int(line.split("of size ")[1])
                base = int(line.split("defined in '")[1].split("'")[1].split("(")[1].split(")")[0], 16)
                #print(offset, size, hex(base), idx)
                pointers_table[keys_list[idx]].byte_offset = offset
                pointers_table[keys_list[idx]].byte_size = size
                pointers_table[keys_list[idx]].base = base
                pointers_table[keys_list[idx]].element_offset = offset//pointers_table[keys_list[idx]].type_size
                idx +=1
            elif "region" in line:
                #print(line)
                # 0x507000000090 is located 0 bytes inside of 80-byte region [0x507000000090,0x5070000000e0)
                offset = int(line.split("inside of ")[1].split("-byte")[0])
                base = int(line.split("[")[1].split(",")[0], 16)
                #print(offset, size, hex(base), idx)
                pointers_table[keys_list[idx]].byte_offset = offset
                pointers_table[keys_list[idx]].byte_size = size
                pointers_table[keys_list[idx]].base = base
                pointers_table[keys_list[idx]].element_offset = offset//pointers_table[keys_list[idx]].type_size
                idx +=1
            elif "Address " in line:
                #print(line)
                # Address 0x7ffff3f00048 is located in stack of thread T0 at offset 72 in frame
                base = int(line.split("Address ")[1].split(" is")[0], 16)
            elif "Memory access" in line: 
                # print(line)
                # print(idx)
                # print(keys_list)
                # print(pointers_table[keys_list[idx]].type_size)
                # [32, 112) 'array3' (line 19) <== Memory access at offset 72 is inside this variable
                # base is taken from elif above
                # offset is given from frame pointer, have to shift it to our base
                offset = (int(line.split("offset ")[1].split(" is")[0]) - int(line.split("[")[1].split(",")[0])) 
                size = int(line.split("[")[1].split(",")[1].split(")")[0]) - int(line.split("[")[1].split(",")[0])
                base = base - offset
                # print(offset, size, hex(base), idx)
                # print(keys_list)
                pointers_table[keys_list[idx]].byte_offset = offset
                pointers_table[keys_list[idx]].byte_size = size
                pointers_table[keys_list[idx]].base = base
                pointers_table[keys_list[idx]].element_offset = offset//pointers_table[keys_list[idx]].type_size
                idx +=1
            #else: print(line)
    # get values
    with open(f"{cfg.tmp_folder}" + func + "_gdb.py", "w") as f:
        print("import gdb", file =f)
        print(f"""gdb.execute("set print elements unlimited")""", file=f)
        print(f"""gdb.execute("file {cfg.tmp_folder}to_debug")""", file=f)
        print(f"""gdb.execute("break {func}")""", file =f)
        print("""gdb.execute("run")""", file =f)
        
        for param in cfg.params_table[func]:
            if isinstance(param[0], c_ast.PtrDecl) or isinstance(param[0], c_ast.ArrayDecl):
                print(f"""gdb.execute("p/x *({pointers_table[param[-1]].base})@{pointers_table[param[-1]].byte_size//4}")""", file =f) ## print 4 bytes at a time
            else:
                print(f"""gdb.execute("p/x {param[-1]}")""", file =f)

        print("""gdb.execute("quit")""", file =f)
    # run debug
    p = Popen(["gdb"], stdout=PIPE, stdin=PIPE, stderr=PIPE, bufsize=0, text=True)
    stdout_data, stderr_data = p.communicate(input=f"\n\nsource {cfg.tmp_folder}{func}_gdb.py\n")
    
    with open(f"{cfg.tmp_folder}" + func + "_gdb.log", "w") as f:
        dbg_out = stdout_data.replace(", \n", ",")
        print(dbg_out, file=f) # this is just for debugging but info form fsan is in stderr

    # build the test functoin
    main_decl = c_ast.Decl("main", [], [], [], [], c_ast.FuncDecl(c_ast.ParamList([]), c_ast.TypeDecl("main", [], [], c_ast.IdentifierType(['int']))), None, None)
    main_def = c_ast.FuncDef(main_decl, None, c_ast.Compound([]))
    # add def of params
    n_params = len(cfg.params_table[func])
    for i in range(n_params):
        # find init values
        lines = dbg_out.split("\n")
        multiline = False
        for j in range(len(lines)):
            if not multiline:
                line = lines[j]
            else:
                line = line + lines[j]
            if line.startswith(f"${i+1} = "):
                if lines[j+1].startswith("$") or lines[j+1].startswith("Breakpoint") or "process" in lines[j+1] or line.count("{") == line.count("}"):    
                    multiline = False
                    # is a pointer
                    # pointers_table[params_table[func][i][1]] = (0,0)
                    init = c_ast.Constant(c_ast.IdentifierType(['int']), "0")
                    if "{" in line and line.count("=") == 1:
                        # is a single array
                        value = line.split(" = ")[1]
                        value = value.replace("{", "[").replace("}", "]")
                        if "repeat" in value:
                            value = fix_repeat(value)
                        value = eval(value)
                        pointers_table[cfg.params_table[func][i][1]].element_size = len(value) # array dimensions and sizes
                        init = c_ast.InitList([c_ast.Constant(c_ast.IdentifierType(['int']), str(val)) for val in value])
                    elif "{" in line and line.count("=") > 1:
                        # it's a struct
                        # needs to go from {size = 0x14, key = 0x37} to [0x14, key = 0x37]
                        value = "=".join(line.split(" = ")[1:])[1:-1]
                        elements = value.split(",")
                        cfg.structs_table[cfg.params_table[func][i][1]] = []
                        values = []
                        for element in elements:
                            split = element.split("=")
                            values.append(split[1].strip())
                            cfg.structs_table[cfg.params_table[func][i][1]].append(split[0].strip())
                        value = "[" + ", ".join(values) + "]"
                        value = fix_repeat(value)
                        value = eval(value)
                        init = c_ast.InitList([c_ast.Constant(c_ast.IdentifierType(['int']), str(val)) for val in value])
                    else:
                        value = line.split(" = ")[1]
                        init =c_ast.Constant(c_ast.IdentifierType(['int']), value)
                        #pointers_table[params_table[func][i][1]] = (0,0)
                else:
                    multiline = True
        if isinstance(cfg.params_table[func][i][0], c_ast.PtrDecl) or isinstance(cfg.params_table[func][i][0], c_ast.ArrayDecl):
            array_type = c_ast.TypeDecl(cfg.params_table[func][i][1], [], [], c_ast.IdentifierType(['unsigned','int']))
            main_def.body.block_items.append(c_ast.Decl(cfg.params_table[func][i][1], [], [], [], None, c_ast.ArrayDecl(array_type, None, None), init, None))
        elif isinstance(cfg.params_table[func][i][0], c_ast.TypeDecl): # struct
            main_def.body.block_items.append(c_ast.Decl(cfg.params_table[func][i][1], [], [], [], None, c_ast.TypeDecl(cfg.params_table[func][i][1], None, None, cfg.params_table[func][i][0]), init, None))
        else:
            main_def.body.block_items.append(c_ast.Decl(cfg.params_table[func][i][1], [], [], [], None, cfg.params_table[func][i][0].type, init, None))
    # build param list for call to function
    expr_list = []
    for param in cfg.params_table[func]:
        #if not isinstance(param[0], c_ast.PtrDecl) and not isinstance(param[0], c_ast.ArrayDecl):
        if isinstance(param[0], c_ast.ArrayDecl): 
            expr_list.append(c_ast.Cast(c_ast.PtrDecl( None,param[0].type) ,c_ast.ID(param[1])))
        else:
            expr_list.append(c_ast.Cast(param[0],c_ast.ID(param[1])))
       
    # check function node for return type
    if cfg.nodes_table[func].decl.type.type.type.names[0] == "void":
        # add call to function
        main_def.body.block_items.append(c_ast.FuncCall(c_ast.ID(func), c_ast.ExprList(expr_list)))
    else:
        # need to add a variable to store the return value
        main_def.body.block_items.append(c_ast.Decl("ret", [], [], [], None, c_ast.TypeDecl("ret", [], [], c_ast.IdentifierType(cfg.nodes_table[func].decl.type.type.type.names)), None, None))
        # add call to function and assugn return value to ret
        main_def.body.block_items.append(c_ast.Assignment("=", c_ast.ID("ret"), c_ast.FuncCall(c_ast.ID(func), c_ast.ExprList(expr_list))))
        # add print of ret
        main_def.body.block_items.append(c_ast.FuncCall(c_ast.ID("printf"), c_ast.ExprList([c_ast.Constant(c_ast.IdentifierType(['char']), f'"%d\\n"'), c_ast.ID("ret")])))                           
    # add prints
    for i in range(n_params):
        if isinstance(cfg.params_table[func][i][0], c_ast.PtrDecl) or isinstance(cfg.params_table[func][i][0], c_ast.ArrayDecl):
            if cfg.params_table[func][i][1] in pointers_table:
                code_str = array_printer.format(name=cfg.params_table[func][i][1], size=pointers_table[cfg.params_table[func][i][1]].element_size)
            else:
                main_def.body.block_items.append(c_ast.FuncCall(c_ast.ID("printf"), c_ast.ExprList([c_ast.Constant(c_ast.IdentifierType(['char']), f'"%d\\n"'), c_ast.ID(cfg.params_table[func][i][1])])))
                continue
            for_ast = c_parser.CParser().parse(code_str).ext[0]
            main_def.body.block_items.extend(for_ast.body.block_items)
        elif isinstance(cfg.params_table[func][i][0], c_ast.TypeDecl) and isinstance(cfg.params_table[func][i][0].type, c_ast.Struct):
                for element in cfg.structs_table[cfg.params_table[func][i][1]]:
                    main_def.body.block_items.append(c_ast.FuncCall(c_ast.ID("printf"), c_ast.ExprList([c_ast.Constant(c_ast.IdentifierType(['char']), f'"{element} %d\\n"'), c_ast.ID(f"{cfg.params_table[func][i][1]}.{element}")])))
        else:
            main_def.body.block_items.append(c_ast.FuncCall(c_ast.ID("printf"), c_ast.ExprList([c_ast.Constant(c_ast.IdentifierType(['char']), f'"%d\\n"'), c_ast.ID(cfg.params_table[func][i][1])])))

    generator = c_generator.CGenerator()
    with open(f"{cfg.tmp_folder}" + func + ".c", "w") as f:
        children = []
        explore_calls(func, children, cfg)
        for child_func in children:
            print(generator.visit(cfg.nodes_table[child_func]), file=f)
    with open(f"{cfg.tmp_folder}" + func + "_test.c", "w") as f:
        print(generator.visit(main_def), file=f)



# main
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Automatic Unit Test Generator for C Programs.\nUsage: python gen.py -f <file.c> -t <tmp_folder>')
    parser.add_argument('-f', '--file', type=str, help='C file to generate unit tests for', required=True)
    parser.add_argument('-t', '--top', type=str, help='Top Function: function for which a test is provided', required=True)
    parser.add_argument('--tmp_folder', type=str, default="tmp/", help='Temporary folder to store files', required=False)
    args = parser.parse_args()

    cfg = CFG(args)

    ast = parse_file(cfg.filename, use_cpp=True, cpp_args=r'-Iutils/fake_libc_include')
    v = HierarchyVisitor(cfg)
    v.visit(ast)
    explore_calls(cfg.top, cfg.hierarchical_calls, cfg)
    for func in cfg.hierarchical_calls:
        build_unit_test(func, cfg)
    