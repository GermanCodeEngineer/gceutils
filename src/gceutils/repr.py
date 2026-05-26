from __future__  import annotations
from dataclasses import fields
from enum        import Enum
from types       import NotImplementedType
from typing      import Any, TYPE_CHECKING

from gceutils.dual_key_dict import DualKeyDict

if TYPE_CHECKING:
    from dataclasses import Field
    from gceutils.base import AbstractTreePath


SpecialCaseResult = tuple[str, bool] | str | NotImplementedType


class KeyReprDict(dict[Any, Any]):
    """Dict subclass that displays only its keys in repr, not values. Inherits all dict functionality."""
    
    def __repr__(self) -> str:
        return grepr(self)

class RepresentationImplementation:
    """Architecture boilerplate for recursive representation with standard repr defaults."""

    def __init__(
        self,
        /, *,
        level_offset: int = 0,
        indent: int | str | None = 4,
    ) -> None:
        self.level_offset = level_offset
        self.indent = " " * indent if isinstance(indent, int) else indent

    def recursively_format(self, obj: Any) -> str:
        """Format an object using subclass rules from format_value."""
        return self.format_value(obj, self.level_offset)[0]

    def implement_special_cases(
        self,
        obj: Any,
        level: int,
        path: AbstractTreePath | None = None,
    ) -> SpecialCaseResult:
        """Return NotImplemented when unmatched, else str or (str, is_simple)."""
        return NotImplemented

    def format_value(
        self,
        obj: Any,
        level: int,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        """Format a value according to subclass rules, returning (formatted_str, is_simple)."""
        special_case = self.implement_special_cases(obj, level, path)
        if special_case is not NotImplemented:
            if isinstance(special_case, tuple):
                return special_case
            return special_case, True

        return repr(obj), True


class GreprRepresentationImplementation(RepresentationImplementation):
    """Concrete grepr style implementation layered on top of RepresentationImplementation."""

    def __init__(
        self,
        /, *,
        safe_dkd: bool = False,
        level_offset: int = 0,
        annotate_fields: bool = True,
        vanilla_strings: bool = False,
        indent: int | str | None = 4,
    ) -> None:
        super().__init__(level_offset=level_offset, indent=indent)
        self.safe_dkd = safe_dkd
        self.annotate_fields = annotate_fields
        self.vanilla_strings = vanilla_strings

    def is_compatible_dataclass_instance(self, obj: Any) -> bool:
        """Check whether object opts into grepr dataclass-style formatting."""
        return bool(getattr(obj, "__has_grepr__", False)) and not isinstance(obj, type)

    def recursively_format(self, obj: Any) -> str:
        """Format an object with optional path tracking for advanced subclass hooks."""
        return self.format_value(obj, self.level_offset, self.create_root_path())[0]

    def create_root_path(self) -> AbstractTreePath:
        """Create the root path used for recursive formatting traversal."""
        from gceutils.base import AbstractTreePath

        return AbstractTreePath(())

    def extend_path_with_attribute(self, path: AbstractTreePath | None, attr: str) -> AbstractTreePath | None:
        """Extend a path with a dataclass-style attribute segment."""
        if path is None:
            return None
        return path.add_attribute(attr)

    def extend_path_with_index_or_key(self, path: AbstractTreePath | None, index_or_key: Any) -> AbstractTreePath | None:
        """Extend a path with list/tuple index or mapping key segment."""
        if path is None:
            return None
        return path.add_index_or_key(index_or_key)

    def get_field_options(self, field: Field[Any]) -> dict[str, Any]:
        """Hook for dataclass field options lookup; overridable in subclasses."""
        from gceutils.base import get_field_options

        return get_field_options(field)

    def layout(self, level: int) -> tuple[int, str, str, str]:
        if self.indent is not None:
            level += 1
            prefix = "\n" + self.indent * level
            sep = ",\n" + self.indent * level
            end_sep = ",\n" + self.indent * (level - 1)
            return level, prefix, sep, end_sep
        return level, "", ", ", ""

    def format_value(
        self,
        obj: Any,
        level: int,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        special_case = self.implement_special_cases(obj, level, path)
        if special_case is not NotImplemented:
            if isinstance(special_case, tuple):
                return special_case
            return special_case, True

        next_level, prefix, sep, end_sep = self.layout(level)

        if isinstance(obj, (list, tuple, set)):
            return self.format_collection(obj, next_level, prefix, sep, end_sep, path)

        if isinstance(obj, DualKeyDict):
            return self.format_dual_key_dict(obj, next_level, prefix, sep, end_sep, path)

        if isinstance(obj, KeyReprDict):  # must come before isinstance(obj, dict)
            return self.format_key_repr_dict(obj, next_level, path)

        if isinstance(obj, dict):
            return self.format_dict(obj, next_level, prefix, sep, end_sep, path)

        if isinstance(obj, str):
            return self.format_string(obj)

        if self.is_compatible_dataclass_instance(obj):
            return self.format_compatible_obj(obj, next_level, prefix, sep, end_sep, path)

        return repr(obj), True

    def format_collection(
        self,
        obj: list[Any] | tuple[Any, ...] | set[Any],
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        opening, closing = (
            ("[", "]") if isinstance(obj, list) else ("(", ")") if isinstance(obj, tuple) else ("{", "}")
        )

        if not obj:
            return f"{opening}{closing}", True

        strings: list[str] = []
        allsimple = True
        for index, item in enumerate(obj):
            item_path = self.extend_path_with_index_or_key(path, index)
            item_s, simple = self.format_value(item, level, item_path)
            allsimple = allsimple and simple and (len(item_s) <= 40)
            strings.append(item_s)

        if allsimple:
            return f"{opening}{', '.join(strings)}{closing}", True
        return f"{opening}{prefix}{sep.join(strings)}{end_sep}{closing}", False

    def format_dual_key_dict(
        self,
        obj: DualKeyDict,
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        if not obj:
            return ("DualKeyDict()" if self.safe_dkd else "DualKeyDict{}"), True

        args: list[tuple[str, str, str]] = []
        for key1, key2, value in obj.items_key1_key2():
            branch_path = self.extend_path_with_index_or_key(path, (key1, key2))
            key1_str, _ = self.format_value(key1, level, branch_path)
            key2_str, _ = self.format_value(key2, level, branch_path)
            value_str, _ = self.format_value(value, level, branch_path)
            args.append((key1_str, key2_str, value_str))

        if self.safe_dkd:
            strings = [f"({key1_str}, {key2_str}): {value_str}" for key1_str, key2_str, value_str in args]
            fmt = "DualKeyDict({%s})"
        else:
            strings = [f"{key1_str} / {key2_str}: {value_str}" for key1_str, key2_str, value_str in args]
            fmt = "DualKeyDict{%s}"
        return fmt % f"{prefix}{sep.join(strings)}{end_sep}", False

    def format_key_repr_dict(
        self,
        obj: KeyReprDict,
        level: int,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        keys_str, is_simple = self.format_value(tuple(obj.keys()), level - 1, path)
        keys_str = "{" + keys_str.removeprefix("(").removesuffix(")") + "}"
        return f"KeyReprDict(keys={keys_str})", is_simple

    def format_dict(
        self,
        obj: dict[Any, Any],
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        if not obj:
            return "{}", True
        args: list[str] = []
        for key, value in obj.items():
            value_path = self.extend_path_with_index_or_key(path, key)
            key_s = self.format_value(key, level, value_path)[0]
            value_s = self.format_value(value, level, value_path)[0]
            args.append(f"{key_s}: {value_s}")
        return "{" + f"{prefix}{sep.join(args)}{end_sep}" + "}", False

    def format_string(self, obj: str) -> tuple[str, bool]:
        if self.vanilla_strings:
            return repr(obj), True

        obj = obj.replace("\\", "\\\\")
        if '"' in obj:
            if "'" in obj:
                return f'"{obj.replace('"', '\\"')}"', True
            return f"'{obj}'", True
        return f'"{obj}"', True

    def format_compatible_obj(
        self,
        obj: Any,
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
        path: AbstractTreePath | None = None,
    ) -> tuple[str, bool]:
        args: list[str] = []
        allsimple = True
        for field in fields(obj):
            options = self.get_field_options(field)
            if not options["grepr"]:
                continue
            if not hasattr(obj, field.name):
                continue
            value = getattr(obj, field.name)
            field_path = self.extend_path_with_attribute(path, field.name)
            value_str, simple = self.format_value(value, level, field_path)
            allsimple = allsimple and simple
            if self.annotate_fields:
                args.append(f"{field.name}={value_str}")
            else:
                args.append(value_str)

        class_name = obj.__class__.__name__
        if allsimple and len(args) <= 3:
            return f"{class_name}({', '.join(args)})", not args
        return f"{class_name}({prefix}{sep.join(args)}{end_sep})", False

def grepr(obj, /,
        safe_dkd:bool=False, level_offset:int=0, annotate_fields:bool=True,
        vanilla_strings:bool=False, *, indent:int|str|None=4,
    ) -> str:
    """
    Generate a custom string representation of an object with enhanced formatting.
    
    Provides pretty-printed output for dataclasses, collections, DualKeyDict, and nested structures.
    By default, dataclass fields marked with grepr=False are excluded from output.
    
    Returns:
        str: Formatted representation of the object
        
    Args:
        safe_dkd: If True, represent DualKeyDict using dict notation; otherwise use custom notation
        level_offset: Initial indentation level for nested structures
        annotate_fields: Include field names in dataclass representations
        vanilla_strings: If True, use repr() for strings; otherwise use custom quoting
        indent: Number of spaces (int) or indent string for multi-line formatting; None for single-line
    """
    formatter = GreprRepresentationImplementation(
        safe_dkd=safe_dkd,
        level_offset=level_offset,
        annotate_fields=annotate_fields,
        vanilla_strings=vanilla_strings,
        indent=indent,
    )
    return formatter.recursively_format(obj)

class GEnum(Enum):
    """Base class for enums with enhanced repr."""
    name: str
    value: Any

    def __repr__(self) -> str:
        return self.__class__.__name__ + "." + self.name


__all__ = [
    "KeyReprDict",
    "RepresentationImplementation",
    "GreprRepresentationImplementation",
    "grepr",
    "GEnum",
]

