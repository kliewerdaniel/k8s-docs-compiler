---
title: "Pod"
id: pod
full_link: /docs/concepts/workloads/pods/
short_description: >
  A Pod represents a set of running containers in your cluster.
tags:
- core-object
- fundamental
---
 The smallest and simplest Kubernetes object. A Pod represents a set of running
 {{< glossary_tooltip text="containers" term_id="container" >}} on your cluster.

A Pod is typically set up to run a single primary container. It can also run
optional {{< glossary_tooltip text="sidecar" term_id="sidecar" >}} containers that
add supplementary features like logging. Pods are commonly managed by a
{{< glossary_tooltip text="Deployment" term_id="deployment" >}}.

{{< note >}}Pods are ephemeral; do not store state you cannot recreate.{{< /note >}}
