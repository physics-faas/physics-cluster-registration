# physics-cluster-registration
Knative source to sink service to trigger steps upon cluster (OCM) registration

## Deploy

The steps to deploy it are:

* Create the namespace, sa, role and role binding:

```
oc apply -f deploy/001-namespace.yaml
oc apply -f deploy/002-rbac.yaml

```

* Deploy the sink application handling the events:

```
oc apply -f deploy/003-sink.yaml
```

  Note you need to change the container image by the one where your actual
  sink is located

* [optional] instead of deploying a normal Kubernetes service/deployment, there
  is an option to deploy a knative service too, so that the application is
  scaled to 0 when not used, since cluster registration is sporadic action and
  this could lead to saving resources

```
oc apply -f deploy/003b-sink.yaml
```

* Create the knative ApiServerSource by running the commant:

```
kn source apiserver physics-apiserversource \
  --namespace physics-cluster-registration \
  --mode "Resource" \
  --resource "ManagedCluster:v1" \
  --service-account physics-cr-sa \
  --sink http://cluster-registration.physics-cluster-registration.svc.cluster.local
```
