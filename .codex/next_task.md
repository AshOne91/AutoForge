# Next Task

## Next executable unit: prove the regenerated KIS Redis failover boundary

Run the maintained KIS Redis failover verifier against the fresh HA generation.
Prove Redis Cluster slot coverage, replica promotion, data continuity, old-master
rejoin, and application health without calling the live KIS API. Honor generated
external-network prerequisites and remove disposable resources after the drill.
