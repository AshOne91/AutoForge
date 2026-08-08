# Event and pipeline architecture

- Target flow: producer -> EventBus -> typed handler -> result event. EventBus must not know Git, plugins, generators, or pipeline business rules.
- In-process EventBus is generic asynchronous dispatch; RabbitMQ is durable cross-process transport and does not replace EventBus.
- Pipeline coordinates explicit task sequencing and failure policy; handler registration order must never define workflow order.
- Primary layers: CLI; Application orchestration; Core contracts/models/events/tasks; Services (generation, validation, workspace, build, Git); Infrastructure adapters.
- Plugins extend validated generation/validation capabilities; they are not mandatory for the first generator.