<div align="center">

# gceutils

Python utilities for DRY tools, rich repr/validation helpers,  object-tree iteration & more.

</div>

---

## Features

The public API is kept intentionally small. Highlights:

- `grepr_dataclass`, `field`: Enhanced dataclasses with validation and improved representation
- `HasGreprValidate`: Protocol reflecting the effects of `grepr_dataclass`
- `AbstractTreePath`: Path abstraction for nested object trees (attributes, indexes, keys)
- `NotSet`, `NotSetType`: Unique sentinel useful for keyword arguments and defaults
- `enforce_argument_types`: Runtime enforcement of function argument types from annotations
- `enforce_type`: Recursive type checking against rich typing constructs
- `DualKeyDict`: Dictionary supporting two linked key spaces with full mapping features
- `GU_PathValidationError`: Validation error carrying an `AbstractTreePath` context

- `read_all_files_of_zip`: Read all files from a ZIP into a name→bytes map (with robust errors)
- `read_file_text`: Read text files with encoding and solid error reporting
- `write_file_text`: Write text files with encoding and solid error reporting
- `delete_file`: Remove a file with clear, specific exceptions
- `delete_directory`: Recursively remove a directory with clear, specific exceptions
- `create_zip_file`: Build a ZIP file from an in-memory name→bytes mapping
- `file_exists`: Lightweight existence check for a path

- `KeyReprDict`: Dict wrapper whose repr displays only keys
- `grepr`: Flexible pretty-printer for dataclasses, collections, dicts, and `DualKeyDict`
- `GEnum`: Enum base class with concise `Class.Member` repr

- `TreeVisitor`: Recursive traversal over dataclass-based object trees with type filtering

- `ValidateAttribute`: Prebuilt validators (type/range/length/formats)
- `is_valid_js_data_uri`: Validate JS data URIs
- `is_valid_directory_path`: Validate an existing or creatable, writable directory path
- `is_valid_url`: Validate basic HTTP(S) URLs with a domain

For the full, always-up-to-date list, see [features.md](features.md).

---

## Install

Python 3.12+ is required.

- From PyPI (if published):

```bash
pip install gceutils
```

- From source (editable):

```bash
git clone https://github.com/GermanCodeEngineer/gceutils.git
cd gceutils
pip install -e .
```

---

## Quick Examples

Validate attributes using built-in validators:

```python
from gceutils import grepr_dataclass, ValidateAttribute as VA, AbstractTreePath, HasGreprValidate
from datetime import date

@grepr_dataclass()
class Config(HasGreprValidate): # HasGreprValidate is optional, just helps type checkers
	color: str

	def post_validate(self, path: AbstractTreePath) -> None:
		# Additional validation can be done here if needed
		if date.today().weekday() == 1:
			VA.VA_HEX_COLOR(self, path, "color", condition="on mondays")

cfg = Config(color="#FF0956e") # not valid
cfg.validate(path=AbstractTreePath(())) # Ensures color is a str and hex color
```
Output(abbreviated):
```
gceutils.errors.GU_InvalidValueError: on tuesdays: color of a __main__.Config must be a valid hex color eg. '#FF0956'
```

Traverse an object tree and collect specific node types:

```python
from gceutils import grepr_dataclass, grepr, TreeVisitor

@grepr_dataclass()
class Node:
	name: str
	children: list["Node"]

root = Node("root", [Node("a", []), Node("b", [])])
visitor = TreeVisitor.create_new_include_only([Node])
matches = visitor.visit_tree(root)  # {AbstractTreePath: Node}
print("My matches:", grepr(matches))
```
Output:
```
My matches: {
    AbstractTreePath(.children[0]): Node(name="a", children=[]),
    AbstractTreePath(.children[1]): Node(name="b", children=[]),
}
```

Read all files from a ZIP and pretty-print a structure:

```python
from gceutils import read_all_files_of_zip, grepr

contents = read_all_files_of_zip("archive.zip")  # {"path/inside.txt": b"..."}
print(grepr(list(contents.keys()), indent=2))
```

---

## Testing

This repo uses `pytest`.

```bash
pytest
```

---

## Contributing

Contribution is welcomed and encouraged.

---

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

