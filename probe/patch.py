from bacpypes.basetypes import *
from bacpypes.apdu import ReadAccessSpecification
from BAC0.core.io.Read import *
from BAC0.core.io.IOExceptions import *
from BAC0.scripts import Lite
import bacpypes.basetypes

from bacpypes.udp import UDPDirector
from bacpypes.comm import PDU
import dpkt
import socket

import config

def build_rpm_request_patch(self, args, vendor_id = 0):
    self._log.debug(args)
    i = 0
    addr = args[i]
    i += 1
    vendor_id = vendor_id
    
    read_access_spec_list = []
    while i < len(args):
        obj_type_str = args[i]
        i += 1
    
        obj_type = self._ReadProperty__get_obj_type(obj_type_str, vendor_id)
        obj_inst = int(args[i])
        i += 1
    
        prop_reference_list = []
        while i < len(args):
            prop_id = args[i]
            if "@obj_" in prop_id:
                break
            i += 1
    
            # build a property reference
            prop_reference = PropertyReference(propertyIdentifier=prop_id)
    
            # check for an array index
            if (i < len(args)) and args[i].isdigit():
                prop_reference.propertyArrayIndex = int(args[i])
                i += 1
    
            prop_reference_list.append(prop_reference)
    
        if not prop_reference_list:
            raise ValueError("provide at least one property")
    
        # build a read access specification
        read_access_spec = ReadAccessSpecification(
            objectIdentifier=(obj_type, obj_inst),
            listOfPropertyReferences=prop_reference_list,
        )
    
        read_access_spec_list.append(read_access_spec)
    
    if not read_access_spec_list:
        raise RuntimeError("at least one read access specification required")
    
    # build the request
    request = ReadPropertyMultipleRequest(
        listOfReadAccessSpecs=read_access_spec_list
    )
    request.pduDestination = Address(addr)
    return request    

