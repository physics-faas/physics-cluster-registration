import logging
import os
import requests
import time

from cloudevents.http import from_http
from flask import Flask, request
from kubernetes import client, config


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

EVENT_TYPES = ("dev.knative.apiserver.resource.add",)
SERVICE_PORT = 5000
SERVICE_NAMESPACE = "open-cluster-management-agent"
SERVICE_ACCOUNT = "klusterlet-work-sa"
PULL_SECRET = "physics-harbor-pullsecret"
MANIFEST_WORK_SEMANTICS = "cluster-registration-semantics"
MANIFEST_WORK_ENERGY = "cluster-registration-energy"
ENERGY_JOB = 'energy-semantics'
SEMANTIC_SERVICE = 'service-semantics'


def deploy_manifest_work(namespace, manifest_type):
    # config.load_kube_config()
    config.load_incluster_config()

    if manifest_type == MANIFEST_WORK_SEMANTICS:
        manifest_work = create_semantics_manifest_work()
    elif manifest_type == MANIFEST_WORK_ENERGY:
        manifest_work = create_energy_manifest_work()
    else:
        # Unknown manifest
        return

    api = client.CustomObjectsApi()
    api.create_namespaced_custom_object(
        group="work.open-cluster-management.io",
        version="v1",
        namespace=namespace,
        plural="manifestworks",
        body=manifest_work,
    )


def create_energy_manifest_work():
    physics_energy_pod = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": ENERGY_JOB,
            "namespace": SERVICE_NAMESPACE
        },
        "spec": {
            "parallelism": 3,
            "completions": 3,
            "template": {
                "metadata": {
                    "name": ENERGY_JOB
                },
                "spec": {
                    "containers": [
                    {
                        "name": ENERGY_JOB,
                        "image": "progrium/stress",
                        "command": ["sh", "-c"],
                        "args": ["stress --cpu 4 --vm-bytes 512M --vm-keep -t 180s"],
                        "resources": {
                            "limits": {
                                "cpu": "1",
                                "memory": "1Gi"
                            },
                            "requests": {
                                "cpu": "0.5",
                                "memory": "512Mi"
                            }
                        }
                    }],
                    "restartPolicy": "OnFailure"
                }
            }
        }
    }

    physics_energy_r_id = {
        "group": "batch",
        "name": ENERGY_JOB,
        "namespace": SERVICE_NAMESPACE,
        "resource": "jobs",
        "version": "v1"
    }
    physics_energy_feedback = {
        "type": "JSONPaths",
        "jsonPaths": [{
            "name": "jobCompleted",
            "path": ".status.completionTime"
        }]
    }

    return {
        "apiVersion": "work.open-cluster-management.io/v1",
        "kind": "ManifestWork",
        "metadata": {"name": MANIFEST_WORK_ENERGY},
        "spec": {
            "manifestConfigs": [{
                "resourceIdentifier": physics_energy_r_id,
                "feedbackRules": [physics_energy_feedback]
            }],
            "workload": {
                "manifests": [
                    physics_energy_pod
                ]
            }
        }
    }


def create_semantics_manifest_work():
    # TODO: Change by actual pod
    physics_semantic_pod = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "labels": {"app": SEMANTIC_SERVICE},
            "name": SEMANTIC_SERVICE,
            "namespace": SERVICE_NAMESPACE
            },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {"app": SEMANTIC_SERVICE}
            },
            "strategy": {"type": "Recreate"},
            "template": {
                "metadata": {
                    "labels": {"app": SEMANTIC_SERVICE}
                },
                "spec": {
                    "containers": [{
                        "env": [
                            {"name": "TIME", "value": "August-31-22-20-22-50"},
                            {"name": "SEMANTICS-BLOCK-URL", "value": "https://service-semantics.apps.ocphub.physics-faas.eu"}
                        ],
                        "image": "registry.apps.ocphub.physics-faas.eu/wp5/service-semantics:latest",
                        "name": SEMANTIC_SERVICE,
                        "ports": [{
                            "containerPort": SERVICE_PORT,
                            "name": "semantics",
                            "protocol": "TCP"
                        }],
                        "terminationMessagePath": "/dev/termination-log",
                        "terminationMessagePolicy": "File"
                    }],
                    "imagePullSecrets": [{"name": PULL_SECRET}],
                    "serviceAccountName": SERVICE_ACCOUNT
                }
            }
        }
    }

    physics_semantic_svc = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "labels": {"app": SEMANTIC_SERVICE},
            "name": SEMANTIC_SERVICE,
            "namespace": SERVICE_NAMESPACE
            },
        "spec": {
            "ports": [{
                "name": "semanticsef",
                "port": SERVICE_PORT,
                "protocol": "TCP",
                "targetPort": SERVICE_PORT
            }],
            "selector": {"app": SEMANTIC_SERVICE},
            "type": "ClusterIP"
        }
    }

    physics_semantic_r_id_1 = {
        "group": "",
        "name": SEMANTIC_SERVICE,
        "namespace": SERVICE_NAMESPACE,
        "resource": "services",
        "version": "v1"
    }
    physics_semantic_feedback_1 = {
        "type": "JSONPaths",
        "jsonPaths": [{
            "name": "serviceIP",
            "path": ".spec.clusterIP"
        }]
    }

    physics_semantic_r_id_2 = {
        "group": "apps",
        "name": SEMANTIC_SERVICE,
        "namespace": SERVICE_NAMESPACE,
        "resource": "deployments",
        "version": "v1"
    }
    physics_semantic_feedback_2 = {
        "type": "JSONPaths",
        "jsonPaths": [{
            "name": "deploymentStatus",
            "path": ".status.readyReplicas"
        }]
    }

    return {
        "apiVersion": "work.open-cluster-management.io/v1",
        "kind": "ManifestWork",
        "metadata": {"name": MANIFEST_WORK_SEMANTICS},
        "spec": {
            "manifestConfigs": [{
                "resourceIdentifier": physics_semantic_r_id_1,
                "feedbackRules": [physics_semantic_feedback_1]
            },
            {
                "resourceIdentifier": physics_semantic_r_id_2,
                "feedbackRules": [physics_semantic_feedback_2]
            }],
            "workload": {
                "manifests": [
                    physics_semantic_pod,
                    physics_semantic_svc
                ]
            }
        }
    }


