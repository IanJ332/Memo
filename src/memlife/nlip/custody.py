# SPDX-License-Identifier: MIT
"""Offline direct-record custody. All writers and handoffs share an OS file lock.

This API split is an application capability boundary, not protection from a
same-UID process able to open the database, lock file, or construct an admin.
"""
import contextlib
import fcntl
import hashlib
import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

SCHEMA = '''
CREATE TABLE metadata(store_id TEXT NOT NULL, generation INTEGER NOT NULL);
CREATE TABLE notes(seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, issuer TEXT NOT NULL,
 subject TEXT NOT NULL, project TEXT NOT NULL, content BLOB NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE routes(id TEXT PRIMARY KEY, issuer TEXT NOT NULL, subject TEXT NOT NULL,
 project TEXT NOT NULL, use TEXT NOT NULL CHECK(use IN ('reference','operational')));
CREATE TABLE reservations(id TEXT PRIMARY KEY, issuer TEXT NOT NULL, subject TEXT NOT NULL,
 project TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE sources(event TEXT PRIMARY KEY, source TEXT NOT NULL, body BLOB NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE confirmations(id TEXT PRIMARY KEY, record_id TEXT NOT NULL, event TEXT NOT NULL,
 revision INTEGER NOT NULL, digest TEXT NOT NULL);
CREATE TABLE associations(seq INTEGER PRIMARY KEY, record_id TEXT NOT NULL, issuer TEXT NOT NULL,
 subject TEXT NOT NULL, project TEXT NOT NULL, event TEXT NOT NULL, status TEXT NOT NULL,
 confirmation TEXT NOT NULL, host_revision INTEGER NOT NULL);
CREATE TABLE events(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, details TEXT NOT NULL);
CREATE TABLE audit(seq INTEGER PRIMARY KEY, payload BLOB NOT NULL);
'''

def digest(data): return hashlib.sha256(data).hexdigest()
def scope(principal, project): return (principal.issuer, principal.subject, project)
def checked_bytes(content):
    if not isinstance(content, str): raise ValueError('NOTE_LIMIT')
    b = content.encode('utf-8', 'strict')
    if len(b) > 8192: raise ValueError('NOTE_LIMIT')
    return b

@dataclass(frozen=True)
class Record:
    record_id: str
    issuer: str
    subject: str
    project: str
    content: bytes
    revision: int
    use: str

