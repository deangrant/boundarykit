# Examples (Yes / No)

## Lint unused args (2.1)

```python
# Yes
def viking_cafe_order(spam: str, beans: str, eggs: str | None = None) -> str:
    del beans, eggs  # Unused.
    return spam + spam + spam
```

## Imports and packages (2.2–2.3)

```python
# Yes
from absl import flags
from doctor.who import jodie
from collections.abc import Sequence
from typing import Any

# No — relative / ambiguous local bare import
from . import jodie
import jodie  # unclear if local sibling or third-party
```

## Assert vs raise (2.4)

```python
# Yes — validate with raise; assert only for non-critical sanity
if minimum < 1024:
    raise ValueError(f'Min. port must be at least 1024, not {minimum}.')
assert port >= minimum

# No — application logic depends on assert
assert minimum >= 1024
port = self._find_next_open_port(minimum)
assert port is not None
return port
```

## Comprehensions (2.7)

```python
# Yes
result = [mapping_expr for value in iterable if filter_expr]
result = []
for x in range(10):
    for y in range(5):
        if x * y > 10:
            result.append((x, y))

# No
result = [(x, y) for x in range(10) for y in range(5) if x * y > 10]
```

## Default iterators (2.8)

```python
# Yes
for key in adict:
    ...
for k, v in adict.items():
    ...

# No
for key in adict.keys():
    ...
for line in afile.readlines():
    ...
```

## Mutable defaults (2.12)

```python
# Yes
def append_to(element: str, target: list[str] | None = None) -> list[str]:
    if target is None:
        target = []
    target.append(element)
    return target

# No
def append_to(element: str, target: list[str] = []) -> list[str]:
    target.append(element)
    return target
```

## Truthiness (2.14)

```python
# Yes
if foo:
    ...
if foo is not None:
    ...
if i % 10 == 0:
    ...

# No
if foo == False:
    ...
if not i % 10:
    ...
```

## Indent and trailing commas (3.4)

```python
# Yes
foo = long_function_name(
    var_one,
    var_two,
    var_three,
    var_four,
)
golomb4 = [
    0,
    1,
    4,
    6,
]

# No
foo = long_function_name(var_one, var_two,
    var_three, var_four)
golomb4 = [
    0,
    1,
    4,
    6,]
```

## Annotated defaults (3.6 / 3.19.4)

```python
# Yes
def func(a: int = 0) -> int:
    ...

# No
def func(a: int=0) -> int:
    ...
```

## Function docstring (3.8.3)

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows from a Smalltable.

    Args:
        table_handle: An open smalltable.Table instance.
        keys: A sequence of strings representing the key of each table
          row to fetch.  String keys will be UTF-8 encoded.
        require_all_keys: If True only rows with values set for all keys will be
          returned.

    Returns:
        A dict mapping keys to the corresponding table row data fetched.

    Raises:
        IOError: An error occurred accessing the smalltable.
    """
```

## Class / exception docstring (3.8.4)

```python
# Yes
class OutOfCheeseError(Exception):
    """No more cheese is available."""

# No
class OutOfCheeseError(Exception):
    """Raised when no more cheese is available."""
```

## Logging vs f-strings (3.10.1)

```python
# Yes
logging.info('Current $PAGER is: %s', os.getenv('PAGER', default=''))

# No
logging.error(f'Cannot write to home directory, $HOME={homedir!r}')
```

## Resources (3.11)

```python
# Yes
with open('hello.txt') as hello_file:
    for line in hello_file:
        print(line)
```

## TODO (3.12)

```python
# Yes
# TODO: crbug.com/192795 - Investigate cpufreq optimizations.

# No (discouraged for new code)
# TODO(yourusername): Use a "*" here for concatenation operator.
```

## Import grouping (3.13)

```python
# Yes
from __future__ import annotations

import os
import sys

from absl import app
import tensorflow as tf

from book.genres import scifi
from myproject.backend import huxley

# No
import os, sys
```

## Main (3.17)

```python
# Yes
def main() -> None:
    ...


if __name__ == '__main__':
    main()
```

## Type line breaks (3.19.2)

```python
# Yes
def my_method(
    self,
    first_var: int,
    second_var: Foo,
    third_var: Bar | None,
) -> int:
    ...
```

## None and generics (3.19.5 / 3.19.15)

```python
# Yes
def modern(a: str | None = None) -> str:
    ...

def get_names(employee_ids: Sequence[int]) -> Mapping[int, str]:
    ...

# No
def implicit_optional(a: str = None) -> str:
    ...

def get_names(employee_ids: Sequence) -> Mapping:
    ...
```

## Typing imports (3.19.12)

```python
# Yes
from collections.abc import Mapping, Sequence

def transform_coordinates(
    original: Sequence[tuple[float, float]],
) -> Sequence[tuple[float, float]]:
    ...

# No (prefer abc + builtins over typing.List/Tuple)
from typing import List, Tuple

def transform_coordinates(
    original: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    ...
```
