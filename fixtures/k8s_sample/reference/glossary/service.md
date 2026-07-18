---
title: "Service"
id: service
full_link: /docs/concepts/services-networking/service/
short_description: >
  An abstract way to expose an application running on a set of Pods.
tags:
- networking
- fundamental
---
 A Service is an abstract way to expose an application running on a set of
 {{< glossary_tooltip text="Pods" term_id="pod" >}}.

Services select Pods by using label {{< glossary_tooltip text="selectors" term_id="selector" >}}.
A Service may be exposed via a {{< glossary_tooltip text="NodePort" term_id="nodeport" >}},
{{< glossary_tooltip text="LoadBalancer" term_id="loadbalancer" >}}, or
{{< glossary_tooltip text="ClusterIP" term_id="clusterip" >}}.
