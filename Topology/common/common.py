import json
import time
import ipaddress
import os
import subprocess
import re
#import netsnmp
#from pysnmp.hlapi import *
from msa_sdk.variables import Variables
from msa_sdk.msa_api import MSA_API
from msa_sdk.order import Order
from msa_sdk.device import Device
from msa_sdk.customer import Customer
from msa_sdk.orchestration import Orchestration
from msa_sdk.lookup import Lookup
from msa_sdk import constants

dev_var = Variables()
context = Variables.task_call(dev_var)

MS_General_CDP_Neighbors         = 'General_CDP_Neighbors'        #MS filename to get LDDP neighbors
MS_GENERAL_HARDWARE_INFORMATION  = 'General_Hardware_Information' #MS filename for serial number
MS_General_Vlan_Interfaces       = 'General_Vlan_Interfaces'      #MS General_Vlan_Interfaces.xml
MS_Overlay_L2_Tenants_vn_segment = 'Overlay_L2_Tenants-vn_segment' 
MS_Overlay_L3_Tenants            = 'Overlay_L3_Tenants'  #VRF
MS_BGP_Neighbors                 = 'BGP_Neighbors'
#MS_Underlay_OSPF_Neighbors      = 'Underlay_OSPF_Neighbors'
MS_OSPF_Neighbors                = 'OSPF_Neighbors'


def send_continuous_request_on_MS_NETWORK(command, devicelongid, MS, param, stop_if_error= True, timeout = 120, interval = 10):
  order    = Order(devicelongid)
  global_timeout = time.time() + timeout
  count = 0
  context['import_resultat_'+MS+'_'+devicelongid] = {}
  while True and count< 4:
    order.command_execute(command, param)
    content = json.loads(order.content)
    count   = count + 1
    #context['import_resultat_'+MS+'_'+devicelongid]['11_'+str(count)] = content
    if order.response.ok:
      if command == 'IMPORT':
        #context['import_resultat_'+MS+'_'+devicelongid]['22_'+str(count)] = content
        if "message" in content:
          import_result_message = json.loads(content['message'])
          #context['import_resultat_'+MS+'_'+devicelongid]['33_'+str(count)] = import_result_message
          if MS in import_result_message:
            #context['import_resultat_'+MS+'_'+devicelongid]['44_'+str(count)] = import_result_message[MS]
            return import_result_message[MS]
          return {}
      else:
        return content
    else:
      if time.time() > global_timeout:
        if stop_if_error:
          MSA_API.task_error(command + ' Microservice "'+MS+'" FAILED on device '+str(devicelongid),context, True)
        else:
          return {}
    time.sleep(interval)
  if stop_if_error:
    MSA_API.task_error(command + ' Microservice "'+MS+'" FAILED on device '+str(devicelongid),context, True)
  else:
    return {}


 
def get_device_status (device_id):
  # Get device status from MSA
  devicelongid                    = device_id[3:]
  deviceObj    = Device(device_id= devicelongid) 
  device_status_resp = deviceObj.status()
  #device_status_resp = json.loads(device_status_resp)
  if device_status_resp == "UP":
    device_status = "OK"
  elif device_status_resp == "UNREACHABLE":
    device_status = "ERROR"
  elif device_status_resp == "CRITICAL":
    device_status = "CRITICAL"
  else:
    device_status = "NEVERREACHED"
  return  device_status 
    
  
