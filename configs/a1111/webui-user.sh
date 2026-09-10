#!/bin/bash
# A1111 launch configuration
# Template — install_a1111.sh substitutes __REPO_ROOT__ when copying this to
# automatic1111/webui-user.sh.

export MODELS_ROOT="__REPO_ROOT__/models"

export COMMANDLINE_ARGS="
  --xformers
  --ckpt-dir ${MODELS_ROOT}/checkpoints
  --lora-dir ${MODELS_ROOT}/loras
  --vae-dir ${MODELS_ROOT}/vae
  --embeddings-dir ${MODELS_ROOT}/embeddings
  --controlnet-dir ${MODELS_ROOT}/controlnet
  --listen
  --port 7860
"
