# Qubership Deployment Status Provisioner

This guide provides information about the usage of the Qubership Deployment Status Provisioner.

Topics covered in this section:

<!-- TOC -->
* [Qubership Deployment Status Provisioner](#qubership-deployment-status-provisioner)
* [Overview](#overview)
* [Common information](#common-information)
* [Usage](#usage)
* [Example](#example)
<!-- TOC -->

# Overview

Deployment Status Provisioner is a component for providing the overall service status in Deployer jobs.

![status-provisioner](/documentation/images/status-provisioner.drawio.png)

# Common information

`Deployment Status Provisioner` is a component for providing the overall service status of deployment procedure for operator-less services. It is
used to receive statuses from all required service resources and specify the final result to a preselected resource from
where the Deployers read the status.

First of all, `Deployment Status Provisioner` checks readiness status of resources specified in `MONITORED_RESOURCES`
parameter. If all resources are successfully started, the status condition displays the following message:

```
All components are in ready status.
```

If some resources are not started in the allotted time, status condition contains `RESOURCE_NAME component is not ready`
message for each unready resource, where `RESOURCE_NAME` is the name of monitored resource.

Then `Deployment Status Provisioner` checks the result of integration tests if it is necessary. If the integration tests
fail, the status condition outputs a message from the `INTEGRATION_TESTS_RESOURCE` status. If they do not complete in
the allotted time, you will see `Integration tests have not completed in INTEGRATION_TESTS_TIMEOUT seconds` message
in the status condition. If the integration tests complete successfully, the status condition displays
`Integration tests are successfully completed` message.

You also can find information about monitored resources and array with failed resources in the pod logs.

# Usage

To use `Deployment Status Provisioner` you need to create a resource inside your Helm chart, which creates Pod with the
latest image of `Deployment Status Provisioner` and the following parameters:

The `INITIAL_WAIT` parameter specifies the time in seconds that the `Deployment Status Provisioner` waits before starting
to check readiness status for monitored components. It is important for `upgrade` process. The default value is `30`.

The `MONITORED_RESOURCES` parameter specifies the comma-separated list of resources that should be monitored by
`Deployment Status Provisioner`. Each resource description should consist of **two** parts separated by space: resource
kind and its name. There is ability to monitor readiness status only for the following resource kinds:

* `DaemonSet`
* `Deployment`
* `Job`
* `StatefulSet`

For example, if you have Stateful Set with name `consul-server`, its description should look like `StatefulSet consul-server`.
A complete example for this parameter would be `Deployment consul-backup-daemon, DaemonSet consul, StatefulSet consul-server, Job consul-server-acl-init`.
This parameter is mandatory and does not have default value.

The `MONITORED_CUSTOM_RESOURCES` parameter specifies the comma-separated list of custom resources that should be monitored by `Deployment Status Provisioner`. Each resource description should consist of **six** or **seven** parts separated by space:

* `group` is the group of custom resource. It is required. For example, `qubership.org`.
* `version` is the version of custom resource. It is required. For example, `v1`.
* `plural` is the custom resource's plural name. It is required. For example, `opensearchservices`.
* `name` is the custom resource's name. It is required. For example, `opensearch`.
* `expression` is the JSONPath (query language for JSON) expression to get custom resource status. It is required. For example, you need to get `type` field value from the following custom resource status if `reason` field is equal to `ReconcileCycleStatus`:

  ```yaml
  status:
    conditions:
      - lastTransitionTime: 2024-02-27 10:06:13.746985042 +0000 UTC m=+199.958634385
        message: The deployment readiness status check is successful
        reason: ReconcileCycleStatus
        status: 'True'
        type: Successful
      - lastTransitionTime: 2024-02-27 10:06:08.714381731 +0000 UTC m=+194.926031082
        message: Component pods are ready
        reason: ComponentReadinessStatus
        status: 'True'
        type: Ready
    disasterRecoveryStatus:
      mode: ''
      status: ''
  ```

  In that case required expression looks like `$.status.conditions[?(@.reason=='ReconcileCycleStatus')].type`. If you need to get status from a specific field (for example, `component.status`) in the following custom resource:

  ```
  apiVersion: qubership.org/v1
  kind: ComponentService
  metadata:
    creationTimestamp: '2024-02-27T10:02:51Z'
    generation: 1
    name: component
    namespace: component-service
  spec:
    global:
      podReadinessTimeout: 700
      waitForPodsReady: true
    component:
      replicas: 3
      resources:
        limits:
          cpu: 500m
          memory: 1024Mi
        requests:
          cpu: 100m
          memory: 1024Mi
      status: Success
  ```

  you can specify `$.spec.component.status` expression. For more information, refer to [Python JSONPath Next-Generation](https://github.com/h2non/jsonpath-ng/blob/master/README.rst).

* `successful condition` is the value that should be considered as successfully processed custom resource. It is required. For example, `Successful`.
* `failed condition` is the value that should be considered as inability to process the custom resource. It is optional. If it is not specified, `Deployment Status Provisioner` will try to find `successful condition` before time runs out (`CR_PROCESSING_TIMEOUT`). For example, `Failed`.

A complete example for this parameter would be as follows: 

```
qubership.org v1 opensearchservices opensearch $.status.conditions[?(@.reason=='ReconcileCycleStatus')].type Successful Failed, qubership.org v1 customservices name $.spec.status.type Ready
```

The `RESOURCE_TO_SET_STATUS` parameter specifies the characteristics of the resource to set the final status of the cluster.
This parameter value should consist of **four** parts separated by space: resource group, version, plural and its name.
For example, if you want to write down the status to `Job` named `consul-status-provisioner`, the value should look
like `batch v1 jobs consul-status-provisioner`.
This parameter is mandatory and does not have default value.

The `NAMESPACE` parameter specifies the namespace in OpenShift/Kubernetes where all the monitored resources and resource
to set status are located. This parameter is mandatory and does not have default value.

The `CONDITION_REASON` parameter specifies the name of the condition reason that is used when setting the status condition
for the `RESOURCE_TO_SET_STATUS` resource. For example, `ConsulServiceReadinessStatus`. The default value is `ServiceReadinessStatus`.

The `SUCCESSFUL_CONDITION_TYPE` parameter specifies the condition type that is used when setting the successful status
condition for the `RESOURCE_TO_SET_STATUS` resource. For example, `Success`. The default value is `Successful`.

The `FAILED_CONDITION_TYPE` parameter specifies the condition type that is used when setting the failed status condition
for the `RESOURCE_TO_SET_STATUS` resource. For example, `Fail`. The default value is `Failed`.

The `POD_READINESS_TIMEOUT` parameter specifies the timeout in seconds that the `Deployment Status Provisioner` waits for
each of the monitored resources to be ready or completed. The default value is `300`.

The `CR_PROCESSING_TIMEOUT` parameter specifies the timeout in seconds the `Deployment Status Provisioner` waits for each of the monitored custom resources to have `successful` or `failed` status. The default value is `300`.

The `INTEGRATION_TESTS_RESOURCE` parameter specifies the characteristics of the resource which the status of
integration tests execution is stored in. This parameter value should consist of **four** parts separated by space:
resource group, version, plural and its name. For example, if you want to read the integration tests status from `Deployment`
named `consul-integration-tests-runner`, the value should look like `apps v1 deployments consul-integration-tests-runner`.
This parameter should be specified only if you want the result of the integration tests to get inside the final cluster
status. 

The `INTEGRATION_TESTS_CONDITION_REASON` parameter specifies the name of the condition reason which meets the condition
with the result of the integration tests in the `INTEGRATION_TESTS_RESOURCE` resource. The default value is `IntegrationTestsExecutionStatus`.
This parameter is meaningless without `INTEGRATION_TESTS_RESOURCE` parameter.

The `INTEGRATION_TESTS_SUCCESSFUL_CONDITION_TYPE` parameter specifies the condition type which corresponds to the successful
result of the integration tests in the status condition of the `INTEGRATION_TESTS_RESOURCE` resource. The default value
is `Ready`.
This parameter is meaningless without `INTEGRATION_TESTS_RESOURCE` parameter.

The `INTEGRATION_TESTS_TIMEOUT` parameter specifies the timeout in seconds that the `Deployment Status Provisioner` waits for
successful or failed status condition in the `INTEGRATION_TESTS_RESOURCE` resource. The default value is `300`.
This parameter is meaningless without `INTEGRATION_TESTS_RESOURCE` parameter.

The `TREAT_STATUS_AS_FIELD` parameter specifies whether resource status should be treated as field. It is necessary when initially `RESOURCE_TO_SET_STATUS` does not have `Status` sub-resource. In that case status is set as a field to chosen resource. For example, it may be applicable for some of custom resources. The default value
is `False`.

# Example

`Deployment Status Provisioner` job with only required environment variables looks like the follows:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: my-status-provisioner
  labels:
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  template:
    metadata:
      name: my-status-provisioner
      labels:
        component: status-provisioner
    spec:
      restartPolicy: Never
      serviceAccountName: my-status-provisioner
      containers:
        - name: status-provisioner
          image: ghcr.io/netcracker/deployment-status-provisioner:main
          imagePullPolicy: "Always"
          env:
            - name: NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: MONITORED_RESOURCES
              value: "Deployment backup-daemon, StatefulSet server, Job server-acl-init"
            - name: RESOURCE_TO_SET_STATUS
              value: "batch v1 jobs my-status-provisioner"
          resources:
            requests:
              memory: "50Mi"
              cpu: "50m"
            limits:
              memory: "50Mi"
              cpu: "50m"
```

You should also create `Service Account`, `Role Binding` and `Role` with permissions that allow `Deployment Status Provisioner`
to work with your monitored resources.

`Deployment Status Provisioner` role should allow to `get` statuses for all resources that are specified in the `MONITORED_RESOURCES`
parameter. In addition, the role should give permissions to `get` and `patch` status for the resource from `RESOURCE_TO_SET_STATUS`
parameter. So, according to the configured `Deployment Status Provisioner` job, the role should look like this:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-status-provisioner
rules:
  - apiGroups:
      - apps
    resources:
      - deployments/status
      - statefulsets/status
    verbs:
      - get
  - apiGroups:
      - batch
    resources:
      - jobs/status
    verbs:
      - get
      - patch
```

And the following `deployment-configuration.json` can be used:
```yaml
{
  "statusPolling":{
    "resourceType": "job.batch",
    "resourceName": "my-status-provisioner",
    "statusPath": "$.status.conditions[?(@.type=='Successful')]",
    "statusPathFail": "$.status.conditions[?(@.type=='Failed')]",
    "timeout": "${ CUSTOM_TIMEOUT_MIN ? CUSTOM_TIMEOUT_MIN : '10' }"
  }
}
```

The example of status subresource:
```yaml
status:
  conditions:
    - lastTransitionTime: 2023-10-31 07:45:28.487195606 +0000 UTC m=+74.412108827
      message: The deployment readiness status check is successful
      reason: ServiceReadinessStatus
      status: 'True'
      type: Successful
```

A complete example can be found in [Consul Service Templates](https://github.com/Netcracker/consul-service/tree/main/charts/helm/consul-service/templates/status-provisioner).
