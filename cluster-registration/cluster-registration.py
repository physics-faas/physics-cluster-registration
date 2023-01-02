from cloudevents.http import from_http
from flask import Flask, request
from kubernetes import client, config

app = Flask(__name__)

EVENT_TYPES = ("dev.knative.apiserver.resource.add",)

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
            "namespace": "default"
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
                            "containerPort": 5000,
                            "name": "semantics",
                            "protocol": "TCP"
                        }],
                        "terminationMessagePath": "/dev/termination-log",
                        "terminationMessagePolicy": "File"
                    }],
                    "imagePullSecrets": [{"name": "jenkinssecretregistry"}],
                    #"serviceAccountName": "semantic"
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
            "namespace": "default"
            },
        "spec": {
            "ports": [{
                "name": "semanticsef",
                "port": 5000,
                "protocol": "TCP",
                "targetPort": 5000
            }],
            "selector": {"app": "service-semantics"},
            "type": "ClusterIP"
        }
    }

    return {
        "apiVersion": "work.open-cluster-management.io/v1",
        "kind": "ManifestWork",
        "metadata": {"name": "cluster-registration"},
        "spec": {
            "workload": {
                "manifests": [
                    physics_semantic_pod,
                    physics_semantic_svc
                ]
            }
        }
    }


# create an endpoint at http://localhost:/8080/
@app.route("/", methods=["POST"])
def home():
    # create a CloudEvent
    event = from_http(request.headers, request.get_data())

    # we are only interested on the omboarding of new clusters,
    # not in the updates or removal
    event_type = event['type']
    print("The event type is %s", event_type)

    if event_type not in EVENT_TYPES:
       return "", 204

    cluster_name = event['name']
    print("Cluster name is %s", cluster_name)

    deploy_manifest_work(namespace=cluster_name)

    # print("The service IP is {}", service_ip)

    return "", 204

    # List of steps
    # filter by event type (only "add" event is needed)
    # Get the name of the cluster
    # create a manifestwork on the cluster name namespace
    # get the service ip (in a loop) from the manifestwork status
    # query the RF with the cluster name and service IP


if __name__ == "__main__":
    app.run(port=8080)
