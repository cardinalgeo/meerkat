import logging
import warnings
from typing import Any, Generic, Iterator, List, Tuple, Union

from pydantic import BaseModel, Field, ValidationError
from pydantic.fields import ModelField
from wrapt import ObjectProxy

from meerkat.interactive.graph.reactivity import _reactive, is_reactive, no_react, react
from meerkat.interactive.modification import StoreModification
from meerkat.interactive.node import NodeMixin
from meerkat.interactive.types import Storeable, T
from meerkat.mixins.identifiable import IdentifiableMixin

__all__ = ["Store", "StoreFrontend", "make_store", "store_field"]
logger = logging.getLogger(__name__)


class StoreFrontend(BaseModel):
    store_id: str
    value: Any
    has_children: bool
    is_store: bool = True


# ObjectProxy must be the last base class
class Store(IdentifiableMixin, NodeMixin, Generic[T], ObjectProxy):
    _self_identifiable_group: str = "stores"

    def __init__(self, wrapped: T, backend_only: bool = False):
        if isinstance(wrapped, Iterator):
            warnings.warn(
                "Wrapping an iterator in a Store is not recommended. "
                "If the iterator is derived from an iterable, wrap the iterable:\n"
                "    >>> store = mk.gui.Store(iterable)\n"
                "    >>> iterator = iter(store)"
            )
        super().__init__(wrapped=wrapped)
        # Set up these attributes so we can create the
        # schema and detail properties.
        self._self_schema = None
        self._self_detail = None
        self._self_value = None
        self._self_backend_only = backend_only

    @property
    def value(self):
        return self.__wrapped__

    def to_json(self):
        return self.__wrapped__

    @property
    def frontend(self):
        return StoreFrontend(
            store_id=self.id,
            value=self.__wrapped__,
            has_children=self.inode.has_children() if self.inode else False,
        )

    @property
    def detail(self):
        return f"Store({self.__wrapped__}) has id {self.id} and node {self.inode}"

    def set(self, new_value: T):
        """Set the value of the store."""
        if isinstance(new_value, Store):
            # if the value is a store, then we need to unpack so it can be sent to the
            # frontend
            new_value = new_value.__wrapped__

        logging.debug(f"Setting store {self.id}: {self.value} -> {new_value}.")

        # TODO: Find operations that depend on this store and edit the cache.
        # This should be done in the StoreModification
        mod = StoreModification(id=self.id, value=new_value)
        self.__wrapped__ = new_value
        mod.add_to_queue()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(self.__wrapped__)})"

    @_reactive
    def __call__(self):
        return self.__wrapped__()

    def __getattr__(self, name: str) -> Any:
        # Only create a reactive function if we are in a reactive context
        # This is like creating another `getattr` function that is reactive
        # and calling it with `self` as the first argument.
        if is_reactive():

            @react
            def wrapper(wrapped, name: str = name):
                return getattr(wrapped, name)

            # Note: this should work for both methods and properties.
            return wrapper(self)
        else:
            # Otherwise, just return the `attr` as is.
            return getattr(self.__wrapped__, name)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field: ModelField):
        if not isinstance(v, cls):
            if not field.sub_fields:
                # Generic parameters were not provided so we don't try to validate
                # them and just return the value as is
                return cls(v)
            else:
                # Generic parameters were provided so we try to validate them
                # and return a Store object
                v, error = field.sub_fields[0].validate(v, {}, loc="value")
                if error:
                    raise ValidationError(error)
                return cls(v)
        return v

    @_reactive
    def __lt__(self, other):
        return super().__lt__(other)

    @_reactive
    def __le__(self, other):
        return super().__le__(other)

    @_reactive
    def __eq__(self, other):
        return super().__eq__(other)

    @_reactive
    def __ne__(self, other):
        return super().__ne__(other)

    @_reactive
    def __gt__(self, other):
        return super().__gt__(other)

    @_reactive
    def __ge__(self, other):
        return super().__ge__(other)

    def __hash__(self):
        return hash(self.__wrapped__)

    @_reactive
    def __nonzero__(self):
        return super().__nonzero__()

    def __bool__(self):
        # __bool__ cannot be reactive because Python expects
        # __bool__ to return a bool and not a Store.
        # This means stores cannot be used in logical statements.
        if is_reactive():
            warnings.warn(
                "bool(store) is not reactive. If you are using the store in "
                "a logical context and you want to preserve reactivity, you "
                "should use `mk.to_bool` (equivalent to `bool(store)`) or "
                "`mk.cnot` (equivalent to `not store`)."
            )
        return super().__bool__()

    @_reactive
    def to_str(self):
        return super().__str__()

    @_reactive
    def __add__(self, other):
        return super().__add__(other)

    @_reactive
    def __sub__(self, other):
        return super().__sub__(other)

    @_reactive
    def __mul__(self, other):
        return super().__mul__(other)

    @_reactive
    def __div__(self, other):
        return super().__div__(other)

    @_reactive
    def __truediv__(self, other):
        return super().__truediv__(other)

    @_reactive
    def __floordiv__(self, other):
        return super().__floordiv__(other)

    @_reactive
    def __mod__(self, other):
        return super().__mod__(other)

    # @reactive(nested_return=False)
    def __divmod__(self, other):
        return super().__divmod__(other)

    @_reactive
    def __pow__(self, other, *args):
        return super().__pow__(other, *args)

    @_reactive
    def __lshift__(self, other):
        return super().__lshift__(other)

    @_reactive
    def __rshift__(self, other):
        return super().__rshift__(other)

    @_reactive
    def __and__(self, other):
        return super().__and__(other)

    @_reactive
    def __xor__(self, other):
        return super().__xor__(other)

    @_reactive
    def __or__(self, other):
        return super().__or__(other)

    @_reactive
    def __radd__(self, other):
        return super().__radd__(other)

    @_reactive
    def __rsub__(self, other):
        return super().__rsub__(other)

    @_reactive
    def __rmul__(self, other):
        return super().__rmul__(other)

    @_reactive
    def __rdiv__(self, other):
        return super().__rdiv__(other)

    @_reactive
    def __rtruediv__(self, other):
        return super().__rtruediv__(other)

    @_reactive
    def __rfloordiv__(self, other):
        return super().__rfloordiv__(other)

    @_reactive
    def __rmod__(self, other):
        return super().__rmod__(other)

    @_reactive
    def __rdivmod__(self, other):
        return super().__rdivmod__(other)

    @_reactive
    def __rpow__(self, other, *args):
        return super().__rpow__(other, *args)

    @_reactive
    def __rlshift__(self, other):
        return super().__rlshift__(other)

    @_reactive
    def __rrshift__(self, other):
        return super().__rrshift__(other)

    @_reactive
    def __rand__(self, other):
        return super().__rand__(other)

    @_reactive
    def __rxor__(self, other):
        return super().__rxor__(other)

    @_reactive
    def __ror__(self, other):
        return super().__ror__(other)

    # We do not need to decorate i-methods because they call their
    # out-of-place counterparts, which are reactive
    def __iadd__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__iadd__ is out-of-place. Use __add__ instead."
        )
        return self.__add__(other)

    def __isub__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__isub__ is out-of-place. Use __sub__ instead."
        )
        return self.__sub__(other)

    def __imul__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__imul__ is out-of-place. Use __mul__ instead."
        )
        return self.__mul__(other)

    def __idiv__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__idiv__ is out-of-place. Use __div__ instead."
        )
        return self.__div__(other)

    def __itruediv__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__itruediv__ is out-of-place. "
            "Use __truediv__ instead."
        )
        return self.__truediv__(other)

    def __ifloordiv__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__ifloordiv__ is out-of-place. "
            "Use __floordiv__ instead."
        )
        return self.__floordiv__(other)

    def __imod__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__imod__ is out-of-place. Use __mod__ instead."
        )
        return self.__mod__(other)

    def __ipow__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__ipow__ is out-of-place. Use __pow__ instead."
        )
        return self.__pow__(other)

    def __ilshift__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__ilshift__ is out-of-place. "
            "Use __lshift__ instead."
        )
        return self.__lshift__(other)

    def __irshift__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__irshift__ is out-of-place. "
            "Use __rshift__ instead."
        )
        return self.__rshift__(other)

    def __iand__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__iand__ is out-of-place. Use __and__ instead."
        )
        return self.__and__(other)

    def __ixor__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__ixor__ is out-of-place. Use __xor__ instead."
        )
        return self.__xor__(other)

    def __ior__(self, other):
        warnings.warn(
            f"{type(self).__name__}.__ior__ is out-of-place. Use __or__ instead."
        )
        return self.__or__(other)

    @_reactive
    def __neg__(self):
        return super().__neg__()

    @_reactive
    def __pos__(self):
        return super().__pos__()

    @_reactive
    def __abs__(self):
        return super().__abs__()

    @_reactive
    def __invert__(self):
        return super().__invert__()

    @_reactive
    def __int__(self):
        return super().__int__()

    @_reactive
    def __long__(self):
        return super().__long__()

    @_reactive
    def __float__(self):
        return super().__float__()

    @_reactive
    def __complex__(self):
        return super().__complex__()

    @_reactive
    def __oct__(self):
        return super().__oct__()

    @_reactive
    def __hex__(self):
        return super().__hex__()

    # @reactive
    # def __index__(self):
    #     return super().__index__()

    # @reactive
    # def __len__(self):
    #     return super().__len__()

    @_reactive
    def __contains__(self, value):
        return super().__contains__(value)

    @_reactive
    def __getitem__(self, key):
        print("getitem", self, "key", key)
        return super().__getitem__(key)

    # TODO(Arjun): Check whether this needs to be reactive.
    # @reactive
    # def __setitem__(self, key, value):
    #     print("In setitem", self, "key", key, "value", value, "type", type(value))
    #     # Make a shallow copy of the value because this operation is not in-place.
    #     obj = self.__wrapped__.copy()
    #     obj[key] = value
    #     warnings.warn(f"{type(self).__name__}.__setitem__ is out-of-place.")
    #     return type(self)(obj, backend_only=self._self_backend_only)

    @_reactive
    def __delitem__(self, key):
        obj = self.__wrapped__.copy()
        del obj[key]
        warnings.warn(f"{type(self).__name__}.__delitem__ is out-of-place.")
        return type(self)(obj, backend_only=self._self_backend_only)

    @_reactive
    def __getslice__(self, i, j):
        return super().__getslice__(i, j)

    @_reactive
    def __setslice__(self, i, j, value):
        obj = self.__wrapped__.copy()
        obj[i:j] = value
        warnings.warn(f"{type(self).__name__}.__setslice__ is out-of-place.")
        return type(self)(obj, backend_only=self._self_backend_only)

    @_reactive
    def __delslice__(self, i, j):
        obj = self.__wrapped__.copy()
        del obj[i:j]
        warnings.warn(f"{type(self).__name__}.__delslice__ is out-of-place.")
        return type(self)(obj, backend_only=self._self_backend_only)

    # def __enter__(self):
    #     return self.__wrapped__.__enter__()

    # def __exit__(self, *args, **kwargs):
    #     return self.__wrapped__.__exit__(*args, **kwargs)

    # Overriding __next__ causes issues when using Stores with third-party libraries.
    # @reactive
    # def __next__(self):
    #     return next(self.__wrapped__)

    def __iter__(self):
        # FIXME: Find efficient way of mocking the iterator.
        # This is inefficient because it loads each element
        # of the wrapped object into memory.
        # This would be inefficient for iterables that should not
        # be loaded into memory (e.g. torch DataLoaders) or for long iterables
        # This is a temporary solution to make the Store iterable.
        _is_reactive = is_reactive()
        # return iter([Store(x) if _is_reactive else x for x in self.value])
        _iterator = iter(self.__wrapped__)
        return _IteratorStore(_iterator) if _is_reactive else _iterator


