import json
import time
import ipaddress
from msa_sdk.variables import Variables
from msa_sdk.msa_api import MSA_API


dev_var = Variables()


context = Variables.task_call(dev_var)


MSA_API.task_success('OPERATION ENDED', context, True)