# SPDX-License-Identifier: MIT
"""Trusted administrative SQLite policy; no NLIP/model mutation route."""
from __future__ import annotations
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

class PolicyError(RuntimeError): pass

def identifier(value, limit):
    return isinstance(value,str) and 0<len(value)<=limit and re.fullmatch(r"[A-Za-z0-9_.@+-]+",value) is not None

@dataclass(frozen=True)
class ToolArguments:
    project_id: str
    recipient: str
    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict) or set(value)!={"project_id","recipient"}: raise ValueError("MALFORMED_ARGUMENTS")
        if not identifier(value["project_id"],64) or not identifier(value["recipient"],128): raise ValueError("MALFORMED_ARGUMENTS")
        return cls(**value)
    def as_dict(self): return {"project_id":self.project_id,"recipient":self.recipient}

@dataclass(frozen=True)
class PolicySnapshot:
    revision: int
    known_project: bool
    principal_allowed: bool
    recipients: frozenset[str]
    scope: tuple[str,str,str]
    def current(self,principal,project):
        if self.scope!=(principal.issuer,principal.subject,project): raise PolicyError("SNAPSHOT_SCOPE_MISMATCH")
        return self

SCHEMA = """CREATE TABLE revision(value INTEGER NOT NULL CHECK(value>=0));
INSERT INTO revision VALUES(0);
CREATE TABLE projects(project TEXT PRIMARY KEY);
CREATE TABLE grants(issuer TEXT,subject TEXT,project TEXT,allowed INTEGER NOT NULL CHECK(allowed IN(0,1)),PRIMARY KEY(issuer,subject,project));
CREATE TABLE recipients(project TEXT,recipient TEXT,PRIMARY KEY(project,recipient));
CREATE TABLE deliveries(invocation TEXT PRIMARY KEY,project TEXT,recipient TEXT,revision INTEGER,synthetic INTEGER NOT NULL CHECK(synthetic=1));
CREATE TABLE audit(invocation TEXT PRIMARY KEY,action TEXT,reason TEXT,revision INTEGER,delivered INTEGER);
"""

class PolicyAdmin:
    """Host-side administrative capability, never passed to the decision adapter."""
    def __init__(self,path): self.path=Path(path)
    @classmethod
    def create(cls,path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        with sqlite3.connect(path) as db: db.executescript(SCHEMA)
        return cls(path)
    def set_policy(self,principal,project,recipients,allowed=True):
        if not identifier(project,64) or type(allowed) is not bool: raise ValueError("INVALID_ADMIN_POLICY")
        recipients=tuple(recipients)
        if len(set(recipients))!=len(recipients) or any(not identifier(x,128) for x in recipients): raise ValueError("INVALID_ADMIN_POLICY")
        with sqlite3.connect(self.path,timeout=2) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO projects VALUES(?)",(project,))
            db.execute("INSERT OR REPLACE INTO grants VALUES(?,?,?,?)",(principal.issuer,principal.subject,project,int(allowed)))
            db.execute("DELETE FROM recipients WHERE project=?",(project,))
            db.executemany("INSERT INTO recipients VALUES(?,?)",[(project,r) for r in recipients])
            db.execute("UPDATE revision SET value=value+1")
            return db.execute("SELECT value FROM revision").fetchone()[0]
    def revoke_recipient(self,project,recipient):
        with sqlite3.connect(self.path,timeout=2) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM recipients WHERE project=? AND recipient=?",(project,recipient))
            db.execute("UPDATE revision SET value=value+1")
            return db.execute("SELECT value FROM revision").fetchone()[0]

class PolicyStore:
    """Read-only policy API; the dispatcher alone uses its private commit seam."""
    def __init__(self,path): self.path=Path(path)
    def _connection(self,write=False):
        mode="rw" if write else "ro"
        return sqlite3.connect(self.path.resolve().as_uri()+"?mode="+mode,uri=True,timeout=2)
    def snapshot(self,db,principal,project):
        revisions=db.execute("SELECT value FROM revision").fetchall()
        if len(revisions)!=1 or type(revisions[0][0]) is not int or revisions[0][0]<0: raise PolicyError("INCONSISTENT_REVISION")
        known=db.execute("SELECT 1 FROM projects WHERE project=?",(project,)).fetchone() is not None
        grant=db.execute("SELECT allowed FROM grants WHERE issuer=? AND subject=? AND project=?",(principal.issuer,principal.subject,project)).fetchone()
        if grant is not None and grant[0] not in (0,1): raise PolicyError("INCONSISTENT_GRANT")
        recipients=frozenset(r[0] for r in db.execute("SELECT recipient FROM recipients WHERE project=?",(project,)))
        if any(not identifier(r,128) for r in recipients): raise PolicyError("INCONSISTENT_RECIPIENT")
        return PolicySnapshot(revisions[0][0],known,grant is not None and grant[0]==1,recipients,(principal.issuer,principal.subject,project))
    def current(self,principal,project):
        with self._connection() as db:
            db.execute("BEGIN")
            return self.snapshot(db,principal,project)
    @contextmanager
    def _dispatch_transaction(self):
        db=self._connection(True)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback();raise
        finally: db.close()
    def deliveries(self):
        with self._connection() as db:
            return [dict(zip(("invocation","project_id","recipient","policy_revision","synthetic"),r)) for r in db.execute("SELECT * FROM deliveries ORDER BY rowid")]
    def audits(self):
        with self._connection() as db:
            return [dict(zip(("invocation","action","reason","policy_revision","delivered"),r)) for r in db.execute("SELECT * FROM audit ORDER BY rowid")]