class Database:
    def __init__(self, path, store_id):
        self.path = Path(path); self.store_id = store_id
        self.lock_path = Path(str(path) + '.lock')
    @classmethod
    def create(cls, path, store_id):
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
        obj = cls(path, store_id)
        try:
            with sqlite3.connect(path) as db:
                db.executescript(SCHEMA); db.execute('INSERT INTO metadata VALUES(?,0)',(store_id,))
            fd = os.open(obj.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
        except BaseException:
            path.unlink(missing_ok=True); raise
        return obj
    @contextlib.contextmanager
    def lease(self):
        with open(self.lock_path, 'rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(lock, fcntl.LOCK_UN)
    @contextlib.contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            db.execute('BEGIN IMMEDIATE')
            meta=db.execute('SELECT store_id,generation FROM metadata').fetchall()
            if len(meta)!=1 or meta[0][0]!=self.store_id or type(meta[0][1]) is not int: raise ValueError('INVALID_STORE_IDENTITY')
            yield db; db.commit()
        except BaseException:
            db.rollback(); raise
        finally: db.close()
    def records(self, db, principal, project):
        rows = db.execute('''SELECT n.id,n.issuer,n.subject,n.project,n.content,n.revision,r.use
          FROM notes n LEFT JOIN routes r ON r.id=n.id AND r.issuer=n.issuer
          AND r.subject=n.subject AND r.project=n.project
          WHERE n.issuer=? AND n.subject=? AND n.project=? ORDER BY n.seq''', scope(principal, project)).fetchall()
        if any(row[6] not in ('reference','operational') for row in rows): raise ValueError('INVALID_ROUTE')
        return tuple(Record(*r) for r in rows)

class Notes:
    """Ordinary writer: cannot choose identity, route, or evidence."""
    def __init__(self, database): self.database = database
    def append(self, principal, project, content):
        data = checked_bytes(content); record_id = uuid.uuid4().hex
        with self.database.lease(), self.database.transaction() as db:
            self._insert(db, principal, project, data, record_id, 'reference')
        return record_id
    @staticmethod
    def _insert(db, principal, project, data, record_id, use):
        s = scope(principal, project)
        if db.execute('SELECT COUNT(*) FROM notes WHERE issuer=? AND subject=? AND project=?', s).fetchone()[0] >= 16: raise ValueError('NOTE_CAPACITY')
        db.execute('INSERT INTO notes(id,issuer,subject,project,content,revision) VALUES(?,?,?,?,?,1)', (record_id,*s,data))
        db.execute('INSERT INTO routes VALUES(?,?,?,?,?)', (record_id,*s,use))
    def read(self, principal, project):
        with self.database.lease(), self.database.transaction() as db:
            return self.database.records(db, principal, project)

class HostAdmin:
    """Bootstrap-only capability; never supplied to ingestion or adapters."""
    def __init__(self, database): self.database = database
    def reserve(self, principal, project):
        rid = uuid.uuid4().hex
        with self.database.lease(), self.database.transaction() as db:
            db.execute('INSERT INTO reservations(id,issuer,subject,project) VALUES(?,?,?,?)',(rid,*scope(principal,project)))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('RESERVE',rid))
        return rid
    def persist_reserved(self, principal, project, rid, content):
        data = checked_bytes(content)
        with self.database.lease(), self.database.transaction() as db:
            row=db.execute('SELECT issuer,subject,project,used FROM reservations WHERE id=?',(rid,)).fetchone()
            if row != (*scope(principal,project),0): raise ValueError('INVALID_RESERVATION')
            Notes._insert(db,principal,project,data,rid,'operational')
            db.execute('UPDATE reservations SET used=1 WHERE id=?',(rid,))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('PERSIST',rid))
    def approve_source(self, source, event, body, revision):
        data=checked_bytes(body)
        if type(revision) is not int or revision < 1: raise ValueError('INVALID_REVISION')
        with self.database.lease(), self.database.transaction() as db:
            db.execute('INSERT INTO sources VALUES(?,?,?,?)',(event,source,data,revision))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('APPROVE',event))
    def confirm(self, principal, project, rid, event):
        cid=uuid.uuid4().hex
        with self.database.lease(), self.database.transaction() as db:
            note=db.execute('SELECT content,revision FROM notes WHERE id=? AND issuer=? AND subject=? AND project=?',(rid,*scope(principal,project))).fetchone()
            source=db.execute('SELECT body FROM sources WHERE event=?',(event,)).fetchone()
            if not note or not source or note[0] != source[0]: raise ValueError('CONFIRMATION_FAILED')
            db.execute('INSERT INTO confirmations VALUES(?,?,?,?,?)',(cid,rid,event,note[1],digest(note[0])))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('CONFIRM',cid))
        return cid
    def publish(self, principal, project, rid, event, confirmation):
        with self.database.lease(), self.database.transaction() as db:
            row=db.execute('''SELECT n.content,n.revision,c.digest,c.revision,s.body,s.revision,r.use
                FROM notes n JOIN confirmations c ON c.record_id=n.id AND c.event=? AND c.id=?
                JOIN sources s ON s.event=c.event JOIN routes r ON r.id=n.id
                WHERE n.id=? AND n.issuer=? AND n.subject=? AND n.project=?''',(event,confirmation,rid,*scope(principal,project))).fetchone()
            if not row or row[6]!='operational' or row[0]!=row[4] or digest(row[0])!=row[2] or row[1]!=row[3]: raise ValueError('PUBLICATION_NOT_CONFIRMED')
            old=db.execute('SELECT MAX(host_revision) FROM associations WHERE record_id=? AND issuer=? AND subject=? AND project=?',(rid,*scope(principal,project))).fetchone()[0]
            if old is not None and row[5]<=old: raise ValueError('STALE_HOST_REVISION')
            db.execute('UPDATE associations SET status=? WHERE record_id=? AND issuer=? AND subject=? AND project=? AND status=?',('SUPERSEDED',rid,*scope(principal,project),'CURRENT'))
            db.execute('INSERT INTO associations(record_id,issuer,subject,project,event,status,confirmation,host_revision) VALUES(?,?,?,?,?,?,?,?)',(rid,*scope(principal,project),event,'CURRENT',confirmation,row[5]))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('PUBLISH',confirmation))
            db.execute('UPDATE metadata SET generation=generation+1')
    def supersede_and_publish(self, principal, project, old_id, new_id, event, confirmation):
        """Publish a replacement and its tombstone in one indivisible head."""
        with self.database.lease(), self.database.transaction() as db:
            row=db.execute('''SELECT n.content,n.revision,c.digest,c.revision,s.body,s.revision,r.use
                FROM notes n JOIN confirmations c ON c.record_id=n.id AND c.event=? AND c.id=?
                JOIN sources s ON s.event=c.event JOIN routes r ON r.id=n.id
                WHERE n.id=? AND n.issuer=? AND n.subject=? AND n.project=?''',(event,confirmation,new_id,*scope(principal,project))).fetchone()
            if not row or row[6]!='operational' or row[0]!=row[4] or digest(row[0])!=row[2] or row[1]!=row[3]: raise ValueError('PUBLICATION_NOT_CONFIRMED')
            old=db.execute('SELECT MAX(host_revision) FROM associations WHERE record_id=? AND issuer=? AND subject=? AND project=?',(new_id,*scope(principal,project))).fetchone()[0]
            if old is not None and row[5]<=old: raise ValueError('STALE_HOST_REVISION')
            cur=db.execute('UPDATE associations SET status=?,host_revision=host_revision+1 WHERE record_id=? AND issuer=? AND subject=? AND project=? AND status=?',('SUPERSEDED',old_id,*scope(principal,project),'CURRENT'))
            if cur.rowcount!=1: raise ValueError('ASSOCIATION_NOT_CURRENT')
            db.execute('INSERT INTO associations(record_id,issuer,subject,project,event,status,confirmation,host_revision) VALUES(?,?,?,?,?,?,?,?)',(new_id,*scope(principal,project),event,'CURRENT',confirmation,row[5]))
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',('SUPERSEDE_AND_PUBLISH',confirmation))
            db.execute('UPDATE metadata SET generation=generation+1')
    def deactivate(self, principal, project, rid, status):
        if status not in ('REVOKED','SUPERSEDED'): raise ValueError('INVALID_STATUS')
        with self.database.lease(), self.database.transaction() as db:
            cur=db.execute('UPDATE associations SET status=?,host_revision=host_revision+1 WHERE record_id=? AND issuer=? AND subject=? AND project=? AND status=?',(status,rid,*scope(principal,project),'CURRENT'))
            if cur.rowcount != 1: raise ValueError('ASSOCIATION_NOT_CURRENT')
            db.execute('INSERT INTO events(kind,details) VALUES(?,?)',(status,rid))
            db.execute('UPDATE metadata SET generation=generation+1')
    def replace_for_test(self, principal, project, rid, content):
        """Offline lifecycle fixture only; no user-facing update API."""
        data=checked_bytes(content)
        with self.database.lease(), self.database.transaction() as db:
            cur=db.execute('UPDATE notes SET content=?,revision=revision+1 WHERE id=? AND issuer=? AND subject=? AND project=?',(data,rid,*scope(principal,project)))
            if cur.rowcount!=1: raise ValueError('NOTE_NOT_FOUND')