def readMultiple_patch(
    self,
    args: str,
    request_dict=None,
    vendor_id: int = 0,
    timeout: int = 10,
    show_property_name: bool = False,
) -> t.Union[t.Dict, t.List[t.Tuple[t.Any, str]]]:
    """Build a ReadPropertyMultiple request, wait for the answer and return the values

    :param args: String with <addr> ( <type> <inst> ( <prop> [ <indx> ] )... )...
    :returns: data read from device (str representing data like 10 or True)

    *Example*::

        import BAC0
        myIPAddr = '192.168.1.10/24'
        bacnet = BAC0.connect(ip = myIPAddr)
        bacnet.readMultiple('2:5 analogInput 1 presentValue units')

    Requests the controller at (Network 2, address 5) for the (presentValue and units) of
    its analog input 1 (AI:1).
    """
    if not self._started:
        raise ApplicationNotStarted("BACnet stack not running - use startApp()")

    if request_dict is not None:
        request = self.build_rpm_request_from_dict(request_dict, vendor_id)
    else:
        args_list = args.split()
        request = self.build_rpm_request(args_list, vendor_id=vendor_id)
        self.log_title("Read Multiple", args_list)

    values = []
    dict_values = {}

    try:
        # build an ReadPropertyMultiple request
        iocb = IOCB(request)
        iocb.set_timeout(timeout)
        # pass to the BACnet stack
        deferred(self.this_application.request_io, iocb)
        self._log.debug("{:<20} {!r}".format("iocb", iocb))

    except ReadPropertyMultipleException as error:
        # construction error
        self._log.exception("exception: {!r}".format(error))

    iocb.wait()  # Wait for BACnet response

    if iocb.ioResponse:  # successful response
        apdu = iocb.ioResponse

        # note: the return types along this pass don't appear to be consistent
        # not sure if this is a real problem or not, leaving as-is and ignoring errors
        if not isinstance(apdu, ReadPropertyMultipleACK):  # expecting an ACK
            self._log.debug("{:<20}".format("not an ack"))
            self._log.warning(
                "Not an Ack. | APDU : {} / {}".format(apdu, type(apdu))
            )
            return  # type: ignore[return-value]

        # loop through the results
        for result in apdu.listOfReadAccessResults:
            # here is the object identifier
            objectIdentifier = result.objectIdentifier

            self.log_subtitle(
                "{!r} : {!r}".format(objectIdentifier[0], objectIdentifier[1]),
                width=114,
            )
            self._log.debug(
                "{:<20} {:<20} {:<30} {:<20}".format(
                    "propertyIdentifier", "propertyArrayIndex", "value", "datatype"
                )
            )
            self._log.debug("-" * 114)
            dict_values[objectIdentifier] = []
            # now come the property values per object
            for element in result.listOfResults:
                # get the property and array index
                propertyIdentifier = element.propertyIdentifier
                propertyArrayIndex = element.propertyArrayIndex

                readResult = element.readResult

                if propertyArrayIndex is not None:
                    _prop_id = "{}@idx:{}".format(
                        propertyIdentifier, propertyArrayIndex
                    )
                else:
                    _prop_id = propertyIdentifier

                if readResult.propertyAccessError is not None:
                    self._log.debug(
                        "Property Access Error for {}".format(
                            readResult.propertyAccessError
                        )
                    )
                    values.append(None)
                    dict_values[objectIdentifier].append((_prop_id, None))
                else:
                    # here is the value
                    propertyValue = readResult.propertyValue

                    # find the datatype
                    datatype = get_datatype(
                        objectIdentifier[0], propertyIdentifier, vendor_id=vendor_id
                    )

                    if not datatype:
                        value = cast_datatype_from_tag(
                            propertyValue, objectIdentifier[0], propertyIdentifier
                        )
                    else:
                        # special case for array parts, others are managed by cast_out
                        if issubclass(datatype, Array) and (
                            propertyArrayIndex is not None
                        ):
                            if propertyArrayIndex == 0:
                                value = propertyValue.cast_out(Unsigned)
                            else:
                                value = propertyValue.cast_out(datatype.subtype)
                        elif propertyValue.is_application_class_null():
                            value = None
                        else:
                            value = propertyValue.cast_out(datatype)

                        self._log.debug(
                            "{!r:<20} {!r:<20} {!r:<30} {!r:<20}".format(
                                propertyIdentifier,
                                propertyArrayIndex,
                                value,
                                datatype,
                            )
                        )
                    if show_property_name:
                        try:
                            int(
                                propertyIdentifier
                            )  # else it will be a name like maxMaster
                            prop_id = "@prop_{}".format(propertyIdentifier)
                            _obj, _id = apdu.listOfReadAccessResults[
                                0
                            ].objectIdentifier
                            _key = (str(_obj), vendor_id)
                            if _key in registered_object_types.keys():
                                _classname = registered_object_types[_key].__name__
                                for k, v in registered_object_types["BAC0"][
                                    _classname
                                ].items():
                                    if v["obj_id"] == propertyIdentifier:
                                        prop_id = (k, propertyIdentifier)  # type: ignore
                            if isinstance(value, dict):
                                value = list(value.items())[0][1]

                        except ValueError:
                            prop_id = propertyIdentifier
                        values.append((value, prop_id))
                        dict_values[objectIdentifier].append(
                            (_prop_id, (value, prop_id))
                        )
                    else:
                        values.append(value)
                        dict_values[objectIdentifier].append((_prop_id, value))

        if request_dict is not None:
            return dict_values
        else:
            return values

    # note: the return types along this pass don't appear to be consistent
    # not sure if this is a real problem or not, leaving as-is and ignoring errors
    if iocb.ioError:  # unsuccessful: error/reject/abort
        apdu = iocb.ioError
        reason = find_reason(apdu)
        self._log.warning("APDU Abort Reject Reason : {}".format(reason))
        self._log.debug("The Request was : {}".format(args))
        if reason == "unrecognizedService":
            raise UnrecognizedService()
        elif reason == "segmentationNotSupported":
            # value = self._split_the_read_request(args, arr_index)
            # return value
            self.segmentation_supported = False
            raise SegmentationNotSupported()
        elif reason == "unknownObject":
            self._log.warning("Unknown object {}".format(args))
            raise UnknownObjectError("Unknown object {}".format(args))
        elif reason == "unknownProperty":
            self._log.warning("Unknown property {}".format(args))
            raise UnknownPropertyError("Unknown property {}".format(args))
        elif reason == "bufferOverflow":
            self._log.warning("Buffer overflow {}".format(args))
            raise BufferOverflow("Buffer overflow {}".format(args))
        else:
            self._log.warning("No response from controller {}".format(reason))
            raise ReadPropertyMultipleException("No response from controller {}".format(reason))

    return values