def get_all_existing_devices_in_MSA_and_status():
  # Get all devices in the MSA for this customer_id
  global existing_devices_id_msa, existing_devices_name_msa, NOT_FOUND
  lookup      = Lookup()
  lookup.look_list_device_by_customer_ref(context['UBIQUBEID'])
  device_list = lookup.content
  context['device_list_result_str'] = device_list
  device_list = json.loads(device_list)
  existing_devices_id_msa   = {}
  existing_devices_name_msa = {}
  #existing_devices_per_IP    = {}
  for device in device_list:
    # device: {"id": 497,  "prefix": "sds", "ubiId": "sds497", "externalReference": "sds497",  "name": "LEAF-05"}
    if device.get('name') and device.get('externalReference') and device.get('ubiId'):
      new_device                      = {}
      new_device['name']              = device['name']
      devicelongid                    = device['ubiId'][3:]
      new_device['devicelongid']      = devicelongid
      new_device['device_id']         = device['ubiId']
      new_device['externalReference'] = device['externalReference']
      #Long if device.get('serial_number'):
      #Long   new_device['serial_number']   = device['serial_number']
      #Long else:
      #Long #to slow, don't need here
      #Long new_device['serial_number']   = get_device_serial_number(device['ubiId'], device['name'])        
      #Long deviceObj    = Device(device_id= devicelongid) 
      #Long device_detail = deviceObj.read()
      #Long device_detail = json.loads(device_detail)
      #Long # device_detail = "{  "manufacturerId" : 1,  "modelId" : 22032401,  "managementAddress" : "192.168.130.108",  "reporting" : true,  "useNat" : false,  "logEnabled" : true,  "logMoreEnabled" : true,  "managementInterface" : "",  "mailAlerting" : false,  "passwordAdmin" : "sds123!!",  "externalReference" : "sds493",  "login" : "xxxx",  "name" : "leaf-08",  "password" : "xxxx",  "id" : 493,  "snmpCommunity" : "xxxxx",  "sdNature" : "PHSL",  "hostname" : "",  "managementPort" : 80,  "monitoringPort" : 161}"   
      #Long new_device['management_address']         = device_detail['managementAddress']
      #Long new_device['device_nature']              = device_detail['sdNature']
      new_device['device_nature']              = 'PHSL'
      new_device['status']                     = get_device_status(device['ubiId'])
      new_device['subtype']                    = "router"
      existing_devices_id_msa[device['ubiId']]  = new_device
      existing_devices_name_msa[device['name']] = new_device
      #existing_devices_per_IP[device_detail['managementAddress']] = new_device
  context['existing_devices_id_msa_serialized']   = json.dumps(existing_devices_id_msa)
  context['existing_devices_name_msa_serialized'] = json.dumps(existing_devices_name_msa)
  #context['existing_devices_per_IP_serialized']       = json.dumps(existing_devices_per_IP)


def get_device_name_from_device_id(device_id):
  #get the curent name from device_id
  global existing_devices_id_msa
  for device in existing_devices_id_msa:
    if device['full_device_id'] == device_id:
      return new_device['name']
  return ''


def get_device_serial_number(device_id, device_name):
  global MS_GENERAL_HARDWARE_INFORMATION

  devicelongid = device_id[3:]
  order = Order(devicelongid)
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS_GENERAL_HARDWARE_INFORMATION] = obj
  # IMPORT ONLY the MS MS_GENERAL_HARDWARE_INFORMATION
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  response = json.loads(order.content)
  device_serial_number = ''

  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_serial_numbers_resp_'+device_id] = message
    if message.get(MS_GENERAL_HARDWARE_INFORMATION):
      # "message": "{"General_Hardware_Information":{"1":{"object_id":"1","serial_number":"9TMPYOOJXVV"}}}",
      for key, val in message[MS_GENERAL_HARDWARE_INFORMATION].items():
        if val.get('serial_number') and val['serial_number']:
          return val['serial_number']
  return ''

  
def find_direct_neighbors_for_one_device_CDP(device_id):
  global MS_General_CDP_Neighbors
  MS = MS_General_CDP_Neighbors
  # Task_Get_Device_Neighbours_List.py
  devicelongid = device_id[3:]
  order = Order(devicelongid)

  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the MS MS_General_CDP_Neighbors
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  #context['CDP_response_'+device_id+'_serialized'] = order.content
  response = json.loads(order.content)

  direct_neighbor_temp = {}
  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_neighbor_'+device_id] = message
    if message.get(MS):
      # "message": "{"General_CDP_Neighbors":{"eth1/8":{"object_id":"eth1/8","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/8","management_ip":"192.168.130.106"},"eth1/3":{"object_id":"eth1/3","neighbor_system_name":"Spine-03","neighbor_interface":"eth1/1","management_ip":"192.168.130.203"},"mgmt0":{"object_id":"mgmt0","neighbor_system_name":"Spine-03","neighbor_interface":"mgmt0","management_ip":"192.168.130.203"},"eth1/9":{"object_id":"eth1/9","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/9","management_ip":"192.168.130.106"},"eth1/4":{"object_id":"eth1/4","neighbor_system_name":"Spine-04","neighbor_interface":"eth1/1","management_ip":"192.168.130.204"}}}",
      direct_neighbor_temp = message[MS]  
      
  direct_neighbor = {}
  # "direct_neighbor_temp":{"eth1/8":{"object_id":"eth1/8","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/8","management_ip":"192.168.130.106"},"eth1/3":{"object_id":"eth1/3","neighbor_system_name":"Spine-03","neighbor_interface":"eth1/1","management_ip":"192.168.130.203"},"mgmt0":{"object_id":"mgmt0","neighbor_system_name":"Spine-03","neighbor_interface":"mgmt0","management_ip":"192.168.130.203"},"eth1/9":{"object_id":"eth1/9","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/9","management_ip":"192.168.130.106"},"eth1/4":{"object_id":"eth1/4","neighbor_system_name":"Spine-04","neighbor_interface":"eth1/1","management_ip":"192.168.130.204"}}}",
  for port, device2 in direct_neighbor_temp.items():
    if device2.get('neighbor_system_name') and device2.get('management_ip'):
      #We don't want management port (like mgmt0)
      if not re.search("^mgmt\d",device2['object_id']): 
        neighbor_device_name        = device2['neighbor_system_name']
        link = neighbor_device_name
        direct_neighbor[link] = 1
        
  return direct_neighbor


