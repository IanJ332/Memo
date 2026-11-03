# SPDX-License-Identifier: MIT
"""ECMA-430 envelope processing; application content and labels stay untrusted."""
from __future__ import annotations
import copy
import json
import math
import re
from dataclasses import dataclass

MAX_BODY = 131072
MAX_PARTS = 32
FORMATS = {"text", "structured", "token", "binary", "location", "generic"}

class WireError(ValueError):
    pass

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise WireError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result

def strict_json(raw):
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed): raise WireError("NONFINITE_JSON")
        return parsed
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_float=finite_float,
                          parse_constant=lambda x: (_ for _ in ()).throw(WireError("NONFINITE_JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise WireError("INVALID_JSON") from exc

def depth(value, level=0):
    if level > 32: raise WireError("EXCESSIVE_DEPTH")
    if isinstance(value, dict):
        for child in value.values(): depth(child, level+1)
    elif isinstance(value, list):
        for child in value: depth(child, level+1)

def fields(value, allowed):
    if not isinstance(value, dict): raise WireError("EXPECTED_OBJECT")
    result = {}
    for key, item in value.items():
        normalized = key.casefold()
        if normalized not in allowed: raise WireError("UNKNOWN_PROTOCOL_FIELD")
        if normalized in result: raise WireError("CONFLICTING_PROTOCOL_FIELDS")
        result[normalized] = item
    return result

@dataclass(frozen=True)
class Part:
    format: str
    subformat: str
    content: object
    label: str | None = None
    @property
    def kind(self): return self.format.casefold()
    @property
    def subtype(self): return self.subformat.casefold()
    def as_dict(self):
        result = {"Format":self.format,"Subformat":self.subformat,"Content":copy.deepcopy(self.content)}
        if self.label is not None: result["Label"] = self.label
        return result

def part(value, first=False):
    allowed = {"format","subformat","content"} | ({"messagetype","submessages","control"} if first else {"label"})
    d = fields(value, allowed)
    if not {"format","subformat","content"} <= d.keys(): raise WireError("MISSING_REQUIRED_FIELD")
    if not isinstance(d["format"],str) or d["format"].casefold() not in FORMATS: raise WireError("INVALID_FORMAT")
    if not isinstance(d["subformat"],str) or not d["subformat"] or len(d["subformat"])>128: raise WireError("INVALID_SUBFORMAT")
    if "label" in d and (not isinstance(d["label"],str) or len(d["label"])>128): raise WireError("INVALID_LABEL")
    if d["format"].casefold()=="text" and not isinstance(d["content"],str): raise WireError("INVALID_TEXT")
    # ECMA-430 5.3 Table 1: binary subformat carries a category and an
    # encoding, optionally prefixed by '.'. The prose omits video but the
    # same table explicitly exemplifies video/.mp3; accept that category.
    if d["format"].casefold()=="binary" and not re.fullmatch(
        r"(?:audio|image|sensor|generic|video)/\.?[^/\s.][^/\s]*",d["subformat"],re.IGNORECASE
    ): raise WireError("INVALID_BINARY_SUBFORMAT")
    if d["format"].casefold()=="location":
        if d["subformat"].casefold() not in {"text","gps"}: raise WireError("INVALID_LOCATION_SUBFORMAT")
        if d["subformat"].casefold()=="text" and not isinstance(d["content"],str): raise WireError("INVALID_LOCATION_TEXT")
    return Part(d["format"],d["subformat"],copy.deepcopy(d["content"]),d.get("label")),d

@dataclass(frozen=True)
class Message:
    first: Part
    submessages: tuple[Part,...]
    message_type: str | None = None
    control_compatibility: bool | None = None
    @property
    def parts(self): return (self.first,)+self.submessages
    @property
    def is_control(self): return (self.message_type or "").casefold()=="control" or self.control_compatibility is True
    def as_dict(self):
        result=self.first.as_dict()
        if self.message_type is not None: result["MessageType"]=self.message_type
        if self.control_compatibility is not None: result["control"]=self.control_compatibility
        if self.submessages: result["Submessages"]=[p.as_dict() for p in self.submessages]
        return result
    def response(self, content, text=False):
        # Echo all received token values, including a token in the first part.
        tokens=tuple(p for p in self.parts if p.kind=="token")
        return Message(Part("text" if text else "structured","English" if text else "json",content),
                       tokens,"control" if self.is_control else None,self.control_compatibility)

def parse_message(raw: bytes):
    if not isinstance(raw,bytes) or len(raw)>MAX_BODY: raise WireError("BODY_LIMIT")
    value=strict_json(raw); depth(value)
    first,d=part(value,True)
    mt=d.get("messagetype")
    if "messagetype" in d and not isinstance(mt,str): raise WireError("INVALID_MESSAGE_TYPE")
    control=d.get("control")
    if "control" in d and type(control) is not bool: raise WireError("INVALID_CONTROL")
    if mt is not None and control is not None and ((mt.casefold()=="control") != control): raise WireError("CONFLICTING_CONTROL")
    sub=d.get("submessages",[])
    if not isinstance(sub,list) or ("submessages" in d and not sub) or len(sub)>MAX_PARTS: raise WireError("INVALID_SUBMESSAGES")
    return Message(first,tuple(part(x)[0] for x in sub),mt,control)

def encode(message):
    # JSON permits escaped UTF-16 code units. ASCII escapes also preserve
    # lone surrogates in opaque tokens without failing UTF-8 serialization.
    return json.dumps(message.as_dict(),ensure_ascii=True,separators=(",",":"),allow_nan=False).encode()
