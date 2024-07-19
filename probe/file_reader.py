from bacpypes.apdu import \
     AtomicReadFileRequest, \
     AtomicReadFileRequestAccessMethodChoice, \
     AtomicReadFileACK, \
     AtomicReadFileRequestAccessMethodChoiceRecordAccess, \
     AtomicReadFileRequestAccessMethodChoiceStreamAccess
from bacpypes.pdu import Address
from bacpypes.iocb import IOCB
from bacpypes.core import deferred
import BAC0
from BAC0.core.io.Read import *
from BAC0.scripts.Lite import Lite
import sqlite3
import sys
import os
import config
import traceback

class ReadFile(Lite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def read_file(self, address, fileId, start, size, access_method):
        is_record = (access_method == 'recordAccess')
        try:
            # build AtomicReadFile request
            iocb = IOCB(
                self.build_request(address, fileId, start, size, is_record)
            )
            iocb.set_timeout(500)
            # pass to the BACnet stack
            deferred(self.this_application.request_io, iocb)
            self._log.debug("{:<20} {!r}".format("iocb", iocb))
        
        except Exception as error:
            # construction error
            self._log.exception("exception: {!r}".format(error))
            return None
        
        iocb.wait()  # Wait for BACnet response
        
        if iocb.ioResponse:  # successful response
            apdu = iocb.ioResponse
        
            if not isinstance(apdu, AtomicReadFileACK):  # expecting an ACK
                self._log.warning("Not an ack, see debug for more infos.")
                self._log.debug("Not an ack. | APDU : {}".format(apdu))
                return None
            if is_record:
                return b''.join(apdu.accessMethod.recordAccess.fileRecordData)
            return apdu.accessMethod.streamAccess.fileData            
        
        if iocb.ioError:  # unsuccessful: error/reject/abort
            apdu = iocb.ioError
            reason = find_reason(apdu)
            print('Error reading file:', reason)
        return None
    
    def build_request(self, address, fileId, start, size, is_record):
        if is_record:
            method = AtomicReadFileRequestAccessMethodChoice(recordAccess=AtomicReadFileRequestAccessMethodChoiceRecordAccess(
                fileStartRecord=start,
                requestedRecordCount=size
            ))
        else:
            method = AtomicReadFileRequestAccessMethodChoice(streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                fileStartPosition=start,
                requestedOctetCount=size
            ))
        request = AtomicReadFileRequest(
            fileIdentifier=fileId,
            accessMethod=method,
        )
        
        request.pduDestination = Address(address)
        return request


def read_large_file(bacnet, address, file_id, out_file, batch_size):
    try:
        access_method = bacnet.read(f'{address} file {file_id} fileAccessMethod')
        if access_method == 'recordAccess':
            size = int(bacnet.read(f'{address} file {file_id} recordCount'))
        else:
            size = int(bacnet.read(f'{address} file {file_id} fileSize'))
        batch_range = range(0, size, batch_size)
        with open(out_file, 'wb') as fout:
            for batch_start in batch_range:
                print(f'Reading {batch_size} units starting from {batch_start} (of {size})', flush=True)
                chunk = bacnet.read_file(address, ('file', file_id), batch_start, batch_size, access_method)
                if chunk is None:
                    print('Read failed, see exception above', flush=True)
                    break
                fout.write(chunk)
                fout.flush()
    except Exception as e:
        print('Error while reading file', file_id, 'from', address)
        print(traceback.format_exc())
        print('End of error', flush=True)


def fetch_files(db, timestamp):
    # Get all present files as tuples (File object database ID, Device ID, File object BACnet ID, File access method)
    files_query = """
    SELECT DISTINCT o.Id, d.Address, o.BACnetId, pv.Value FROM Objects o
        JOIN Devices d ON o.Device = d.Id
        JOIN Properties p ON p.Object = o.Id AND p.Name = "fileAccessMethod"
        JOIN PropertyValues pv ON pv.Property = p.Id
        WHERE o.Type = "file"
    """
    cur = db.cursor()
    cur.execute(files_query)
    files = cur.fetchall()
    
    bacnet = ReadFile(ip=config.probe_ip)
    for obj_id, address, file_id, access_method in files:
        print(f'Processing file {file_id} at {address} using {access_method} method', flush=True)
        try:
            if access_method == 'recordAccess':
                batch_size = config.record_batch_size
                size = bacnet.read(f'{address} file {file_id} recordCount')
                if size >= config.large_record_file_size:
                    print(f'File too big ({size} records), skipping', flush=True)
                    continue
                batch_range = range(0, size, config.record_batch_size)
            else:
                batch_size = config.stream_batch_size
                size = bacnet.read(f'{address} file {file_id} fileSize')
                if size >= config.large_stream_file_size:
                    print(f'File too big ({size} bytes), skipping', flush=True)
                    continue
                batch_range = range(0, size, config.stream_batch_size)
            data = []
            for batch_start in batch_range:
                print(f'Reading {batch_size} units starting from {batch_start} (of {size})', flush=True)
                data.append(bacnet.read_file(address, ('file', file_id), batch_start, batch_size, access_method))
            cur.execute('INSERT INTO Files(Timestamp, File, Data) VALUES (?, ?, ?)', (timestamp, obj_id, b''.join(data)))
        except Exception as e:
            print('Error while reading file', file_id, 'from', address)
            print(traceback.format_exc())
            print('End of error', flush=True)
    db.commit()
    bacnet.disconnect()
