# SPDX-License-Identifier: MIT
"""Safe HTTPCore stage telemetry; never retains callback payloads or headers."""
import time
import httpx


class DuplicateTransportSend(RuntimeError): pass


class TransportDiagnostics:
    STAGES = {
        'connection.connect_tcp': 'CONNECT_TCP_OR_DNS',
        'connection.start_tls': 'TLS_HANDSHAKE',
        'http11.send_request_headers': 'SEND_REQUEST_HEADERS',
        'http11.send_request_body': 'SEND_REQUEST_BODY',
        'http11.receive_response_headers': 'WAIT_RESPONSE_HEADERS',
        'http11.receive_response_body': 'READ_RESPONSE_BODY',
        'http11.response_closed': 'RESPONSE_CLOSED',
    }

    def __init__(self, clock=time.perf_counter_ns):
        self.clock=clock;self.start=clock();self.events=[];self.stage='BEFORE_TRANSPORT'
        self.failed_stage=None;self.headers_started=0;self.first_chunk_ns=None
        self.body_bytes=0;self.chunks=0;self.truncated=False

    def trace(self, name, info):
        prefix,_,suffix=name.rpartition('.')
        if prefix not in self.STAGES or suffix not in {'started','complete','failed'}:return
        stage=self.STAGES[prefix]
        if stage!='RESPONSE_CLOSED':self.stage=stage
        if suffix=='failed' and stage!='RESPONSE_CLOSED':self.failed_stage=stage
        event={'event':name,'elapsed_ns':self.clock()-self.start}
        # info can contain credentials, SSL objects and arbitrary exception text.
        # Do not inspect or serialize it, even for failed events.
        if len(self.events)<256:self.events.append(event)
        else:self.truncated=True
        if name=='http11.send_request_headers.started':
            self.headers_started+=1
            if self.headers_started>1:raise DuplicateTransportSend('DUPLICATE_TRANSPORT_SEND')

    def chunk(self, size):
        if self.first_chunk_ns is None:self.first_chunk_ns=self.clock()-self.start
        self.body_bytes+=size;self.chunks+=1;self.stage='READ_RESPONSE_BODY'

    def headers(self):self.stage='RESPONSE_HEADERS_RECEIVED'

    def snapshot(self, error=None, *, headers_received=False):
        stage=self.failed_stage or self.stage
        if isinstance(error,httpx.ConnectTimeout) and stage=='BEFORE_TRANSPORT':stage='CONNECT_OR_TLS'
        elif isinstance(error,httpx.PoolTimeout):stage='CONNECTION_POOL'
        elif isinstance(error,httpx.WriteTimeout) and stage=='BEFORE_TRANSPORT':stage='REQUEST_WRITE'
        elif isinstance(error,httpx.ReadTimeout) and self.failed_stage is None:
            stage='READ_RESPONSE_BODY' if headers_received else 'WAIT_RESPONSE_HEADERS'
        if isinstance(error,httpx.TimeoutException):category=type(error).__name__
        elif isinstance(error,(KeyboardInterrupt,SystemExit)):category='LOCAL_INTERRUPTION'
        elif isinstance(error,DuplicateTransportSend):category='DUPLICATE_TRANSPORT_SEND'
        else:category=None
        return {'stage':stage,'timeout_or_interruption_category':category,
            'stage_basis':'HTTPCORE_TRACE' if self.events else 'EXCEPTION_AND_RESPONSE_STATE_ONLY',
            'trace_events':list(self.events),'trace_truncated':self.truncated,
            'request_header_send_starts':self.headers_started,
            'first_observed_response_chunk_ns':self.first_chunk_ns,
            'response_body_bytes_received':self.body_bytes,'response_chunks_received':self.chunks,
            'backend_cancellation':'NOT_CONFIRMED','backend_completion':'UNKNOWN'}
