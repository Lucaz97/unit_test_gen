# C Unit Test Generation Tool

## Overview
This repository provides a Python-based tool for analyzing function calls and generating test cases for C programs subroutines. It utilizes `pycparser` to parse C source files and extract function call hierarchies, parameters, and memory usage.

## Features
- Parses C source files to build function call hierarchies.
- Extracts function parameters and detects pointer-based arguments.
- Generates unit tests for C functions.
- Uses `clang` and `gdb` for compiling and debugging.
- Provides memory analysis for pointer variables.

## Dependencies
Ensure you have the following dependencies installed:
- Python 3.x
- `pycparser` (install via `pip install pycparser`)
- `clang` and `gdb` (for compiling and debugging C programs)
- `fsanitize`
## Usage

### Running the Tool
```sh
python generate_unit_test.py --file <c_source_file> --top <top_function> --tmp_folder <temporary_directory>
```
- `--file`: Path to the C source file to analyze.
- `--top`: Name of the top-level function to analyze.
- `--tmp_folder`: Directory to store temporary files.

### Example
```sh
python generate_unit_test.py --file tests/AES.c --top Cipher --tmp_folder ./tmp
```

## Components
- `CFG`: Stores function call data and analysis results.
- `FuncCallVisitor`: Extracts function call relationships.
- `HierarchyVisitor`: Analyzes function definitions and parameters.
- `PointerData`: Handles pointer-related memory analysis.
- `explore_calls()`: Recursively explores function call hierarchy.
- `fix_repeat()`: Expands repeated memory data representations.
- `build_unit_test()`: Generates unit tests based on extracted function parameters.

## Output
- A unit test C file for the analyzed function.
- Debugging logs generated by `gdb`.
- Function call relationships stored in internal data structures.

Example unit test:
```c
int main()
{
  uint8_t round = 0x0;
  unsigned int state[] = {2863311530, 2863311530, 2863311530, 2863311530};
  unsigned int RoundKey[] = {286331153, 286331153, 286331153, 286331153, 2475922322, 2189591171, 2475922322, 2189591171, 2139127939, 4244767232, 1855033746, 3960673041, 4249812474, 5046266, 1860005480, 2194570617, 1264416269, 1259440631, 634185631, 2801965798, 3305177509, 2383448146, 2883350477, 215938347, 889134179, 3136263217, 288619516, 502075095, 979061128, 2159336889, 2441553477, 2355767442, 1967082300, 4119565957, 1678553280, 3899037778, 1973712993, 2150624996, 3827523108, 205899382, 1297749731, 3447060487, 693544483, 622026837};
  AddRoundKey((uint8_t) round, (state_t *) state, (const expandedKey_t *) RoundKey);
  printf("%d\n", round);
  for (int _i = 0; _i < 4; _i++)
  {
    printf("%x ", state[_i]);
  }

  printf("\n");
  for (int _i = 0; _i < 44; _i++)
  {
    printf("%x ", RoundKey[_i]);
  }

  printf("\n");
}

```

## Example Unit Test:


## License
This project is licensed under the MIT License.
