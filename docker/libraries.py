from datetime import datetime

import kubernetes
import urllib3
from kubernetes.client import V1ComponentCondition, V1ComponentStatus

DEFAULT_TIMEOUT = '300'


class ConditionReason:
    DEFAULT = 'ServiceReadinessStatus'
    INTEGRATION_TESTS_DEFAULT = 'IntegrationTestsExecutionStatus'


class ConditionType:
    FAILED = 'Failed'
    IN_PROGRESS = 'In Progress'
    READY = 'Ready'
    SUCCESSFUL = 'Successful'


class ConditionStatus:
    FALSE = 'False'
    TRUE = 'True'


class CustomResource(object):

    def __init__(self, custom_resource: str):
        parts = custom_resource.strip().split()
        if len(parts) != 4:
            raise Exception(f'The description of specified resource must contain 4 parts: '
                            f'group, version, plural and name. But [{custom_resource}] is received.')
        self.group = parts[0]
        self.version = parts[1]
        self.plural = parts[2]
        self.name = parts[3]

    def __str__(self):
        return f'{self.group}/{self.version} {self.plural} {self.name}'


def get_kubernetes_api_client(config_file=None, context=None, persist_config=True):
    try:
        kubernetes.config.load_incluster_config()
        return kubernetes.client.ApiClient()
    except kubernetes.config.ConfigException:
        return kubernetes.config.new_client_from_config(config_file=config_file,
                                                        context=context,
                                                        persist_config=persist_config)


class KubernetesLibrary(object):

    def __init__(self,
                 namespace: str,
                 resource_to_set_status=None,
                 config_file=None,
                 context=None,
                 persist_config=True):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.k8s_api_client = get_kubernetes_api_client(config_file=config_file,
                                                        context=context,
                                                        persist_config=persist_config)
        self.k8s_apps_v1_client = kubernetes.client.AppsV1Api(self.k8s_api_client)
        self.k8s_batch_v1_client = kubernetes.client.BatchV1Api(self.k8s_api_client)
        self.custom_objects_api = kubernetes.client.CustomObjectsApi(self.k8s_api_client)
        self.namespace = namespace
        if resource_to_set_status:
            self.status_resource = CustomResource(resource_to_set_status)

    def delete_job(self, name):
        self.k8s_batch_v1_client.delete_namespaced_job(name, self.namespace, propagation_policy='Background')

    def is_resource_ready(self, resource_type: str, name: str) -> bool:
        if resource_type == 'daemonset':
            return self.is_daemon_set_ready(name)
        elif resource_type == 'deployment':
            return self.is_deployment_ready(name)
        elif resource_type == 'job':
            return self.is_job_succeeded(name)
        elif resource_type == 'statefulset':
            return self.is_stateful_set_ready(name)
        else:
            raise Exception(f'The type [{resource_type}] is not supported yet.')

    def is_daemon_set_ready(self, name: str) -> bool:
        daemon_set = self.k8s_apps_v1_client.read_namespaced_daemon_set_status(name, self.namespace)
        return (daemon_set.status.desired_number_scheduled == daemon_set.status.number_ready
                and daemon_set.status.desired_number_scheduled == daemon_set.status.updated_number_scheduled)

    def is_deployment_ready(self, name: str) -> bool:
        deployment = self.k8s_apps_v1_client.read_namespaced_deployment_status(name, self.namespace)
        return (deployment.status.replicas == deployment.status.ready_replicas
                and deployment.status.replicas == deployment.status.updated_replicas)

    def is_job_succeeded(self, name: str) -> bool:
        job = self.k8s_batch_v1_client.read_namespaced_job_status(name, self.namespace)
        return job.status.succeeded == 1

    def is_stateful_set_ready(self, name: str) -> bool:
        stateful_set = self.k8s_apps_v1_client.read_namespaced_stateful_set_status(name, self.namespace)
        return (stateful_set.status.replicas == stateful_set.status.ready_replicas
                and stateful_set.status.replicas == stateful_set.status.updated_replicas)

    def get_custom_resource(self, resource: CustomResource):
        return self.custom_objects_api.get_namespaced_custom_object(resource.group, resource.version, self.namespace,
                                                                    resource.plural, resource.name)

    def get_custom_resource_status_condition(self, resource: CustomResource, condition_reason: str) -> dict:
        resource_status = self.custom_objects_api.get_namespaced_custom_object_status(resource.group, resource.version,
                                                                                      self.namespace, resource.plural,
                                                                                      resource.name)
        conditions = resource_status['status'].get('conditions')
        if conditions:
            for i, condition in enumerate(conditions):
                if condition.get('reason') == condition_reason:
                    return condition
        return {}

    def update_custom_resource_status_condition(self, new_condition: dict):
        resource_status = self.custom_objects_api.get_namespaced_custom_object_status(self.status_resource.group,
                                                                                      self.status_resource.version,
                                                                                      self.namespace,
                                                                                      self.status_resource.plural,
                                                                                      self.status_resource.name)
        status = resource_status.get('status')
        if not status:
            status = {}
            resource_status['status'] = status
        conditions = status.get('conditions')
        if not conditions:
            conditions = []
        is_condition_found = False
        for i, condition in enumerate(conditions):
            if (condition.get('reason') == new_condition['reason']
                    or condition.get('reason') is None and condition.get('message') == new_condition['reason']):
                conditions[i] = new_condition
                is_condition_found = True
                break
        if not is_condition_found:
            conditions.append(new_condition)

        resource_status['status']['conditions'] = conditions
        self.custom_objects_api.patch_namespaced_custom_object_status(self.status_resource.group,
                                                                      self.status_resource.version,
                                                                      self.namespace,
                                                                      self.status_resource.plural,
                                                                      self.status_resource.name,
                                                                      resource_status)

    def update_custom_resource_status_as_field(self, new_condition: dict):
        custom_resource = self.custom_objects_api.get_namespaced_custom_object(self.status_resource.group,
                                                                               self.status_resource.version,
                                                                               self.namespace,
                                                                               self.status_resource.plural,
                                                                               self.status_resource.name)
        status = custom_resource.get('status', None)
        if status:
            conditions = status.get('conditions', [])
        else:
            conditions = []
        is_condition_found = False
        new_condition = V1ComponentCondition(
            type=new_condition['type'],
            status=new_condition['status'],
            message=new_condition['reason']
        )
        for i, condition in enumerate(conditions):
            if condition.get('message') == new_condition.message:
                conditions[i] = new_condition
                is_condition_found = True
                break
        if not is_condition_found:
            conditions.append(new_condition)

        status = V1ComponentStatus(conditions=conditions)
        custom_resource['status'] = status
        self.custom_objects_api.patch_namespaced_custom_object(self.status_resource.group,
                                                               self.status_resource.version,
                                                               self.namespace,
                                                               self.status_resource.plural,
                                                               self.status_resource.name,
                                                               custom_resource)


class Condition(object):

    def __init__(self, reason: str, successful_type):
        self.reason = reason
        self.successful_type = successful_type

    def get_condition(self, type: str, message: str):
        return {
            'type': type,
            'status': ConditionStatus.TRUE if type == self.successful_type else ConditionStatus.FALSE,
            'lastTransitionTime': datetime.utcnow().isoformat()[:-3] + 'Z',
            'reason': self.reason,
            'message': message
        }