def find_direct_neighbors_for_SNMP(device_id):
  #Get community pwd and address from device inofrmations
  devicelongid = device_id[3:]
  deviceObj    = Device(device_id= devicelongid) 
  device_detail = deviceObj.read()
  #context['device_read_'+devicelongid+'_serialized'] = device_detail 
  device_detail = json.loads(device_detail)
  direct_neighbor = {}
  if device_detail.get('snmpCommunity'):   
    community = device_detail['snmpCommunity']   
  else:
    community = 'public'
  address = device_detail['managementAddress']     # '192.168.130.101'
  output_file = '/tmp/temp_' + context['SERVICEINSTANCEID'] + '.txt'

  # I use one temporary file output_file, else get one json error from api
  command_snmp = '/usr/bin/snmpwalk -v2c -c '+community+' '+address + ' IP-MIB::ipAdEntNetMask  > ' + output_file + ' 2>&1 '
  #context['snmp_command'] = command_snmp
  
  result =  os.system(command_snmp) 
  result =''
  with open (output_file , 'r') as f:
    for line in f:
      result = result +'<br>' + line
      #line = IP-MIB::ipAdEntNetMask.10.4.0.25 = IpAddress: 255.255.255.252
      #We want IP/netmask like 192.168.130.102/32
      found = re.search('IP-MIB::ipAdEntNetMask.(.+?) = IpAddress', line)
      if found :
        address_link = found.group(1)
        found = re.search(" IpAddress: (.+?)$", line)
        maskAdr      = found.group(1)
        mask = ipaddress.IPv4Network('0.0.0.0/'+maskAdr).prefixlen
        iface = ipaddress.ip_interface(address_link + '/' +maskAdr)
        network_address = str(iface.network.network_address)
        network_and_mask = network_address +'/' + str(mask)
        #context['snmp_res_IP'+devicelongid+'_'+line] = 'address_link=' + address_link +', maskAdr ='+maskAdr  +' mask='+str(mask)+ ' network_and_mask='+network_and_mask
        direct_neighbor[network_and_mask] = 1
        network_and_mask_objID =  network_and_mask.replace('.','_')
        createTopologyNetwork(network_and_mask_objID, network_and_mask, 'network', '', '', "#f7f30a") # color #f7f30a yellow
    f.close()

  #context['snmp_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)
  if os.path.exists(output_file):
    os.remove(output_file)

  return direct_neighbor
 
 

