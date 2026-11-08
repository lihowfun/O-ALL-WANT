# model-registry

Stores trained model versions and the per-model assignment that tells the
inference fleet which version to serve. Serving nodes poll the registry and
route requests locally with `src/rollout.py`.
