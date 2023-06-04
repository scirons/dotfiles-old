from typing import Any, Union
import copy


class OverrideElement(object):

    obj: Any
    attr: str
    original: Any
    override: Any

    def __init__(self, obj: Any, attr: str, override: Any) -> None:
        self.obj = obj
        self.attr = attr
        self.original = copy.deepcopy(getattr(obj, attr))

        self.update(override)

    def update(self, override):
        self.override = override
        setattr(self.obj, self.attr, override)

    def restore(self) -> None:
        setattr(self.obj, self.attr, self.original)

    def __repr__(self) -> str:
        return f'[OVERRIDE]{self.obj}.{self.attr}: {self.original} -> {self.override}'


class OverrideHandler(object):

    data: list[OverrideElement]

    def __init__(self):
        self.data = []

    def override(self, obj: Any, attr: str, override: Any) -> OverrideElement:
        if e := self.get_element(obj, attr):
            e.update(override)
        else:
            e = OverrideElement(obj, attr, override)
            self.data.append(e)
        return e

    def store(self, obj: Any, attr: str) -> OverrideElement:
        if e := self.get_element(obj, attr):
            return e
        else:
            e = OverrideElement(obj, attr, getattr(obj, attr))
            self.data.append(e)
        return e

    def restore(self) -> None:
        for e in self.data:
            e.restore()

    def get_element(self, obj, attr) -> Union[None, OverrideElement]:
        try:
            return next(x for x in self.data if x.obj == obj and x.attr == attr)
        except StopIteration:
            return None


__all__ = ['OverrideHandler']
