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
from msa_sdk import util

dev_var = Variables()
context = Variables.task_call(dev_var)
process_id = context['SERVICEINSTANCEID']

MS_VIEW_LIST = { 'CDP'                         : 'General_CDP_Neighbors',
                 'HARDWARE_INFORMATION'        : 'General_Hardware_Information' , 
                 'VLAN'                        : 'General_Vlan_Interfaces'  ,    
                 'VXLAN'                       : 'Overlay_L2_Tenants-vn_segment', 
                 'VRF'                         : 'Overlay_L3_Tenants' , 
                 'BGP'                         : 'Underlay_BGP_Neighbors',
                 'OSPF'                        : 'Underlay_OSPF_Neighbors',
                 'OSPF_IP'                     : 'General_Interfaces',
                 'OSPF_router_ID'             :  'General_OSPF_Base'                 }
 
def find_all_ip_in_subnet_ipv4_or_ipv6(ip_cidr):
    # Get all avaible IP from ipv4 cidr (ex 120.120.130.11/24) or ipv6 cidr
    # Not used anymore if we have to much IP available like 120.120.130.11/10 (4.194.304 IP)
    ips = ipaddress.ip_network(ip_cidr, strict=False)
    ip_list = [str(ip) for ip in ips]
    IP_List_Available = []
    for ip in ip_list:
        new_ip = str(ip).lower()
        IP_List_Available.append(new_ip)
    return IP_List_Available

    
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
  global existing_devices_id_msa,  NOT_FOUND
  lookup      = Lookup()
  curent_customer      = Customer()
  curent_customer.get_customer_by_id(context['UBIQUBEID'][4:])
  current_subtenant_detail = json.loads(curent_customer.content)
  # "current_subtenant_detail ": "{\"id\":14,\"actorId\":91,\"name\":\"Laurent\",\"address\":{\"streetName1\":\"\",\"streetName2\":\"\",\"streetName3\":\"\",\"city\":\"\",\"zipCode\":\"\",\"country\":\"\",\"email\":\"\",\"phone\":\"\"},\"civility\":null,\"company\":false,\"externalReference\":\"sdsA14\",\"firstname\":\"\",\"login\":\"Laurent14\",\"operatorPrefix\":\"sds\"}"
  context['current_subtenant_detail '] = current_subtenant_detail
  subtenant_externalReference = current_subtenant_detail['externalReference']
  context['Subtenant_externalReference'] = subtenant_externalReference 
  
  lookup.look_list_device_by_customer_ref(subtenant_externalReference )
  #lookup.look_list_device_by_customer_ref(context["UBIQUBEID"])
  device_list = lookup.content
  context['device_list_result_str'] = device_list
  #MSA_API.task_error('test laurent',context, True)

  
  device_list = json.loads(device_list)
      util.log_to_process_file(process_id, '***device_list***')
  util.log_to_process_file(process_id, device_list)
  existing_devices_id_msa   = {}
  for device in device_list:
    # device: {"id": 497,  "prefix": "sds", "ubiId": "sds497", "externalReference": "sds497",  "name": "LEAF-05"}
    if device.get('name') and device.get('externalReference') and device.get('ubiId'):
      new_device                      = {}
      new_device['name']              = device['name']
      devicelongid                    = device['ubiId'][3:]
      new_device['devicelongid']      = devicelongid
      new_device['device_id']         = device['ubiId']
      new_device['externalReference'] = device['externalReference']     
      util.log_to_process_file(process_id, '***new_device***')
      util.log_to_process_file(process_id, new_device)
      deviceObj    = Device(device_id= devicelongid) 
      util.log_to_process_file(process_id, '***deviceObj***')
      util.log_to_process_file(process_id, deviceObj)
      device_detail = deviceObj.read()
      util.log_to_process_file(process_id, '***device_detail***')
      util.log_to_process_file(process_id, device_detail)
      device_detail = json.loads(device_detail)
      #Long # device_detail = "{  "manufacturerId" : 1,  "modelId" : 22032401,  "managementAddress" : "192.168.130.108",  "reporting" : true,  "useNat" : false,  "logEnabled" : true,  "logMoreEnabled" : true,  "managementInterface" : "",  "mailAlerting" : false,  "passwordAdmin" : "sds123!!",  "externalReference" : "sds493",  "login" : "xxxx",  "name" : "leaf-08",  "password" : "xxxx",  "id" : 493,  "snmpCommunity" : "xxxxx",  "sdNature" : "PHSL",  "hostname" : "",  "managementPort" : 80,  "monitoringPort" : 161}"   
      new_device['management_address']         = device_detail['managementAddress']
      #Long new_device['device_nature']              = device_detail['sdNature']
      new_device['device_nature']              = 'PHSL'
      new_device['status']                     = get_device_status(device['ubiId'])
      new_device['subtype']                    = "router"
      new_device['links']                    = []
      existing_devices_id_msa[device['ubiId']]  = new_device
  context['existing_devices_id_msa_serialized']   = json.dumps(existing_devices_id_msa)


