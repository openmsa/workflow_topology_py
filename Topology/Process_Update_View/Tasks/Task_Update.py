import json
import time
import ipaddress
import os
import re
import sys
from msa_sdk.variables import Variables
from msa_sdk.msa_api import MSA_API
from msa_sdk.order import Order
from msa_sdk.device import Device
from msa_sdk.customer import Customer
from msa_sdk.orchestration import Orchestration
from msa_sdk.lookup import Lookup
#from functorflow import Check_cidr

# List all the parameters required by the task
dev_var = Variables()
#dev_var.add('ipam_device_id', var_type='Device')

context = Variables.task_call(dev_var)

currentdir = os.path.dirname(os.path.realpath(__file__))
wf_dir  = os.path.dirname(os.path.dirname(currentdir))
sys.path.append(wf_dir)
from common.common import get_all_existing_devices_in_MSA_and_status, find_direct_neighbor, MS_VIEW_LIST, find_direct_neighbors_for_Generic_Tunnels, find_direct_neighbors_for_OSPF


#################### PRG START ###############################    
 

#if not context['ipam_device_id'] :
#  MSA_API.task_error('Mandatory parameters required',context, True)

# Get all devices in the MSA for this customer_id
existing_devices_id_msa = get_all_existing_devices_in_MSA_and_status()

context['Nodes_MAJ']              = []
context['other_nodes_serialized'] = ''

nb_links = 0

if str(context['view_type']) == 'OSPF':
  find_direct_neighbors_for_OSPF()
elif str(context['view_type']) == 'Generic_Tunnels':
  find_direct_neighbors_for_Generic_Tunnels()
else:
  for device_id, device in existing_devices_id_msa.items():
    devicelongid = device_id[3:]
    neighbors = []
    if device['status'] == 'OK':
  
      if device.get('name'):
        device_name = device['name']
      else:
        device_name = '???'
      if device.get('management_address'):
        device_ip = device['management_address']
      else:
        device_ip = 'xxx.xxx.xxx.xxx'

      direct_neighbor = find_direct_neighbor(device_id, device_name, device_ip)
      if direct_neighbor:
        for link in direct_neighbor:
          neighbors.append(link)
      device['subtype'] = 'NETWORK'

    device['links'] = neighbors


if context.get('other_nodes_serialized') and context['other_nodes_serialized']:
  position_y = '150'
else:  
  position_y = ''

#Convert hash table into array for Topology view_type
nodes = []
other_nodes = {}

if context.get('other_nodes_serialized') and context['other_nodes_serialized']:
  other_nodes = json.loads(context['other_nodes_serialized'])
  for node in other_nodes.values():
    if node.get('links'):
      nb_links = nb_links + len(node['links'])
    nodes.append(node)

for device_id, device in existing_devices_id_msa.items():
  if device['displayInTopology']:
    if device['device_id'] not in other_nodes:
      # Do not add device already in other_nodes
      node = {}
      node["primary_key"]  = device_id
      node["name"]         = device['name']
      node["object_id"]    = device_id[3:]
      node["x"]            = ""
      node["y"]            = position_y
      node["description"]  = ""
      node["subtype"]      = device['subtype']
      node["image"]        = ""
      if device.get('status') and device['status'] == 'OK':
        node["color"]        = "#acd7e5"  #green
      else:
        node["color"]        = "#db2e14"  #red
      node["hidden"]       = 'false'
      node["cluster_id"]   = ""

      if device.get('links'):
        nb_links = nb_links + len(device['links'])
      node["links"]        = device['links']
      if device.get('device_nature'):
        node["device_nature"] = device['device_nature']
      node["status"]       = device['status']
      nodes.append(node)

context['Nodes_MAJ_Object_ID'] = []
context['Nodes'] = nodes

if (nb_links == 0):
  if MS_VIEW_LIST.get(context['view_type']):
    MS_list = MS_VIEW_LIST[context['view_type']]
    MS = ''
    for ms in MS_list.values():
      MS = MS + f'{ms} '
  else:
    MS = 'Undefined'
  MSA_API.task_success(f'Can not find any link, may be MS {MS} not attached', context, True)

MSA_API.task_success(f"OPERATION ENDED, topology schema {context['view_type']} updated", context, True)
