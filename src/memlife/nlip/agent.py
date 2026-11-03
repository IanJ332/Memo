# SPDX-License-Identifier: MIT
"""Decision adapter and separate persisted, untrusted project notes."""
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from .policy import ToolArguments
from .wire import WireError

@dataclass(frozen=True)
class Proposal:
    tool: str
    arguments: dict

class DecisionAdapter(Protocol):
    def propose(self,message,notes: tuple[str,...]) -> Proposal: ...

def request_proposal(message):
    candidates=[p.content for p in message.parts if p.kind=="structured" and p.subtype=="json"]
    if len(candidates)!=1 or not isinstance(candidates[0],dict) or set(candidates[0])!={"tool","arguments"}:
        raise WireError("ONE_STRUCTURED_TOOL_REQUEST_REQUIRED")
    value=candidates[0]
    if not isinstance(value["tool"],str) or len(value["tool"])>64: raise WireError("INVALID_TOOL_REQUEST")
    ToolArguments.parse(value["arguments"])
    return Proposal(value["tool"],dict(value["arguments"]))

class DeterministicAdapter:
    """Deliberately susceptible engineering fixture, never labeled an LLM."""
    def propose(self,message,notes):
        from .admission import TypedContext
        if type(notes) is not TypedContext: raise TypeError('TYPED_CONTEXT_REQUIRED')
        proposal=request_proposal(message)
        recipient=proposal.arguments["recipient"]
        for item in notes.items:
            note=item.content.decode("utf-8", "strict")
            matches=re.findall(r"Suggested send_report recipient: ([A-Za-z0-9_.@+-]+)",note)
            if matches: recipient=matches[-1]
        return Proposal(proposal.tool,{**proposal.arguments,"recipient":recipient})

class NoteStore:
    def __init__(self,path):
        self.path=Path(path)
        if not self.path.exists():
            fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
            with sqlite3.connect(self.path) as db:
                db.execute("CREATE TABLE notes(issuer TEXT,subject TEXT,project TEXT,content TEXT)")
    def append(self,principal,project,content):
        if not isinstance(content,str) or len(content.encode())>8192: raise ValueError("NOTE_LIMIT")
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            count=db.execute("SELECT COUNT(*) FROM notes WHERE issuer=? AND subject=? AND project=?",(principal.issuer,principal.subject,project)).fetchone()[0]
            if count>=16: raise ValueError("NOTE_CAPACITY")
            db.execute("INSERT INTO notes VALUES(?,?,?,?)",(principal.issuer,principal.subject,project,content))
    def read(self,principal,project):
        with sqlite3.connect(self.path) as db:
            return tuple(r[0] for r in db.execute("SELECT content FROM notes WHERE issuer=? AND subject=? AND project=? ORDER BY rowid",(principal.issuer,principal.subject,project)))
