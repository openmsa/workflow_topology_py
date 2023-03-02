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
#	MSA_API.task_error('Mandatory parameters required',context, True)

# Get all devices in the MSA for this customer_id
get_all_existing_devices_in_MSA_and_status()

not_existing_device_in_msa        = {}

context['Nodes_MAJ']              = []
context['other_nodes_serialized'] = ''

# read the ID of the selected managed entity
#curent_device_id = context['ipam_device_id']
existing_devices_id_msa   = json.loads(context['existing_devices_id_msa_serialized'])
existing_devices_name_msa = json.loads(context['existing_devices_name_msa_serialized'])
for device_id, device in existing_devices_id_msa.items():
  devicelongid = device_id[3:]
  neighbors = []
  if device['status'] == 'OK':
    if context['view_type'] == 'CDP': 
      #find his direct neighbor from CDP MS
      direct_neighbor = find_direct_neighbors_for_one_device_CDP(device_id)
    elif context['view_type'] == 'SNMP': 
      #find his direct neighbor from snmp command v2
      direct_neighbor = find_direct_neighbors_for_SNMP(device_id)
    elif context['view_type'] == 'VLAN': 
      #find his direct neighbor from MS_General_Vlan_Interfaces
      direct_neighbor = find_direct_neighbors_for_VLAN(device_id)
    elif context['view_type'] == 'VXLAN': 
      #find his direct neighbor from Overlay_L2_Tenants-vn_segment.xml
      direct_neighbor = find_direct_neighbors_for_VXLAN(device_id)
    elif context['view_type'] == 'VXLAN_VRF': 
      #find his direct neighbor from Overlay_L2_Tenants-vn_segment.xml and Overlay_L3_Tenants.xml
      direct_neighbor = find_direct_neighbors_for_VXLAN_VRF(device_id)
    elif context['view_type'] == 'OSPF': 
      #find his direct neighbor from MS_Underlay_OSPF_Neighbors
      direct_neighbor = find_direct_neighbors_for_OSPF(device_id)
    elif context['view_type'] == 'BGP': 
      #find his direct neighbor from MS_Underlay_BGP_Neighbors
      direct_neighbor = find_direct_neighbors_for_BGP(device_id)
    elif context['view_type'] == 'VRF': 
      #find his direct neighbor from MS Overlay_L3_Tenants.xml
      direct_neighbor = find_direct_neighbors_for_VRF(device_id)
    else:
      MSA_API.task_error('TODO CONVERT PHP INTO PYTHON',context, True)
    
    if isinstance(direct_neighbor, dict):
      for link in direct_neighbor:
        neighbors.append(link)
        
    device['subtype'] = 'NETWORK'



  #existing_devices_id_msa[device['device_id']]['neighbors'] = neighbors
  device['links'] = neighbors


#Convert hash table into array for Topology view_name
nodes = []
for device_id, device in existing_devices_id_msa.items():

 #for i in range(8):
  node = {}
  #node["primary_key"]  = device_id+'_'+str(i)
  #node["name"]         = device['name']+'_'+str(i)
  #node["object_id"]    = device_id[3:]+'_'+str(i)
  node["primary_key"]  = device_id
  node["name"]         = device['name']
  node["object_id"]    = device_id[3:]
  node["x"]            = ""
  node["y"]            = ""
  node["description"]  = ""
  node["subtype"]      = device['subtype']
  node["image"]        = ""
  if device.get('status') and device['status'] == 'OK':
    node["color"]        = "#acd7e5"  #green
  else:
    node["color"]        = "#db2e14"  #red
  node["hidden"]       = 'false'
  node["cluster_id"]   = ""
  
  #if device.get('links'):
  #  links=[]
  #  for link in device['links']:
  #    links.append(link+'_'+str(i))
  #  device['links'] = links
    
    
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
context['existing_devices_name_msa_serialized']   = json.dumps(existing_devices_name_msa)
  
MSA_API.task_success('OPERATION ENDED, topology schema "' + context['view_name'] + '" updated',context, True)
   