ReadProperty.build_rpm_request = build_rpm_request_patch
ReadProperty.readMultiple = readMultiple_patch


# If errors occur while printing complex objects, remove everything below
from io import StringIO
import inspect

def dump(self):
    out = StringIO()
    self.debug_contents(file=out)
    return out.getvalue()

def str_wrap(self):
    return str(self)

for _, typ in inspect.getmembers(bacpypes.basetypes, inspect.isclass):
    if typ.__repr__ is object.__repr__:
        if hasattr(typ, 'debug_contents'):
            typ.__repr__ = dump
        elif typ.__str__ is object.__str__:
            typ.__repr__ = str_wrap



# For illegal values detection only
packets = []
udp_template = b"\xff\xff\xff\xff\xff\xff\n\x00'\x00\x00\x05\x08\x00E\x00%b\x00\x01\x00\x00@\x11\x8bh%b%b%b%b%b\xde\xad%b"

def handle_read_patch(self):
    _debug = False
    if _debug: UDPDirector._debug("handle_read(%r)", self.address)

    try:
        msg, addr = self.socket.recvfrom(65536)
        if _debug: UDPDirector._debug("    - received %d octets from %s", len(msg), addr)

        if config.enable_capture and config.capture_target_ip == addr[0]:
            try:
                packet = udp_template % \
                    ((len(msg) + 28).to_bytes(2, 'big'),    # IP packet length
                     socket.inet_aton(addr[0]),             # Source IP
                     socket.inet_aton(config.probe_ip),     # Destination IP
                     addr[1].to_bytes(2, 'big'),            # Source port
                     b'\xba\xc0',                           # Destination port
                     (len(msg) + 8).to_bytes(2, 'big'),     # UDP packet length
                     msg                                    # Payload
                    )
                packets.append(packet)
            except Exception as e:
                print(e)

        # send the PDU up to the client
        deferred(self._response, PDU(msg, source=addr))

    except socket.timeout as err:
        if _debug: UDPDirector._debug("    - socket timeout: %s", err)

    except socket.error as err:
        if err.args[0] == 11:
            pass
        else:
            if _debug: UDPDirector._debug("    - socket error: %s", err)

            # pass along to a handler
            self.handle_error(err)

def handle_write_patch(self):
    _debug = False
    """get a PDU from the queue and send it."""
    if _debug: UDPDirector._debug("handle_write(%r)", self.address)

    try:
        pdu = self.request.get()

        if config.enable_capture and config.capture_target_ip == pdu.pduDestination[0]:
            try:
                packet = udp_template % \
                        ((len(pdu.pduData) + 28).to_bytes(2, 'big'),    # IP packet length
                         socket.inet_aton(config.probe_ip),             # Source IP
                         socket.inet_aton(pdu.pduDestination[0]),       # Destination IP
                         b'\xba\xc0',                                   # Source port
                         pdu.pduDestination[1].to_bytes(2, 'big'),      # Destination port
                         (len(pdu.pduData) + 8).to_bytes(2, 'big'),     # UDP packet length
                         pdu.pduData                                    # Payload
                        )
                packets.append(packet)
            except Exception as e:
                print(e)

        sent = self.socket.sendto(pdu.pduData, pdu.pduDestination)
        if _debug: UDPDirector._debug("    - sent %d octets to %s", sent, pdu.pduDestination)

    except socket.error as err:
        if _debug: UDPDirector._debug("    - socket error: %s", err)

        # get the peer
        peer = self.peers.get(pdu.pduDestination, None)
        if peer:
            # let the actor handle the error
            peer.handle_error(err)
        else:
            # let the director handle the error
            self.handle_error(err)

def write_packets():
    with open(config.capture_output_file, 'wb') as fout:
        write = dpkt.pcap.Writer(fout)
        for elem in packets:
            write.writepkt(elem)

UDPDirector.handle_read = handle_read_patch
UDPDirector.handle_write = handle_write_patch
