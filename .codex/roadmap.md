# AutoForge Roadmap

## Completed foundations

- specification and generation contracts
- FastAPI project/module/model/router generation
- Workspace and validation pipeline
- Plugin architecture
- PostgreSQL database generation
- Redis and RabbitMQ foundations
- Transactional Outbox
- EventBus and Pipeline
- durable GenerationJob worker model
- Git checkout/branch/commit/push/Pull Request automation
- Control Plane and Worker execution
- GitHub webhook ingestion
- GitHub Actions/Jenkins validation configuration

## Active

### Docker build

- [x] build-only responsibility contract
- [ ] minimal Dockerfile Generator
- [ ] generated-project Docker build verification

## Later

- [ ] additional database providers such as MySQL
- [ ] remaining managed Redis deployment contracts
- [ ] WebSocket/additional service blueprints
- [ ] Metrics Handler
- [ ] artifact publishing
- [ ] deployment plugins
- [ ] additional infrastructure/cloud automation
- [ ] AI specification assistance
- [ ] AI code-generation assistance
- [ ] dashboard/distributed-worker enhancements
- [ ] plugin marketplace

Implement one bounded contract at a time.
Do not create empty future architecture merely to represent roadmap items.