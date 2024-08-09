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
from common.common import *


    
#################### PRG START ###############################    
 

#if not context['ipam_device_id'] :
#  MSA_API.task_error('Mandatory parameters required',context, True)

# Get all devices in the MSA for this customer_id
get_all_existing_devices_in_MSA_and_status()

not_existing_device_in_msa        = {}

context['Nodes_MAJ']              = []
context['other_nodes_serialized'] = ''

nb_links=0

if str(context['view_type']) == 'OSPF':
  existing_devices_id_msa = find_direct_neighbors_for_OSPF()
  
else:
  existing_devices_id_msa   = json.loads(context['existing_devices_id_msa_serialized'])
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
    
      function = "find_direct_neighbors_for_" + str(context['view_type'])
      if function in globals():
        direct_neighbor_function = globals()[function]
        direct_neighbor = direct_neighbor_function(device_id, device_name, device_ip)
      else:
        MSA_API.task_error('TODO CONVERT PHP INTO PYTHON',context, True)
    
      if direct_neighbor:
        for link in direct_neighbor:
          neighbors.append(link)
      device['subtype'] = 'NETWORK'

    #existing_devices_id_msa[device['device_id']]['neighbors'] = neighbors
    device['links'] = neighbors

  
  
if context.get('other_nodes_serialized') and context['other_nodes_serialized']:
  position_y = '150'
else:  
  position_y = ''
  
#Convert hash table into array for Topology view_type
nodes = []
for device_id, device in existing_devices_id_msa.items():

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
    nb_links = nb_links+ len(device['links'])
  node["links"]        = device['links']
  if device.get('device_nature'):
    node["device_nature"]= device['device_nature']
  node["status"]       = device['status']
  nodes.append(node)

  
if context.get('other_nodes_serialized') and context['other_nodes_serialized']:
  other_nodes = json.loads(context['other_nodes_serialized'])
  for nodeID, node in other_nodes.items() :
     nodes.append(node)

context['Nodes_MAJ_Object_ID'] = []
context['Nodes'] = nodes
context['existing_devices_id_msa_serialized']     = json.dumps(existing_devices_id_msa)
  
if (nb_links==0):
  # Check if the selected MS is attached
  if MS_VIEW_LIST.get(context['view_type']):
    MS = MS_VIEW_LIST[context['view_type']]
  else:
    MS = 'Undefined'
  MSA_API.task_success('Can not find any link, may be MS '+MS+' not attached',context, True)

MSA_API.task_success('OPERATION ENDED, topology schema "' + context['view_type'] + '" updated',context, True)
   