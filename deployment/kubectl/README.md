# Deploying with kubectl

The YAML files inside this directory are examples to help you deply this application on a kubernetes cluster in a single pod with a dedicated Redis server inside the pod. The pod will have four containers running (just like the docker-compose based deployment) and there will be an ephemeral volume mount shared by the Flask app and the Celery worker.  

The application does not need to be deployed in a single pod, and can instead be deployed as a set of pods, though that is outside of the scope of this document.  In the case of a multi-pod deployment, see the "Other Deployment Structures" section below. 

**This document is intended to help beginners deploy on k8s for learning purposes.  Make sure you know how to deploy an application for production on a kubernetes cluster before you try to do this on anything outside of a controlled environment.  I am not a kubernetes expert, so if you need this guide, you're definitely not ready.**

## Testing/Example Cluster

I used the YAML files in this directory to bring up a deployment on my own test cluster, which is a single-master three-node K3s cluster running on Debian 10 vms which in turn are hosted by KVM on a Debian 10 bare metal, x86_64 server.  I used MetalLB as a load balancer and Traefik as an ingress controller, and used an external PowerDNS server to create A records that all point at the external IP assigned to the traefik LoadBalancer service by MetalLB.  My K3s server is version 1.17.

Kubernetes is complex and no two clusters are set up exactly the same, and many clusters are set up extremely differently.  These files are only a starting point, and you will need to know your own cluster.

### Creating the Deployment

I start with the assumption that you have a running kubernetes cluster and you have kubectl access to create services, deployments, and ingresses.  If not, K3s is a good place to start learning.

The deployment is in "latex-deployment.yaml"

You will likely not need to edit anything in this file.  If you do want to change the `app: latex` label to something else (to avoid naming collisions, etc), make sure you change it in all three places:
* in "latex-deployment.yaml" under `spec.selector.matchLabels`
* in "latex-deployment.yaml" under `spec.template.metadata.labels`
* in "latex-service.yaml" under `spec.selector`

To deploy to the default namespace:
```bash
kubectl apply -f latex-deployment.yaml
```

To deply to a custom namespace it is best to add a `namespace: <name_of_namespace>` to the `metadata` attributes, but can also be done with:
```bash
kuebctl apply -f latex-deployment.yaml --namespace=<name_of_namespace>
```

### Creating a Service
The "latex-service.yaml" file defines an internal ClusterIP service which points at the pod that contains the Flask application.  This is done through the label `app: latex` so if you changed that in the deployment, make sure you followed the instructions above and changed it here as well.

If you are using a cluster with a proper ingress controller set up, it is unlikely that you will need to change anything in this file.  If you do not have an ingress controller, you can define this as a NodePort to make it easily reachable for testing, but know that it isn't a long-term solution.  

Apply it with 
```bash
kubectl apply -f latex-service.yaml
```

If you didn't use the default namespace for the deployment, apply with your custom namespace.

### Creating an Ingress
An ingress object allows an ingress controller in the cluster to route L7 traffic to the intended service.

The "latex-ingress.yaml" file here creates a routing rule that anything going to "latex.example.com" (obviously you need to replace this with your own fully qualified domain name) as read from the HTTP headers gets sent to the `latex-internal-service` service on port 80.  

You will need to make sure that any clients using this service will resolve that FQDN to the external IP for your cluster's ingress controller (whether by a legitimate DNS record or by messing with the hosts file).

If your service is going to be exposed as a path on a different host, the ingress object configuration will allow you to do that.  [Refer to the official ingress documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/) to see how to do that.

```bash
kubectl apply -f latex-ingress.yaml
```

If you didn't use the default namespace for the deployment, apply with your custom namespace.

### Tearing it all down
If you want to remove these components, you can tear them down with `kubectl delete`.

```bash
kubectl delete -f latex-deployment.yaml
kubectl delete -f latex-service.yaml
kubectl delete -f latex-ingress.yaml
```


## Other Deployment Structures

If deciding to deploy the application in a structure different from the single-pod configuration shown in these YAML files, remember the following:

1. The `/working` directory in the Flask container and the Celery worker(s) needs to be shared, since the Flask app will read and write there and the worker will perform the compilation on those files
2. There can be multiple Flask containers and Celery workers, but only one Celery beat scheduler
3. The Flask containers, Celery workers, and Celery beat scheduler must all be using the same redis instance, and have the same INSTANCE_KEY environmental variable set (if you don't change the default you should be fine)
