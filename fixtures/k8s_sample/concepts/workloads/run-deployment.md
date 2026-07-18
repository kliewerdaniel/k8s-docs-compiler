---
title: "Deployments"
weight: 20
description: >
  How to run stateless applications using Deployments and expose them with Services.
---
# Deployments

A {{< glossary_tooltip text="Deployment" term_id="deployment" >}} runs your application
as a set of identical {{< glossary_tooltip text="Pods" term_id="pod" >}}.

## Expose a Deployment with a Service and Ingress

1. Create a Deployment.
2. Create a {{< glossary_tooltip text="Service" term_id="service" >}} selecting the Pods.
3. Optionally create an {{< glossary_tooltip text="Ingress" term_id="ingress" >}} to route
   external traffic to the Service.

See [Services](/docs/concepts/services-networking/service/) for details.
