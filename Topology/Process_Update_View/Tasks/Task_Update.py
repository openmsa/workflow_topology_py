import time

from msa_sdk.msa_api import MSA_API
from msa_sdk.orchestration import Orchestration
from msa_sdk.order import Order
from msa_sdk.variables import Variables


def main():
    dev_var = Variables()
    # dev_var.add('cpes.0.cpe_sync_status', 'String')
    context = Variables.task_call(dev_var)
    orchestration = Orchestration(context['UBIQUBEID'])
    async_update_list = (context['PROCESSINSTANCEID'],
                         context['TASKID'], context['EXECNUMBER'])
    cpes = context.get('cpes')
    bar_length = 0
    position = 0

    for cpe in cpes:
        if cpe['cpe_prov_status'] == "SUCCESS":
            device_id = int(cpe.get('cpe')[3:])
            sychronize(device_id)
            bar_length += 1

    for cpe in cpes:
        if cpe['cpe_prov_status'] == "SUCCESS":
            pretty_formatted_bar = ['*'] * position + ['-'] * (bar_length - position)
            orchestration.update_asynchronous_task_details(
                *async_update_list, '[{}]'.format(''.join(pretty_formatted_bar))
            )
            device_id = int(cpe.get('cpe')[3:])
            sync_error = sync_status(device_id, orchestration, async_update_list)
            if sync_error:
                cpe['cpe_sync_status'] = f"FAILED: {sync_error}"
            else:
                cpe['cpe_sync_status'] = "SUCCESS"
            if position < bar_length:
                position += 1

    context.update(cpes=cpes)
    ret = MSA_API.process_content('ENDED', '', context, True)
    print(ret)


def sync_status(device_id, orchestration, async_update_list):
    """
    Poll synchronize status safely. Protects against missing keys like 'syncStatus' or 'message'.
    """
    order = Order(device_id)
    error_message = ''

    while True:
        status = order.get_synchronize_status()
        sync_status = status.get('syncStatus')

        if sync_status is None:
            # Defensive: unexpected response format
            error_message = f"No 'syncStatus' field. Full response: {status}"
            break

        if sync_status != 'RUNNING':
            # Either ENDED or some failure state
            if sync_status != 'ENDED':
                error_message = status.get(
                    'message',
                    f"No 'message' field. Full response: {status}"
                )
                orchestration.update_asynchronous_task_details(
                    *async_update_list, 'Import Config Failed'
                )
            break

        # Still running, wait and retry
        time.sleep(5)

    return error_message


def sychronize(device_id):
    order = Order(device_id)
    order.command_synchronize_async()


if __name__ == '__main__':
    main()