def get_device_name_from_device_id(device_id):
  #get the curent name from device_id
  global existing_devices_id_msa
  for device in existing_devices_id_msa:
    if device['full_device_id'] == device_id:
      return new_device['name']
  return ''


def get_device_serial_number(device_id, device_name):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['HARDWARE_INFORMATION']
  devicelongid = device_id[3:]
  order = Order(devicelongid)
  ms_input = {}
  ms_input['object_id'] = 'default' #need at least on value
  obj = {}
  obj['need_for_import'] = ms_input  
  params = {}
  params[MS] = obj
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
    if message.get(MS):
      # "message": "{"General_Hardware_Information":{"1":{"object_id":"1","serial_number":"9TMPYOOJXVV"}}}",
      for key, val in message[MS].items():
        if val.get('serial_number') and val['serial_number']:
          return val['serial_number']
  return ''

  
def find_direct_neighbors_for_CDP(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['CDP']
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
    #context['import_resultat_'+MS+'_'+devicelongid+'_CDP=']= message

    if message.get(MS):
      # "message": "{"General_CDP_Neighbors":{"eth1/8":{"object_id":"eth1/8","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/8","management_ip":"192.168.130.106"},"eth1/3":{"object_id":"eth1/3","neighbor_system_name":"Spine-03","neighbor_interface":"eth1/1","management_ip":"192.168.130.203"},"mgmt0":{"object_id":"mgmt0","neighbor_system_name":"Spine-03","neighbor_interface":"mgmt0","management_ip":"192.168.130.203"},"eth1/9":{"object_id":"eth1/9","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/9","management_ip":"192.168.130.106"},"eth1/4":{"object_id":"eth1/4","neighbor_system_name":"Spine-04","neighbor_interface":"eth1/1","management_ip":"192.168.130.204"}}}",
      direct_neighbor_temp = message[MS]  
      
  direct_neighbor = []
  # "direct_neighbor_temp":{"eth1/8":{"object_id":"eth1/8","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/8","management_ip":"192.168.130.106"},"eth1/3":{"object_id":"eth1/3","neighbor_system_name":"Spine-03","neighbor_interface":"eth1/1","management_ip":"192.168.130.203"},"mgmt0":{"object_id":"mgmt0","neighbor_system_name":"Spine-03","neighbor_interface":"mgmt0","management_ip":"192.168.130.203"},"eth1/9":{"object_id":"eth1/9","neighbor_system_name":"leaf-06","neighbor_interface":"eth1/9","management_ip":"192.168.130.106"},"eth1/4":{"object_id":"eth1/4","neighbor_system_name":"Spine-04","neighbor_interface":"eth1/1","management_ip":"192.168.130.204"}}}",
  for port, device2 in direct_neighbor_temp.items():
    if device2.get('neighbor_system_name') and device2.get('management_ip'):
      #We don't want management port (like mgmt0)
      if not re.search("^mgmt\\d",device2['object_id']): 
        neighbor_device_name = device2['neighbor_system_name']
        link                 = {}
        link['link']         = neighbor_device_name
        link['label']        = "CDP \n" + device_name+": "+device_ip+"\n"
        link['label'] = link['label'] + device2['neighbor_system_name'] +": "+device2['management_ip']
        direct_neighbor.append(link)
        
  return direct_neighbor


def find_direct_neighbors_for_SNMP(device_id, device_name, device_ip):
  #Get community pwd and address from device inofrmations
  devicelongid = device_id[3:]
  deviceObj    = Device(device_id= devicelongid) 
  device_detail = deviceObj.read()
  #context['device_read_'+devicelongid+'_serialized'] = device_detail 
  device_detail = json.loads(device_detail)
  direct_neighbor = []
  if device_detail.get('snmpCommunity'):   
    community = device_detail['snmpCommunity']   
  else:
    community = 'public'
  address = device_detail['managementAddress']     # '192.168.130.101'
  output_file = '/tmp/temp_' + context["SERVICEINSTANCEID"] + '.txt'

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
        #direct_neighbor[network_and_mask] = 1
        link                 = {}
        link['link']         = network_and_mask
        link['label']        = "SNMP \n" + device_name+": "+device_ip+"\n"
        if isinstance(result, dict) and result.get('name') and result.get('ip_list') and result['ip_list'].get('0') and result['ip_list']['0'].get('ip_address') :
           link['label'] = link['label'] + network_and_mask
        direct_neighbor.append(link)

        network_and_mask_objID =  network_and_mask.replace('.','_')
        createTopologyNetwork(network_and_mask_objID, network_and_mask, 'network','')
    f.close()

  #context['snmp_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)
  if os.path.exists(output_file):
    os.remove(output_file)

  return direct_neighbor
 
 

def find_direct_neighbors_for_VLAN(device_id, device_name, device_ip):
  #Get subnets from interfaces
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['VLAN']
  devicelongid = device_id[3:]

  direct_neighbor = []
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
    context['import_resultat_'+MS+'_'+devicelongid+'_VLAN=']= message
    if message.get(MS):

      for id,result in message.get(MS).items():
        # result :{"_order":"3600","enable_ip_forward":"","enable_multicast":"false","name":"vlan3600","description":"VPC-Peer-Link SVI by VPC MGMT","dhcp_relay_servers":{},"admin_state":"up","ip_list":{"0":{"ip_address":"10.4.0.37/30","routing_tag":"0","type":"primary"}},"oper_state":"up","object_id":"3600","mtu":"9216","enable_anycast_gateway":""}
        if result.get('object_id'):
          vlan_id = result['object_id']   # 2002
          if vlan_id != '1':
            vlan_id = 'vlan' + vlan_id
            #direct_neighbor[vlan_id] = 1
            link                 = {}
            link['link']         = vlan_id
            link['label']        = "VLAN \n" + device_name+": "+device_ip+"\n"
            if result.get('name') and result.get('ip_list') and result['ip_list'].get('0') and result['ip_list']['0'].get('ip_address') :
              link['label'] = link['label'] + result['name']+": "+result['ip_list']['0']['ip_address']
            elif result.get('name') :
              link['label'] = link['label'] + result['name']+":"
            direct_neighbor.append(link)

            vlan_id_objID =  vlan_id.replace('.','_')
            createTopologyNetwork(vlan_id_objID, vlan_id, 'network','')
  
  context['vlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VXLAN(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['VXLAN']
  devicelongid = device_id[3:]

  direct_neighbor = []
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
    #context['import_resultat_'+MS+'_'+devicelongid+'_VXLAN=']= content
    #context['direct_neighbor_VXLAN='+device_id] = message
    if message.get(MS):
      for id,result in message.get(MS).items():
        # result :{ "100": {  "vni": "10100",  "_order": "100", "VLAN_name": "test", "object_id": "100"  }
        if result.get('vni'):
          vni = 'vni'+result['vni']  
          vni_objID =  vni.replace('.','_')
          createTopologyNetwork(vni_objID, vni, 'network','')
        if result.get('object_id') and result.get('vni'):
          VLAN_id = 'vlan'+result['object_id']  
          #direct_neighbor[VLAN_id] = 1
          link                 = {}
          link['link']         = VLAN_id
          link['label']        = "VXLAN \n" + device_name+": "+device_ip+"\n"
          if result.get('object_id') and result.get('vni') :
            link['label'] = link['label'] + VLAN_id +": "+'vni'+ result['vni']
          direct_neighbor.append(link)
  
          VLAN_id_objID =  VLAN_id.replace('.','_')
          link                 = {}
          link['link']         = vni_objID
          link['label']        = "VXLAN \n "+VLAN_id+": "+vni

          createTopologyNetwork(VLAN_id_objID, VLAN_id, 'network', '', link, "#e5d7ac")
  #context['vxlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VXLAN_VRF(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS  = MS_VIEW_LIST['VXLAN']
  MS2 = MS_VIEW_LIST['VRF']
  devicelongid = device_id[3:]
  vni_vrf_links = {}

  direct_neighbor = []
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
    if message.get(MS2):
      # "1104":{"vni":"50001","_order":"1104","VLAN_name": "example-vlan1104","object_id":"1104"},
      for id,result in message.get(MS2).items():
          if result.get('object_id') and result.get('vni'):
            vrf = result['object_id']
            if  vrf != 'default' and vrf != 'management':
              vrf = 'vrf'+ vrf
              vrf_objID =  vrf.replace('.','_')
              links = []
              links.append('vni'+result['vni'])
              link                 = {}
              link['link']         =  'vni'+result['vni']
              vni_vrf_links['vni'+result['vni']] = vrf

              if result.get('object_id') :
                link['label'] = vrf+':'+ 'vni'+result['vni']
              createTopologyNetwork(vrf_objID, vrf, 'network','', link, "#e5d7ac")   
      if message.get(MS):
        for id,result in message.get(MS).items():
          # result :{ "100": {  "vni": "10100",  "_order": "100", "VLAN_name": "test", "object_id": "100"  }
          if result.get('vni'):
            vni = 'vni'+result['vni']  
            #We don't want to display the link between vlan<->vni and the link between devices<->vlan  if the vni is not linked to one vrf.
            if  vni in vni_vrf_links :   
              vni_objID =  vni.replace('.','_')
              createTopologyNetwork(vni_objID, vni, 'network','')
              if result.get('object_id'):
                VLAN_id= 'vlan'+result['object_id']  
                #direct_neighbor[VLAN_id] = 1
                link                 = {}
                link['link']         = 'vlan'+result['object_id']  
                link['label']        = "VLAN \n" + device_name+": "+device_ip+"\n"
                if result.get('object_id') and result.get('vni') :
                  link['label'] = link['label'] + 'vlan'+result['object_id']+": "+'vni'+ result['vni']
                direct_neighbor.append(link)
        
                VLAN_id_objID =  VLAN_id.replace('.','_')
                link                 = {}
                link['link']         =  vni_objID 
                link['label']        = "VLAN \n" + device_name+": "+device_ip+"\n"
                if result.get('object_id') and result.get('vni') :
                  link['label'] = link['label'] + 'vlan'+result['object_id']+": "+'vni'+ result['vni']
                createTopologyNetwork(VLAN_id_objID, VLAN_id, 'network', '', link, "#e5d7ac")
    
  #context['vxlan_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_VRF(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['VRF']
  devicelongid = device_id[3:]

  direct_neighbor = []
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
    #context['import_resultat_'+MS+'_'+devicelongid+'_VRF=']= message
    if message.get(MS):
      # "1104":{"vni":"50001","_order":"1104","VLAN_name": "example-vlan1104","object_id":"1104"},
      for id,result in message.get(MS).items():
          if result.get('object_id') and result.get('vni'):
            vni= 'vni'+result['vni']  
            #direct_neighbor[vni] = 1
            link                 = {}
            link['link']         = vni 
            link['label']        = "VRF \n" + device_name+": "+device_ip+"\n"
            link['label'] = link['label'] + 'vrf'+result['object_id']+": "+vni
            direct_neighbor.append(link)

            vni_objID =  vni.replace('.','_')
            createTopologyNetwork(vni_objID, vni, 'network', '')
          if result.get('object_id'):
            vrf = result['object_id']
            if  vrf != 'default' and vrf != 'management':
              vrf = 'vrf'+ vrf
              vrf_objID =  vrf.replace('.','_')
              link                 = {}
              link['link']         =  'vni'+result['vni']
              link['label'] = vrf+':'+ 'vni'+result['vni']
              createTopologyNetwork(vrf_objID, vrf, 'network','', link, "#e5d7ac")
              #direct_neighbor[vrf] = 1
  #context['vrf_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor

  

def find_direct_neighbors_for_OSPF():
  global MS_VIEW_LIST
  #For OSPF, we should get the interface name from underlay_OSPF_Neighbors and the range of IP for each interface from 'General_Interfaces'
  # If 2 device as the same range of IP, it define the link between theses 2 devices.
  #We should put label like
  # OSPF Neighbor
  # Spine1(device_name): 192.168.0.1(router_id)
  #     ethi1/1(interface_name): 10.4.0.1/30(IP_addr)
  # Leaf1(device_name): 192.168.0.2(router_id)
  #     ethi1/1(interface_name): 10.4.0.2/30(IP_addr)
  # State: full
  
  MS = MS_VIEW_LIST['OSPF']                       # 'Underlay_OSPF_Neighbors',
  MS_IP = MS_VIEW_LIST['OSPF_IP']                 # 'General_Interfaces'
  MS_router_ID = MS_VIEW_LIST['OSPF_router_ID' ]  # 'General_OSPF_Base'  
  devices = {}
  neighbors = {}
  IP_neighbors = {}
  existing_devices_id_msa   = json.loads(context['existing_devices_id_msa_serialized'])
  for device_id, device in existing_devices_id_msa.items():
    device['test'] = device_id
    devicelongid = device_id[3:]
    if device['status'] == 'OK':
      order                  = Order(devicelongid)
      ms_input               = {}
      ms_input['object_id']  = 'default' #need at least on value
      obj                    = {}
      obj['need_for_import'] = ms_input  
      params                 = {}
      params[MS]             = obj
      params[MS_IP]          = obj
      params[MS_router_ID]   = obj
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
        context['import_resultat_'+device_id+'_OSPF=']= message
 
        #get IP range for each interface
        if message.get(MS_IP): 
          for id,result in message.get(MS_IP).items():
            #  ip_list.0.ip_address  
            context['import_resultat_'+MS_IP+'_'+device_id+'_OSPF=']= result
            #result = {  "object_id": "po100", "vrf": "default", "ip_list": {  "0": {  "ip_address": "10.4.0.29/30",
            if result.get("object_id") and result.get("ip_list") and result["ip_list"]:
              interface_name = result['object_id']       
              if not re.search("^mgmt\\d",interface_name):        
                for id, ip_list in result["ip_list"].items():
                  if ip_list.get('ip_address'):
                    # ip_cidr = 192.168.130.1/30, we should find all IP avaible in this range with find_all_ip_in_subnet_ipv4_or_ipv6
                    # workflows/common/common.py:def find_all_ip_in_subnet_ipv4_or_ipv6(ip_cidr):
                    if not devices.get(device_id):
                      devices[device_id] = {}
                      devices[device_id] ['device_id'] = device_id
                    if not devices[device_id].get(interface_name):
                      devices[device_id][interface_name] = {}                  
                    
                    # it is faster to get only one string than 4 IP and check all IP individually 
                    devices[device_id][interface_name]['all_ips_string'] = '-'.join(find_all_ip_in_subnet_ipv4_or_ipv6( ip_list['ip_address'] ))
                    devices[device_id][interface_name]['cidr'] =  ip_list['ip_address']
                            
        #Get  router_ID from "General_OSPF_Base"
        if message.get(MS_router_ID):
          for id, result in message.get(MS_router_ID).items():
            context['import_resultat_'+MS_router_ID+'_'+device_id+'_OSPF=']= result
            #result =  { "UNDERLAY": { "object_id": "UNDERLAY", "dom_list": { "0": {  "name": "default",  "router_id": "10.2.0.7",
            if result.get("object_id") and result.get("dom_list"):
              for id2, dom_list in result["dom_list"].items():
                if dom_list.get("name") and dom_list.get("router_id"):
                  if not devices.get(device_id):
                    devices[device_id] = {}
                  devices[device_id] ['device_id'] = device_id
                  devices[device_id] ['router_id'] = dom_list['router_id']
                    
        if message.get(MS):
          for id, result in message.get(MS).items():
             # vrf_list.0.interface_list.0.interface_name
             # vrf_list.0.interface_list.0.state
             context['import_resultat_'+MS+'_'+device_id+'_OSPF=']= result
             #result = { "object_id": "UNDERLAY", "vrf_list": { 0": {   "interface_list": {  "0": {  "interface_name": "po100", "state": "full","ospf_neighbor": "10.2.0.7"

             if result.get("object_id") and result.get("vrf_list") and result["object_id"]  == "UNDERLAY":
               vrf_lists = result['vrf_list']
               for id2, vrf_list in result["vrf_list"].items():
                 #if vrf_list.get("interface_list") and vrf_list.get("name") and vrf_list["name"]  == "default":
                 if vrf_list.get("interface_list") :
                  for id3, interface in vrf_list["interface_list"].items():
                    if interface.get('interface_name') and interface.get('state') and interface.get('state') != 'loopback' :
                      if not devices.get(device_id):
                        devices[device_id] = {}
                      interface_name = interface['interface_name']
                      if  devices[device_id].get(interface_name) and devices[device_id][interface_name].get('all_ips_string'):
                        all_ips_string= devices[device_id][interface_name]['all_ips_string']
                        #Check if one other device has the same range of ip as neighbor
                        if IP_neighbors.get(all_ips_string):
                          for detail in IP_neighbors[all_ips_string]:
                            # true neighbor
                            link={}
                            link['link']      = detail['device_name']
                            link['device_id'] = detail['device_id']
                            if devices[device_id].get('router_id'):
                              router_id = devices[device_id]['router_id']
                            else:
                              router_id = ''
                            link['label']     = "OSPF Neighbor\n" + device['name'] + ': ' + router_id 
                            link['label']    = link['label'] + "\n" + interface_name + ":" + devices[device_id][interface_name]['cidr']
                            link['label']    = link['label'] + "\n" + detail['port_detail'] +"\n State:"+ interface['state']
                            if not device.get('links'):
                              device['links'] = []
                            #add link only on the last direction, faster
                            device['links'].append(link)
                            
                        #store this new IP list
                        if not IP_neighbors.get(all_ips_string):
                          IP_neighbors[all_ips_string] = []
                        detail = {}
                        detail['device_name'] = device['name']
                        detail['device_id'] = device_id
                        if devices[device_id].get('router_id'):
                          router_id = devices[device_id]['router_id']
                        else:
                          router_id = ''
                        detail['port_detail'] = device['name'] +': ' + router_id
                        detail['port_detail'] = detail['port_detail'] + "\n" + interface_name +': ' +devices[device_id][interface_name]['cidr']
                        IP_neighbors[all_ips_string].append(detail)
                        
  context['IP_neighbors'] = IP_neighbors
  context['devices_ospf'] = devices   
  context['dexisting_devices_id_msa_ospf'] = existing_devices_id_msa  
  return existing_devices_id_msa


def find_direct_neighbors_for_OSPF_old(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['OSPF']
  devicelongid = device_id[3:]

  direct_neighbor = []
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
    #context['import_resultat_'+MS+'_'+devicelongid+'_OSPF=']= message

    if message.get(MS):

      for id,result in message.get(MS).items():
        if result.get("object_id"):
          neighbor_IP = result["object_id"] # IP
          neighbor_IP_objID =  neighbor_IP.replace('.','_')
          createTopologyNetwork(neighbor_IP_objID, neighbor_IP, 'network','')
          #direct_neighbor[neighbor_IP] = 1
          link                 = {}
          link['link']         = neighbor_IP 
          link['label']        = "OSPF \n" + device_name+": "+device_ip+"\n"
          link['label'] = link['label'] + 'ospf: '+neighbor_IP
          direct_neighbor.append(link)
  
  context['ospf_result_'+devicelongid+'_serialized'] = json.dumps(direct_neighbor)

  return direct_neighbor


def find_direct_neighbors_for_BGP(device_id, device_name, device_ip):
  global MS_VIEW_LIST
  MS = MS_VIEW_LIST['BGP']
  devicelongid = device_id[3:]
  #existing_devices_per_IP = json.loads(context['existing_devices_per_IP_serialized'])

  direct_neighbor = []
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
        # result = {"10_2_0_4": { "state": "established", "object_id": "10.2.0.4" },        neighbor='test' 
        if result.get("object_id"):
          neighbor_IP = result["object_id"] # IP
          neighbor_IP_objID =  neighbor_IP.replace('.','_')
          createTopologyNetwork(neighbor_IP_objID, neighbor_IP, 'network','')
          #direct_neighbor[neighbor_IP] = 1
          link                 = {}
          link['link']         = neighbor_IP 
          link['label']        = "BGP, state: "+ result["state"]  +"\n" + device_name+": "+device_ip+"\n"
          link['label'] = link['label'] + 'vrf: '+neighbor_IP
          direct_neighbor.append(link)              
  

  return direct_neighbor

def createTopologyNetwork(nodeID, name, subType, image, neighbor={}, color="#acd7e5"):
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
  node["y"]            = "0"
  node["description"]  = ""
  node["subtype"]      = subType
  node["image"]        = image
  node["color"]        = color
  node["hidden"]       = 'false' 
  node["cluster_id"]   = ""
  node["links"] = [];
  if neighbor:
    node["links"].append(neighbor)
  other_nodes[nodeID]  = node

  context['other_nodes_serialized'] = json.dumps(other_nodes)