def find_direct_neighbors_for_VLAN(device_id):
  #Get subnets from interfaces
  global MS_General_Vlan_Interfaces
  MS = MS_General_Vlan_Interfaces
  devicelongid = device_id[3:]

  direct_neighbor = {}
  order = Order(devicelongid)
  #MS = General_Vlan_Interfaces
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the given MS 
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  #context['VLAN_response_'+device_id+'_serialized'] =order.content
  response = json.loads(order.content)

  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_neighbor_VLAN_'+device_id] = message
    if message.get(MS):

      for id,result in message.get(MS).items():
        # result :{"_order":"3600","enable_ip_forward":"","enable_multicast":"false","name":"vlan3600","description":"VPC-Peer-Link SVI by VPC MGMT","dhcp_relay_servers":{},"admin_state":"up","ip_list":{"0":{"ip_address":"10.4.0.37/30","routing_tag":"0","type":"primary"}},"oper_state":"up","object_id":"3600","mtu":"9216","enable_anycast_gateway":""}
        if result.get('object_id'):
          vlan_id = result['object_id']   # 2002
          if vlan_id != '1':
            vlan_id = 'vlan' + vlan_id
            direct_neighbor[vlan_id] = 1
            vlan_id_objID =  vlan_id.replace('.','_')
            createTopologyNetwork(vlan_id_objID, vlan_id, 'network', '', '', "#f7f30a") # color #f7f30a yellow
  
  context['vlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VXLAN(device_id):
  global MS_Overlay_L2_Tenants_vn_segment
  MS = MS_Overlay_L2_Tenants_vn_segment
  devicelongid = device_id[3:]

  direct_neighbor = {}
  order = Order(devicelongid)
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the given MS 
  response = order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  response = json.loads(order.content)
  #context['VXLAN_response_'+device_id+'_serialized'] = response 
  
  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_neighbor_VXLAN='+device_id] = message
    if message.get(MS):
      for id,result in message.get(MS).items():
        # result :{ "100": {  "vni": "10100",  "_order": "100", "VLAN_name": "test", "object_id": "100"  }
        if result.get('vni'):
          vni = 'vni'+result['vni']  
          #direct_neighbor[vni] = 1
          vni_objID =  vni.replace('.','_')
          createTopologyNetwork(vni_objID, vni, 'network','', '', "#3118f0")  # color #3118f0 blue
        if result.get('object_id') and result.get('vni'):
          VLAN_id = 'vlan'+result['object_id']  
          direct_neighbor[VLAN_id] = 1
          VLAN_id_objID =  VLAN_id.replace('.','_')
          links = []
          links.append('vni'+result['vni'])
          createTopologyNetwork(VLAN_id_objID, VLAN_id, 'network', '', links, "#f7f30a") # color #f7f30a yellow
  #context['vxlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VXLAN_VRF(device_id):
  global MS_Overlay_L2_Tenants_vn_segment, MS_Overlay_L3_Tenants
  MS = MS_Overlay_L2_Tenants_vn_segment
  MS2 = MS_Overlay_L3_Tenants
  devicelongid = device_id[3:]

  direct_neighbor = {}
  order = Order(devicelongid)
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params      = {}
  params[MS]  = obj
  params[MS2] = obj
  # IMPORT ONLY the given MS 
  response = order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  response = json.loads(order.content)
  #context['VXLAN_response_'+device_id+'_serialized'] = response 
  
  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_neighbor_VXLAN='+device_id] = message
    if message.get(MS):
      for id,result in message.get(MS).items():
        # result :{ "100": {  "vni": "10100",  "_order": "100", "VLAN_name": "test", "object_id": "100"  }
        if result.get('vni'):
          vni = 'vni'+result['vni']  
          #direct_neighbor[vni] = 1
          vni_objID =  vni.replace('.','_')
          createTopologyNetwork(vni_objID, vni, 'network','')
        if result.get('object_id') and result.get('vni'):
          VLAN_id= 'vlan'+result['object_id']  
          direct_neighbor[VLAN_id] = 1
          VLAN_id_objID =  VLAN_id.replace('.','_')
          links = []
          links.append('vni'+result['vni'])
          createTopologyNetwork(VLAN_id_objID, VLAN_id, 'network', '', links, "#3118f0")  # color #3118f0 blue
    if message.get(MS2):
      # "1104":{"vni":"50001","_order":"1104","VLAN_name": "example-vlan1104","object_id":"1104"},
      for id,result in message.get(MS).items():
          if result.get('object_id') and result.get('vni'):
            vrf = result['object_id']
            if  vrf != 'default' and vrf != 'management':
              vrf = 'vrf'+ vrf
              vrf_objID =  vrf.replace('.','_')
              links = []
              links.append('vni'+result['vni'])
              createTopologyNetwork(vrf_objID, vrf, 'network','', links, "#f7f30a") # color #f7f30a yellow
    
  #context['vxlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VRF(device_id):
  global MS_Overlay_L3_Tenants
  MS = MS_Overlay_L3_Tenants
  devicelongid = device_id[3:]

  direct_neighbor = {}
  order = Order(devicelongid)
  #MS = General_Vlan_Interfaces
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the given MS 
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  #context['VRF_response_'+device_id+'_serialized'] =order.content
  response = json.loads(order.content)

  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    if message.get(MS):
      # "1104":{"vni":"50001","_order":"1104","VLAN_name": "example-vlan1104","object_id":"1104"},
      for id,result in message.get(MS).items():
          if result.get('object_id') and result.get('vni'):
            vni= 'vni'+result['vni']  
            direct_neighbor[vni] = 1
            vni_objID =  vni.replace('.','_')
            createTopologyNetwork(vni_objID, vni, 'network', '','',  "#3118f0")  # color #3118f0 blue
          if result.get('object_id'):
            vrf = result['object_id']
            if  vrf != 'default' and vrf != 'management':
              vrf = 'vrf'+ vrf
              vrf_objID =  vrf.replace('.','_')
              links = []
              if result.get('vni'):
                links.append('vni'+result['vni'])

              createTopologyNetwork(vrf_objID, vrf, 'network','', links, "#f7f30a") # color #f7f30a yellow

              #direct_neighbor[vrf] = 1
  #context['vrf_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_OSPF(device_id):
  #TO FINISH
  global MS_OSPF_Neighbors
  MS = MS_OSPF_Neighbors
  devicelongid = device_id[3:]

  direct_neighbor = {}
  order = Order(devicelongid)
  #MS = General_Vlan_Interfaces
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the given MS 
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  #context['OSPF_response_'+device_id+'_serialized'] =order.content
  response = json.loads(order.content)

  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['direct_neighbor_'+device_id] = message
    if message.get(MS):

      for id,result in message.get(MS).items():
        if result.get("object_id"):
          neighbor_IP = result["object_id"] # IP
          neighbor_IP_objID =  neighbor_IP.replace('.','_')
          createTopologyNetwork(neighbor_IP_objID, neighbor_IP, 'network', '','',  "#3118f0")  # color #3118f0 blue
          direct_neighbor[neighbor_IP] = 1

  
  context['ospf_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_BGP(device_id):
  #TO FINISH
  global MS_BGP_Neighbors
  MS = MS_BGP_Neighbors
  devicelongid = device_id[3:]
  #existing_devices_per_IP = json.loads(context['existing_devices_per_IP_serialized'])

  direct_neighbor = {}
  order = Order(devicelongid)
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
  # IMPORT ONLY the given MS 
  order.command_execute('IMPORT', params, 120)
  # convert dict object into json
  #context['BGP_response_'+device_id+'_serialized'] =order.content
  response = json.loads(order.content)

  if (response.get("status") and response["status"] == "OK" or response.get("wo_status") and response["wo_status"] == "OK"):
    if response.get("status"):
      message = response["message"]
    else:
      message = response["wo_new_params"]
    message = json.loads(message)
    #context['bgp_result_raw_MS_import_'+device_id] = message
    if message.get(MS):
      
      for id,result in message.get(MS).items():
        # result = {"10_2_0_4": { "bgp_state": "established", "object_id": "10.2.0.4" },        neighbor='test' 
        if result.get("object_id"):
          neighbor_IP = result["object_id"] # IP
          neighbor_IP_objID =  neighbor_IP.replace('.','_')
          createTopologyNetwork(neighbor_IP_objID, neighbor_IP, 'network', '','',  "#3118f0")  # color #3118f0 blue
          direct_neighbor[neighbor_IP] = 1
              
  
  #context['bgp_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor

def createTopologyNetwork(nodeID, name, subType, image, neighbors=[], color="#acd7e5"):
  if context.get('other_nodes_serialized') :
    other_nodes = json.loads(context['other_nodes_serialized'])
  else:
    other_nodes = {}
  #color ="#e5c1ac"
  node = {}
  node["primary_key"]  = nodeID
  node["name"]         = name
  node["object_id"]    = nodeID
  node["x"]            = ""
  node["y"]            = ""
  node["description"]  = ""
  node["subtype"]      = subType
  node["image"]        = image
  node["color"]        = color
  node["hidden"]       = 'false' 
  node["cluster_id"]   = ""
  if neighbors:
    node["links"] = neighbors 
  other_nodes[nodeID]  = node

  context['other_nodes_serialized'] = json.dumps(other_nodes)
  
  #object_id = nodeID
  # if not context.get('Nodes_MAJ_Object_ID'):
    # context['Nodes_MAJ_Object_ID'] = {}
  # if not context['Nodes_MAJ_Object_ID'].get(object_id):
    # new_nodes_MAJ                = {}
    # new_nodes_MAJ['primary_key'] =  nodeID
    # #new_nodes_MAJ['object_id']  =  nodeID[3]
    # new_nodes_MAJ['object_id']   =  nodeID
    # context['Nodes_MAJ'].append(new_nodes_MAJ)
    # context['Nodes_MAJ_Object_ID'][object_id] = 1
