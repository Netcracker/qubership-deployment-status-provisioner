# Copyright 2024-2025 NetCracker Technology Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import time

from jsonpath_ng.ext import parse
from libraries import (
    DEFAULT_TIMEOUT,
    Condition,
    ConditionReason,
    ConditionType,
    CustomResource,
    KubernetesLibrary,
)


def get_resources_statuses(resources: str, kubernetes_library: KubernetesLibrary) -> []:
    timeout = int(os.getenv('POD_READINESS_TIMEOUT', DEFAULT_TIMEOUT))
    statuses = []
    resources_list = resources.split(',') if resources else []
    for resource in resources_list:
        resource = resource.strip()
        print(f'Processing [{resource}] resource')
        parts = resource.split()
        if len(parts) != 2:
            raise Exception(f'Resource description must contain 2 parts: type and name. But [{resource}] is received.')
        resource_type = parts[0].lower()
        resource_name = parts[1]
        start_time = time.time()
        message = f'[{resource_name}] component is not ready.'
        while start_time + timeout > time.time():
            if kubernetes_library.is_resource_ready(resource_type, resource_name):
                message = ''
                break
            time.sleep(5)
        statuses.append(message)
    return statuses


def get_custom_resources_statuses(custom_resources: str, kubernetes_library: KubernetesLibrary) -> []:
    timeout = int(os.getenv('CR_PROCESSING_TIMEOUT', DEFAULT_TIMEOUT))
    statuses = []
    resources_list = custom_resources.split(',') if custom_resources else []
    for resource in resources_list:
        resource = resource.strip()
        parts = resource.split()
        if len(parts) != 6 and len(parts) != 7:
            raise Exception(f'Resource description must contain 6 or 7 parts. But [{resource}] is received.')
        expression = parts[4]
        successful_condition = parts[5]
        failed_condition = parts[6] if len(parts) == 7 else None
        custom_resource = CustomResource(resource.split(expression)[0])
        print(f'Processing [{custom_resource}] custom resource')

        message = f'[{custom_resource}] custom resource does not have successful condition after {timeout} seconds.'
        jsonpath_expression = parse(expression)
        start_time = time.time()
        while start_time + timeout > time.time():
            cr = kubernetes_library.get_custom_resource(custom_resource)
            match = jsonpath_expression.find(cr)
            if match:
                if match[-1].value == successful_condition:
                    message = ''
                    break
                if failed_condition and match[-1].value == failed_condition:
                    message = (f'Processing status of [{custom_resource}] custom resource is {failed_condition}. '
                               f'For more details, check custom resource status.')
                    break
            time.sleep(5)
        statuses.append(message)
    return statuses


def get_integration_tests_status(integration_tests_resource: str, kubernetes_library: KubernetesLibrary) -> str:
    integration_tests_condition_reason = os.getenv('INTEGRATION_TESTS_CONDITION_REASON',
                                                   ConditionReason.INTEGRATION_TESTS_DEFAULT)
    integration_tests_successful_condition_type = os.getenv('INTEGRATION_TESTS_SUCCESSFUL_CONDITION_TYPE',
                                                            ConditionType.READY)
    integration_tests_timeout = int(os.getenv('INTEGRATION_TESTS_TIMEOUT', DEFAULT_TIMEOUT))

    resource = CustomResource(integration_tests_resource)
    print(f'Processing integration tests status from [{resource.name}] resource')
    start_time = time.time()
    while start_time + integration_tests_timeout > time.time():
        condition = kubernetes_library.get_custom_resource_status_condition(resource,
                                                                            integration_tests_condition_reason)
        if condition and condition.get('type') != ConditionType.IN_PROGRESS:
            return '' if condition.get('type') == integration_tests_successful_condition_type else condition.get(
                'message')
        time.sleep(5)
    return f'Integration tests have not completed in {integration_tests_timeout} seconds.'


if __name__ == '__main__':
    monitored_resources = os.getenv('MONITORED_RESOURCES')
    monitored_custom_resources = os.getenv('MONITORED_CUSTOM_RESOURCES')
    namespace = os.getenv('NAMESPACE')
    resource_to_set_status = os.getenv('RESOURCE_TO_SET_STATUS')
    treat_status_as_field = os.getenv('TREAT_STATUS_AS_FIELD', False)

    if (monitored_resources or monitored_custom_resources) and namespace and resource_to_set_status:
        condition_reason = os.getenv('CONDITION_REASON', ConditionReason.DEFAULT)
        successful_condition_type = os.getenv('SUCCESSFUL_CONDITION_TYPE', ConditionType.SUCCESSFUL)
        failed_condition_type = os.getenv('FAILED_CONDITION_TYPE', ConditionType.FAILED)

        kubernetes_library = KubernetesLibrary(namespace, resource_to_set_status)
        condition_library = Condition(condition_reason, successful_condition_type)

        successful_status_message = 'All components are in ready status.'

        # Update status condition with 'In Progress' state
        status_condition = condition_library.get_condition(ConditionType.IN_PROGRESS,
                                                           'Computing of cluster state is in progress')
        if treat_status_as_field:
            kubernetes_library.update_custom_resource_status_as_field(status_condition)
        else:
            kubernetes_library.update_custom_resource_status_condition(status_condition)

        # Calculates statuses of resources specified in MONITORED_RESOURCES parameter.
        received_statuses = get_resources_statuses(monitored_resources, kubernetes_library)

        # Calculates statuses of custom resources specified in MONITORED_CUSTOM_RESOURCES parameter.
        received_statuses.extend(get_custom_resources_statuses(monitored_custom_resources, kubernetes_library))

        # Receive the results of running integration tests
        integration_tests_resource = os.getenv('INTEGRATION_TESTS_RESOURCE')
        if integration_tests_resource:
            successful_status_message = f'{successful_status_message} Integration tests are successfully completed.'
            integration_tests_status = get_integration_tests_status(integration_tests_resource, kubernetes_library)
            received_statuses.append(integration_tests_status)

        # Update status condition with final state
        received_statuses = list(filter(None, received_statuses))
        print(f'Failed components statuses are {received_statuses}')
        condition_type = failed_condition_type if len(received_statuses) else successful_condition_type
        condition_message = ' '.join(received_statuses) if len(received_statuses) else successful_status_message
        status_condition = condition_library.get_condition(condition_type, condition_message)
        if treat_status_as_field:
            kubernetes_library.update_custom_resource_status_as_field(status_condition)
        else:
            kubernetes_library.update_custom_resource_status_condition(status_condition)
