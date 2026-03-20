#!/bin/bash
# A1111 launch configuration
# Symlink or copy this to automatic1111/webui-user.sh after install

export MODELS_ROOT="/media/menser/fauna/image_gen/models"

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