def verify_record(db, record):
    """Return the direct-record frozen classification and reason."""
    if record.use == 'reference': return 'REFERENCE', 'ORDINARY_CONTEXT_RETAINED'
    rows=db.execute('''SELECT a.issuer,a.subject,a.project,a.status,a.event,a.host_revision,
        s.body,s.revision,c.record_id,c.event,c.revision,c.digest
        FROM associations a LEFT JOIN sources s ON s.event=a.event
        LEFT JOIN confirmations c ON c.id=a.confirmation
        WHERE a.record_id=? ORDER BY a.seq''',(record.record_id,)).fetchall()
    exact=[r for r in rows if r[:3] == (record.issuer,record.subject,record.project)]
    if not exact: return ('UNKNOWN','HOST_SCOPE_MISMATCH' if rows else 'HOST_ASSOCIATION_MISSING')
    active=[r for r in exact if r[3]=='CURRENT']
    if len(active)>1: return 'UNKNOWN','HOST_ASSOCIATION_CONFLICT'
    if not active:
        last=exact[-1]
        if last[3] in ('REVOKED','SUPERSEDED'): return 'INACTIVE','HOST_'+last[3]
        return 'UNKNOWN','HOST_ASSOCIATION_MISSING'
    r=active[0]
    if r[6] is None or r[7]!=r[5] or r[8]!=record.record_id or r[9]!=r[4]: return 'UNKNOWN','HOST_ASSOCIATION_MISSING'
    if r[6]!=record.content or r[10]!=record.revision or r[11]!=digest(record.content): return 'UNKNOWN','HOST_CONTENT_MISMATCH'
    return 'CURRENT','EXACT_CURRENT_HOST_BINDING'
