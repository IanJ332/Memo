import sqlite3
import threading
import time
import pytest
from memlife.nlip.auth import Principal
from memlife.nlip.custody import Database, Notes, HostAdmin, verify_record

@pytest.fixture
def fixture(tmp_path):
    database=Database.create(tmp_path/'notes.db','store'); p=Principal('issuer','subject')
    return database, Notes(database), HostAdmin(database), p

def prepared(fixture):
    d,n,h,p=fixture; rid=h.reserve(p,'project'); h.persist_reserved(p,'project',rid,'café\r\n')
    h.approve_source('source','event','café\r\n',1); return d,n,h,p,rid

def decision(d,n,p):
    with d.lease(), d.transaction() as db:
        return [verify_record(db,r) for r in d.records(db,p,'project')]

def test_valid_publication(fixture):
    d,n,h,p,r=prepared(fixture); c=h.confirm(p,'project',r,'event');h.publish(p,'project',r,'event',c)
    assert decision(d,n,p)==[('CURRENT','EXACT_CURRENT_HOST_BINDING')]
    assert n.read(p,'project')[0].content=='café\r\n'.encode()

def test_publication_before_confirmation(fixture):
    d,n,h,p,r=prepared(fixture)
    with pytest.raises(ValueError,match='PUBLICATION_NOT_CONFIRMED'): h.publish(p,'project',r,'event','missing')
    assert decision(d,n,p)==[('UNKNOWN','HOST_ASSOCIATION_MISSING')]

def test_persistence_failure_and_recovery(fixture):
    d,n,h,p=fixture; r=h.reserve(p,'project')
    with pytest.raises(ValueError,match='NOTE_LIMIT'): h.persist_reserved(p,'project',r,'x'*8193)
    h.persist_reserved(p,'project',r,'ok'); assert len(n.read(p,'project'))==1

def test_scope(fixture):
    d,n,h,p,r=prepared(fixture); other=Principal('issuer','other')
    with pytest.raises(ValueError,match='CONFIRMATION_FAILED'): h.confirm(other,'project',r,'event')
    assert n.read(other,'project')==() and n.read(p,'other')==()

def test_changed_bytes_and_refresh(fixture):
    d,n,h,p,r=prepared(fixture);c=h.confirm(p,'project',r,'event');h.publish(p,'project',r,'event',c)
    h.replace_for_test(p,'project',r,'new'); assert decision(d,n,p)[0][1]=='HOST_CONTENT_MISMATCH'
    h.approve_source('source','event2','new',2); c=h.confirm(p,'project',r,'event2'); h.publish(p,'project',r,'event2',c)
    assert decision(d,n,p)[0][0]=='CURRENT'

def test_stale_confirmation(fixture):
    d,n,h,p,r=prepared(fixture); c=h.confirm(p,'project',r,'event');h.replace_for_test(p,'project',r,'new')
    with pytest.raises(ValueError,match='PUBLICATION_NOT_CONFIRMED'): h.publish(p,'project',r,'event',c)

@pytest.mark.parametrize('status',['REVOKED','SUPERSEDED'])
def test_inactive(fixture,status):
    d,n,h,p,r=prepared(fixture);c=h.confirm(p,'project',r,'event');h.publish(p,'project',r,'event',c);h.deactivate(p,'project',r,status)
    assert decision(d,n,p)==[('INACTIVE','HOST_'+status)]

def test_conflict(fixture):
    d,n,h,p,r=prepared(fixture);c=h.confirm(p,'project',r,'event');h.publish(p,'project',r,'event',c)
    with d.lease(),d.transaction() as db: db.execute('INSERT INTO associations(record_id,issuer,subject,project,event,status,confirmation,host_revision) SELECT record_id,issuer,subject,project,event,status,confirmation,host_revision FROM associations')
    assert decision(d,n,p)[0]==('UNKNOWN','HOST_ASSOCIATION_CONFLICT')

def test_ordinary_cannot_choose_authority(fixture):
    d,n,h,p=fixture; r=n.append(p,'project','claimed authority')
    assert decision(d,n,p)==[('REFERENCE','ORDINARY_CONTEXT_RETAINED')]
    with pytest.raises(TypeError): n.append(p,'project','x',r)

def test_concurrent_publisher_waits_for_reader(fixture):
    d,n,h,p,r=prepared(fixture);c=h.confirm(p,'project',r,'event'); h.publish(p,'project',r,'event',c)
    started=threading.Event(); done=threading.Event()
    def publisher(): started.set(); h.deactivate(p,'project',r,'REVOKED');done.set()
    with d.lease():
        t=threading.Thread(target=publisher);t.start();assert started.wait(1);assert not done.wait(.05)
    t.join(2);assert done.is_set();assert decision(d,n,p)[0][1]=='HOST_REVOKED'

def test_transaction_rollback(fixture):
    d,n,h,p=fixture
    with pytest.raises(RuntimeError):
        with d.lease(), d.transaction() as db:
            db.execute("INSERT INTO events(kind,details) VALUES('test','x')");raise RuntimeError('fail')
    with d.lease(),d.transaction() as db: assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0
    n.append(p,'project','recovered');assert len(n.read(p,'project'))==1

def test_atomic_supersession_rollback_and_generation(fixture):
    d,n,h,p,old=prepared(fixture); c=h.confirm(p,'project',old,'event');h.publish(p,'project',old,'event',c)
    new=h.reserve(p,'project');h.persist_reserved(p,'project',new,'new');h.approve_source('source','new-event','new',2)
    with pytest.raises(ValueError,match='PUBLICATION_NOT_CONFIRMED'): h.supersede_and_publish(p,'project',old,new,'new-event','invalid')
    assert decision(d,n,p)[0][0]=='CURRENT'
    with d.lease(),d.transaction() as db: assert db.execute('SELECT generation FROM metadata').fetchone()[0]==1
    confirmation=h.confirm(p,'project',new,'new-event');h.supersede_and_publish(p,'project',old,new,'new-event',confirmation)
    assert [x[0] for x in decision(d,n,p)]==['INACTIVE','CURRENT']
    with d.lease(),d.transaction() as db: assert db.execute('SELECT generation FROM metadata').fetchone()[0]==2
