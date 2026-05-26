from __future__  import annotations
from dataclasses import fields
from enum        import Enum
from typing      import Any

from gceutils.dual_key_dict import DualKeyDict


class KeyReprDict(dict):
    """Dict subclass that displays only its keys in repr, not values. Inherits all dict functionality."""
    
    def __repr__(self) -> str:
        return grepr(self)

class RepresentationImplementation:
    """Class-based grepr implementation that supports subclass customization. Entrypoint: `obj.recuresively_format()`"""

    def __init__(
        self,
        /,
        safe_dkd: bool = False,
        level_offset: int = 0,
        annotate_fields: bool = True,
        vanilla_strings: bool = False,
        *,
        indent: int | str | None = 4,
    ) -> None:
        self.safe_dkd = safe_dkd
        self.level_offset = level_offset
        self.annotate_fields = annotate_fields
        self.vanilla_strings = vanilla_strings
        self.indent = " " * indent if isinstance(indent, int) else indent

    def recursively_format(self, obj) -> str:
        """Format an object using grepr-compatible rules."""
        if self.is_supported_top_level(obj):
            return self.grepr_value(obj, self.level_offset)[0]
        return repr(obj)

    def implement_special_cases(self, obj, level: int) -> tuple[str, bool] | str | Any:
        """Return NotImplemented when unmatched, else str or (str, is_simple)."""
        return NotImplemented
    
    def is_supported_top_level(self, obj) -> bool:
        """Return True when object should use custom formatting at top-level."""
        return self.is_compatible_dataclass_instance(obj) or isinstance(
            obj,
            (list, tuple, set, DualKeyDict, dict, str),
        )

    def is_compatible_dataclass_instance(self, obj) -> bool:
        """Check whether object opts into grepr dataclass-style formatting."""
        return bool(getattr(obj, "__has_grepr__", False)) and not isinstance(obj, type)

    def get_field_options(self, field):
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

    def grepr_value(self, obj, level: int) -> tuple[str, bool]:
        special_case = self.implement_special_cases(obj, level)
        if special_case is not NotImplemented:
            if isinstance(special_case, tuple):
                return special_case
            return special_case, True

        next_level, prefix, sep, end_sep = self.layout(level)

        if isinstance(obj, (list, tuple, set)):
            return self.format_collection(obj, next_level, prefix, sep, end_sep)

        if isinstance(obj, DualKeyDict):
            return self.format_dual_key_dict(obj, next_level, prefix, sep, end_sep)

        if isinstance(obj, KeyReprDict):  # must come before isinstance(obj, dict)
            return self.format_key_repr_dict(obj, next_level)

        if isinstance(obj, dict):
            return self.format_dict(obj, next_level, prefix, sep, end_sep)

        if isinstance(obj, str):
            return self.format_string(obj)

        if self.is_compatible_dataclass_instance(obj):
            return self.format_compatible_obj(obj, next_level, prefix, sep, end_sep)

        return repr(obj), True

    def format_collection(
        self,
        obj: list | tuple | set,
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
    ) -> tuple[str, bool]:
        opening, closing = (
            ("[", "]") if isinstance(obj, list) else ("(", ")") if isinstance(obj, tuple) else ("{", "}")
        )

        if not obj:
            return f"{opening}{closing}", True

        strings = []
        allsimple = True
        for item in obj:
            item_s, simple = self.grepr_value(item, level)
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
    ) -> tuple[str, bool]:
        if not obj:
            return ("DualKeyDict()" if self.safe_dkd else "DualKeyDict{}"), True

        args = []
        for key1, key2, value in obj.items_key1_key2():
            key1_str, _ = self.grepr_value(key1, level)
            key2_str, _ = self.grepr_value(key2, level)
            value_str, _ = self.grepr_value(value, level)
            args.append((key1_str, key2_str, value_str))

        if self.safe_dkd:
            strings = [f"({key1_str}, {key2_str}): {value_str}" for key1_str, key2_str, value_str in args]
            fmt = "DualKeyDict({%s})"
        else:
            strings = [f"{key1_str} / {key2_str}: {value_str}" for key1_str, key2_str, value_str in args]
            fmt = "DualKeyDict{%s}"
        return fmt % f"{prefix}{sep.join(strings)}{end_sep}", False

    def format_key_repr_dict(self, obj: KeyReprDict, level: int) -> tuple[str, bool]:
        keys_str, is_simple = self.grepr_value(tuple(obj.keys()), level - 1)
        keys_str = "{" + keys_str.removeprefix("(").removesuffix(")") + "}"
        return f"KeyReprDict(keys={keys_str})", is_simple

    def format_dict(
        self,
        obj: dict,
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
    ) -> tuple[str, bool]:
        if not obj:
            return "{}", True
        args = [f"{self.grepr_value(key, level)[0]}: {self.grepr_value(value, level)[0]}" for key, value in obj.items()]
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
        obj,
        level: int,
        prefix: str,
        sep: str,
        end_sep: str,
    ) -> tuple[str, bool]:
        args = []
        allsimple = True
        for field in fields(obj):
            options = self.get_field_options(field)
            if not options["grepr"]:
                continue
            if not hasattr(obj, field.name):
                continue
            value = getattr(obj, field.name)
            value_str, simple = self.grepr_value(value, level)
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
    formatter = RepresentationImplementation(
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


__all__ = ["KeyReprDict", "RepresentationImplementation", "grepr", "GEnum"]

