from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Sequence, Set

import pyarrow as pa
import pyarrow.compute as pac
from pyarrow.compute import equal

from meerkat.block.abstract import BlockView
from meerkat.block.arrow_block import ArrowBlock
from meerkat.errors import ImmutableError
from meerkat.tools.lazy_loader import LazyLoader

from ..abstract import Column
from .abstract import ScalarColumn

if TYPE_CHECKING:
    from meerkat.interactive.formatter.base import Formatter


torch = LazyLoader("torch")


class ArrowScalarColumn(ScalarColumn):
    block_class: type = ArrowBlock

    def __init__(
        self,
        data: Sequence,
        *args,
        **kwargs,
    ):
        if isinstance(data, BlockView):
            if not isinstance(data.block, ArrowBlock):
                raise ValueError(
                    "ArrowArrayColumn can only be initialized with ArrowBlock."
                )
        elif not isinstance(data, (pa.Array, pa.ChunkedArray)):
            # Arrow cannot construct an array from a torch.Tensor.
            if isinstance(data, torch.Tensor):
                data = data.numpy()
            data = pa.array(data)

        super(ArrowScalarColumn, self).__init__(data=data, *args, **kwargs)

    def _get(self, index, materialize: bool = True):
        index = ArrowBlock._convert_index(index)

        if isinstance(index, slice) or isinstance(index, int):
            data = self._data[index]
        elif index.dtype == bool:
            data = self._data.filter(pa.array(index))
        else:
            data = self._data.take(index)

        if self._is_batch_index(index):
            return self._clone(data=data)
        else:
            # Convert to Python object for consistency with other ScalarColumn
            # implementations.
            return data.as_py()

    def _set(self, index, value):
        raise ImmutableError("ArrowArrayColumn is immutable.")

    def _repr_cell(self, index) -> object:
        return self.data[index]

    def _get_default_formatter(self) -> "Formatter":
        # can't implement this as a class level property because then it will treat
        # the formatter as a method
        from meerkat.interactive.app.src.lib.component.core.scalar import (
            ScalarFormatter,
        )
        from meerkat.interactive.app.src.lib.component.core.text import TextFormatter

        if len(self) == 0:
            return ScalarFormatter()

        if self.data.type == pa.string():
            return TextFormatter()

        cell = self[0]
        return ScalarFormatter(dtype=type(cell).__name__)

    def is_equal(self, other: Column) -> bool:
        if other.__class__ != self.__class__:
            return False
        return pac.all(pac.equal(self.data, other.data)).as_py()

    @classmethod
    def _state_keys(cls) -> Set:
        return super()._state_keys()

    def _write_data(self, path):
        table = pa.Table.from_arrays([self.data], names=["0"])
        ArrowBlock._write_table(os.path.join(path, "data.arrow"), table)

    @staticmethod
    def _read_data(path, mmap=False):
        table = ArrowBlock._read_table(os.path.join(path, "data.arrow"), mmap=mmap)
        return table["0"]

    @classmethod
    def concat(cls, columns: Sequence[ArrowScalarColumn]):
        arrays = []
        for c in columns:
            if isinstance(c.data, pa.Array):
                arrays.append(c.data)
            elif isinstance(c.data, pa.ChunkedArray):
                arrays.extend(c.data.chunks)
            else:
                raise ValueError(f"Unexpected type {type(c.data)}")
        data = pa.concat_arrays(arrays)
        return columns[0]._clone(data=data)

    def to_numpy(self):
        return self.data.to_numpy()

    def to_tensor(self):
        return torch.tensor(self.data.to_numpy())

    def to_pandas(self, allow_objects: bool = False):
        return self.data.to_pandas()

    def to_arrow(self) -> pa.Array:
        return self.data

    def dtype(self):
        pass

    def equals(self, other: Column) -> bool:
        if other.__class__ != self.__class__:
            return False
        return pac.all(pac.equal(self.data, other.data)).as_py()

    """TODO(KG)
    This column is missing a .dtype property that prevents
    it from being used with the Filter component.
    """

    KWARG_MAPPING = {"skipna": "skip_nulls"}
    COMPUTE_FN_MAPPING = {
        "var": "variance",
        "std": "stddev",
        "sub": "subtract",
        "mul": "multiply",
        "truediv": "divide",
    }

    def _dispatch_aggregation_function(self, compute_fn: str, **kwargs):
        kwargs = {self.KWARG_MAPPING.get(k, k): v for k, v in kwargs.items()}
        out = getattr(pac, self.COMPUTE_FN_MAPPING.get(compute_fn, compute_fn))(
            self.data, **kwargs
        )
        return out.as_py()

    def mode(self, **kwargs) -> ScalarColumn:
        if "n" in "kwargs":
            raise ValueError(
                "Meerkat does not support passing `n` to `mode` when "
                "backend is Arrow."
            )

        # matching behavior of Pandas, get all counts, but only return top modes
        struct_array = pac.mode(self.data, n=len(self), **kwargs)
        modes = []
        count = struct_array[0]["count"]
        for mode in struct_array:
            if count != mode["count"]:
                break
            modes.append(mode["mode"].as_py())
        return ArrowScalarColumn(modes)

    def median(self, skipna: bool = True, **kwargs) -> any:
        warnings.warn("Arrow backend computes an approximate median.")
        return pac.approximate_median(self.data, skip_nulls=skipna).as_py()

    def _dispatch_arithmetic_function(
        self, other: ScalarColumn, compute_fn: str, right: bool, **kwargs
    ):
        if isinstance(other, Column):
            assert isinstance(other, ArrowScalarColumn)
            other = other.data

        compute_fn = self.COMPUTE_FN_MAPPING.get(compute_fn, compute_fn)
        if right:

            out = self._clone(data=getattr(pac, compute_fn)(other, self.data, **kwargs))
            return out
        else:
            return self._clone(
                data=getattr(pac, compute_fn)(self.data, other, **kwargs)
            )
