import json
import time
import ipaddress
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
#dev_var.add('view_name')
dev_var.add('view_type')

context = Variables.task_call(dev_var)

#if (context.get('view_type')):
#  context['view_name'] = context['view_name'] + '_' + context['view_type']


MSA_API.task_success('OPERATION ENDED',context, True)
