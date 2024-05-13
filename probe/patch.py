from bacpypes.basetypes import *
from bacpypes.apdu import ReadAccessSpecification
from BAC0.core.io.Read import *
from BAC0.scripts import Lite

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

ReadProperty.build_rpm_request = build_rpm_request_patch


# If errors occur while printing complex objects, remove everything below
from io import StringIO

def dump(self):
    out = StringIO()
    self.debug_contents(file=out)
    return out.getvalue()

PriorityArray.__str__ = dump
COVSubscription.__str__ = dump
DateTime.__str__ = dump
TimeStamp.__str__ = dump
DailySchedule.__str__ = dump