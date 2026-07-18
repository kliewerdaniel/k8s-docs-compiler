---
title: "Deployment"
id: deployment
full_link: /docs/concepts/workloads/controllers/deployment/
short_description: >
  A Deployment provides declarative updates for Pods and ReplicaSets.
tags:
- workload
- fundamental
---
 A Deployment provides declarative updates for {{< glossary_tooltip text="Pods" term_id="pod" >}}
 and {{< glossary_tooltip text="ReplicaSets" term_id="replicaset" >}}.

You describe a desired state in a Deployment, and the Deployment
{{< glossary_tooltip text="controller" term_id="controller" >}} changes the actual
state to the desired state. Deployments are the most common way to run
stateless applications.

## Exposing a Deployment with a Service

To make a Deployment reachable, create a {{< glossary_tooltip text="Service" term_id="service" >}}
and optionally an {{< glossary_tooltip text="Ingress" term_id="ingress" >}}.