class _IteratorStore(Store):
    """A special store that wraps an iterator."""

    def __init__(self, wrapped: T, backend_only: bool = False):
        if not isinstance(wrapped, Iterator):
            raise ValueError("wrapped object must be an Iterator.")
        super().__init__(wrapped, backend_only)

    @_reactive
    def __next__(self):
        return next(self.__wrapped__)


def store_field(value: str) -> Field:
    """Utility for creating a pydantic field with a default factory that
    creates a Store object wrapping the given value.

    TODO (karan): Take a look at this again. I think we might be able to
    get rid of this in favor of just passing value.
    """
    return Field(default_factory=lambda: Store(value))


def make_store(value: Union[str, Storeable]) -> Store:
    """Make a Store.

    If value is a Store, return it. Otherwise, return a
    new Store that wraps value.

    Args:
        value (Union[str, Storeable]): The value to wrap.

    Returns:
        Store: The Store wrapping value.
    """
    return value if isinstance(value, Store) else Store(value)


def _unpack_stores_from_object(
    obj: Any, unpack_nested: bool = False
) -> Tuple[Any, List[Store]]:
    # TODO: cannot put return type hint here because it causes a circular import
    # for `Store` even with TYPE_CHECKING.
    """Unpack all the `Store` objects from a given object.

    By default, if a store is nested inside another store,
    it is not unpacked. If `unpack_nested` is True, then all stores
    are unpacked.

    Args:
        obj: The object to unpack stores from.
        unpack_nested: Whether to unpack nested stores.

    Returns:
        A tuple of the unpacked object and a list of the stores.
    """
    # Must use no_react here so that calling a method on a `Store`
    # e.g. `obj.items()` doesn't return new `Store` objects.
    # Note: cannot use `no_react` as a decorator on this fn because
    # it will automatically unpack the stores in the arguments.
    with no_react():
        if not unpack_nested and isinstance(obj, Store):
            return obj.value, [obj]

        _type = type(obj)
        if isinstance(obj, Store):
            _type = type(obj.value)

        if isinstance(obj, (list, tuple)):
            stores = []
            unpacked = []
            for x in obj:
                x, stores_i = _unpack_stores_from_object(x, unpack_nested)
                unpacked.append(x)
                stores.extend(stores_i)

            if isinstance(obj, Store):
                stores.append(obj)

            return _type(unpacked), stores
        elif isinstance(obj, dict):
            stores = []
            unpacked = {}
            for k, v in obj.items():
                k, stores_i_k = _unpack_stores_from_object(k, unpack_nested)
                v, stores_i_v = _unpack_stores_from_object(v, unpack_nested)
                unpacked[k] = v
                stores.extend(stores_i_k)
                stores.extend(stores_i_v)

            if isinstance(obj, Store):
                stores.append(obj)

            return _type(unpacked), stores
        elif isinstance(obj, Store):
            return obj.value, [obj]
        else:
            return obj, []
