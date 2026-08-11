# Local Docker port policy

This policy applies only to generated local Docker environments. It does not
change container-internal ports or Kubernetes Service ports.

## Rules

1. Services use their standard container ports: PostgreSQL `5432`, Redis
   `6379` (or cluster `7000`-series), RabbitMQ `5672` and `15672`, FastAPI
   `8000`, and Airflow `8080`.
2. Containers communicate through Compose service names and container ports,
   never host ports.
3. Published host ports bind to `127.0.0.1` by default. Set
   `LOCAL_BIND_ADDRESS` explicitly only when LAN access is intended.
4. A Blueprint may declare `tooling.local_environment.host_port_base`. It must
   be a 100-port boundary in the IANA dynamic/private range `49152-65400`.
5. Within that block: application `+00`, PostgreSQL `+10`, RabbitMQ AMQP
   `+30`, RabbitMQ management `+31`, and Airflow `+40`.

For example, a base of `49300` publishes the application on `49300`,
PostgreSQL on `49310`, RabbitMQ on `49330`/`49331`, and Airflow on `49340`.
The individual environment variables remain override points for a one-off
debugging session.

## Why

IANA reserves `49152-65535` as dynamic/private ports; AutoForge uses a bounded
part of that range for local-only mappings. Docker Compose creates an isolated
network where services resolve each other by service name, so publishing a
database or broker is not required for container-to-container traffic.

Kubernetes is separate: use `ClusterIP` for internal communication and an
Ingress, Gateway, or LoadBalancer for external traffic. Do not generate
`hostPort`; it restricts scheduling and is not a scaling primitive.

Sources: [IANA port registry](https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml), [Docker Compose networking](https://docs.docker.com/compose/how-tos/networking/), [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/), and [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/).
