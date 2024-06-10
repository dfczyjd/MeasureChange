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

class ReadFile(Lite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def read_file(self, address, fileId, size, access_method):
        is_record = (access_method == 'recordAccess')
        try:
            # build AtomicReadFile request
            iocb = IOCB(
                self.build_request(address, fileId, size, is_record)
            )
            iocb.set_timeout(5)
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
    
    def build_request(self, address, fileId, size, is_record):
        if is_record:
            method = AtomicReadFileRequestAccessMethodChoice(recordAccess=AtomicReadFileRequestAccessMethodChoiceRecordAccess(
                fileStartRecord=0,
                requestedRecordCount=size
            ))
        else:
            method = AtomicReadFileRequestAccessMethodChoice(streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                fileStartPosition=0,
                requestedOctetCount=size
            ))
        request = AtomicReadFileRequest(
            fileIdentifier=fileId,
            accessMethod=method,
        )
        
        request.pduDestination = Address(address)
        return request



db = sqlite3.connect(config.db_file)

# Get all present files as tuples (Device ID, File object ID, File access method)
files_query = """
SELECT DISTINCT d.Address, o.BACnetId, pv.Value FROM Objects o
	JOIN Devices d ON o.Device = d.Id
	JOIN Properties p ON p.Object = o.Id AND p.Name = "fileAccessMethod"
	JOIN PropertyValues pv ON pv.Property = p.Id
	WHERE o.Type = "file"
"""
cur = db.cursor()
cur.execute(files_query)
files = cur.fetchall()
db.close()

os.makedirs('files', exist_ok=True)

bacnet = ReadFile(ip=config.probe_ip)
for address, file_id, access_method in files:
    try:
        if access_method == 'recordAccess':
            size = bacnet.read(f'{address} file {file_id} recordCount')
        else:
            size = bacnet.read(f'{address} file {file_id} fileSize')
        data = bacnet.read_file_stream(address, ('file', file_id), size, access_method)
        with open(f'files/{address}_{file_id}.xml', 'wb') as fout:
            fout.write(data)
    except Exception as e:
        print('Error while reading file', file_id, 'from', address)
        print(' ', e, flush=True)
bacnet.disconnect()