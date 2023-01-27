import logging
import requests
import time

from cloudevents.http import from_http
from flask import Flask, request
from kubernetes import client, config


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

EVENT_TYPES = ("dev.knative.apiserver.resource.add",)
MANIFEST_WORK_NAME = "cluster-registration"
SERVICE_IP = "serviceIP"
SERVICE_PORT = 5000
SERVICE_NAMESPACE="open-cluster-management-agent"
SERVICE_ACCOUNT="klusterlet-work-sa"
PULL_SECRET="physics-harbor-pullsecret"
RF_URL="172.30.235.166:5000/api/v2/cluster/register"

def deploy_manifest_work(namespace):
    #config.load_kube_config()
    config.load_incluster_config()
    manifest_work = create_manifest_work()

    api = client.CustomObjectsApi()
    api.create_namespaced_custom_object(
        group="work.open-cluster-management.io",
        version="v1",
        namespace=namespace,
        plural="manifestworks",
        body=manifest_work,
    )

def create_manifest_work():
    # TODO: Change by actual pod
    physics_semantic_pod = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "labels": {"app": "service-semantics"},
            "name": "service-semantics",
            "namespace": SERVICE_NAMESPACE
            },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {"app": "service-semantics"}
            },
            "strategy": {"type": "Recreate"},
            "template": {
                "metadata": {
                    "labels": {"app": "service-semantics"}
                },
                "spec": {
                    "containers": [{
                        "env": [
                            {"name": "TIME", "value": "August-31-22-20-22-50"},
                            {"name": "SEMANTICS-BLOCK-URL", "value": "https://service-semantics.apps.ocphub.physics-faas.eu"}
                        ],
                        "image": "registry.apps.ocphub.physics-faas.eu/wp5/service-semantics:latest",
                        "name": "service-semantics",
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
            "labels": {"app": "service-semantics"},
            "name": "service-semantics",
            "namespace": SERVICE_NAMESPACE
            },
        "spec": {
            "ports": [{
                "name": "semanticsef",
                "port": SERVICE_PORT,
                "protocol": "TCP",
                "targetPort": SERVICE_PORT
            }],
            "selector": {"app": "service-semantics"},
            "type": "ClusterIP"
        }
    }

    physics_semantic_r_id = {
        "group": "",
        "name": "service-semantics",
        "namespace": SERVICE_NAMESPACE,
        "resource": "services",
        "version": "v1"
    }
    physics_semantic_feedback = {
        "type": "JSONPaths",
        "jsonPaths": [{
            "name": "serviceIP",
            "path": ".spec.clusterIP"
        }]
    }
    
    return {
        "apiVersion": "work.open-cluster-management.io/v1",
        "kind": "ManifestWork",
        "metadata": {"name": MANIFEST_WORK_NAME},
        "spec": {
            "manifestConfigs": [{
                "resourceIdentifier": physics_semantic_r_id,
                "feedbackRules": [physics_semantic_feedback]
            }],
            "workload": {
                "manifests": [
                    physics_semantic_pod,
                    physics_semantic_svc
                ]
            }
        }
    }

def get_manifest_work_status(namespace):
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    return api.get_namespaced_custom_object_status(
        group="work.open-cluster-management.io",
        version="v1",
        namespace=namespace,
        plural="manifestworks",
        name=MANIFEST_WORK_NAME)

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
       return "", 204

    # Get the name of the cluster
    cluster_name = event['name']
    app.logger.info('Cluster name is %s', cluster_name)

    # create a manifestwork on the cluster name namespace
    deploy_manifest_work(namespace=cluster_name)

    # get the service ip (in a loop) from the manifestwork status
    retries = 5
    service_ip = None
    while retries:
        manifest_work_status = get_manifest_work_status(namespace=cluster_name)
        if manifest_work_status.get('status'):
            manifests = manifest_work_status['status']['resourceStatus'].get('manifests', [])
            for manifest in manifests:
                status_feedback = manifest.get('statusFeedback')
                if status_feedback:
                    for value in status_feedback['values']:
                        if value['name'] == SERVICE_IP:
                            service_ip = value['fieldValue']['string']
                            break
                if service_ip:
                    break
        if service_ip:
            app.logger.info('The service IP is %s', service_ip)
            app.logger.info('The service PORT is %s', SERVICE_PORT)
            break
        retries-=1
        time.sleep(5)

    # query the RF with the cluster name and service IP
    cluster_info = {
        'clusterName': cluster_name,
        'serviceIP': "{}:{}".format(service_ip, SERVICE_PORT)
    }
    x = requests.post(RF_URL, json=cluster_info)
    app.logger.info('The call to RF got: %s', x.text)

    return "", 204


if __name__ == "__main__":
    app.run(port=8080)