def get_manifest_work_status(namespace, manifest_name):
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    return api.get_namespaced_custom_object_status(
        group="work.open-cluster-management.io",
        version="v1",
        namespace=namespace,
        plural="manifestworks",
        name=manifest_name)


def deploy_semantic_component(cluster_name):
    # create a manifestwork on the cluster name namespace
    deploy_manifest_work(cluster_name, MANIFEST_WORK_SEMANTICS)

    # get the service ip (in a loop) from the manifestwork status
    retries = 5
    service_ip = None
    deployment_ready = False
    while retries:
        manifest_work_status = get_manifest_work_status(cluster_name, MANIFEST_WORK_SEMANTICS)
        if manifest_work_status.get('status'):
            manifests = manifest_work_status['status']['resourceStatus'].get('manifests', [])
            for manifest in manifests:
                status_feedback = manifest.get('statusFeedback')
                if status_feedback:
                    for value in status_feedback['values']:
                        if value['name'] == 'serviceIP':
                            service_ip = value['fieldValue']['string']
                            break
                        if value['name'] == 'deploymentStatus':
                            if value['fieldValue']['integer'] == 1:
                                deployment_ready = True
                if service_ip and deployment_ready:
                    break
        if service_ip and deployment_ready:
            break
        retries-=1
        time.sleep(5)
    return service_ip


def deploy_energy_bench(cluster_name):
    deploy_manifest_work(cluster_name, MANIFEST_WORK_ENERGY)

    # Wait until Job finishes or 5 mins
    retries = 20
    completed = False
    while retries:
        manifest_work_status = get_manifest_work_status(cluster_name, MANIFEST_WORK_ENERGY)
        if manifest_work_status.get('status'):
            manifests = manifest_work_status['status']['resourceStatus'].get('manifests', [])
            for manifest in manifests:
                status_feedback = manifest.get('statusFeedback')
                if status_feedback:
                    for value in status_feedback['values']:
                        if value['name'] == "jobCompleted":
                            completed = True
                            break
                if completed:
                    break
        if completed:
            break
        retries-=1
        time.sleep(15)
    if completed:
        return True
    return False


# create an endpoint at http://localhost:/8080/
@app.route("/", methods=["POST"])
def home():
    # create a CloudEvent
    event = from_http(request.headers, request.get_data())

    # we are only interested on the omboarding of new clusters,
    # not in the updates or removal
    event_type = event['type']
    app.logger.info('The event type is %s', event_type)

    # filter by event type (only "add" event is needed)
    if event_type not in EVENT_TYPES:
       return "", 202

    # Get the name of the cluster
    cluster_name = event['name']
    app.logger.info('Cluster name is %s', cluster_name)

    # Steps:
    # 1. Deploy energy bench and wait for execution completion
    success = deploy_energy_bench(cluster_name)
    if not success:
        app.logger.error('Something went wrong while deploying the job to '
                         'measure performance/energy')
        return "TimeOut wating for Job completion", 500

    # 2. Deploy the semantic component, with information about the energy bench
    service_ip = deploy_semantic_component(cluster_name)

    if not service_ip:
        return "TimeOut waiting for Service IP", 500

    app.logger.info('The service IP is %s', service_ip)
    app.logger.info('The service PORT is %s', SERVICE_PORT)

    # 3. Call the Semantic Component with the information about the pod
    energy_label = 'job-name={}'.format(ENERGY_JOB)
    pod_info = {
        'pod_label': energy_label,
    }
    url = "http://{}:{}/kubemantics-trigger".format(service_ip, SERVICE_PORT)
    x = requests.post(url, json=pod_info)
    app.logger.info('The call to Semantic Component to pass the pod label information got: %s', x.text)

    # 4. Call the RF with the information about the semantic service (IP)
    headers = {'X-API-Key': os.environ['RF_API_KEY']}
    cluster_info = {
        'clusterName': cluster_name,
        'serviceIP': "{}:{}".format(service_ip, SERVICE_PORT)
    }
    x = requests.post(os.environ['RF_API_URL'], headers=headers, json=cluster_info)
    app.logger.info('The call to RF got: %s', x.text)

    return "", 204


if __name__ == "__main__":
    app.run(port=8080)
