#!/bin/bash
set -e

REPO_ROOT="/media/menser/fauna/image_gen"
INSTALL_DIR="${REPO_ROOT}/automatic1111"

if [ -d "$INSTALL_DIR" ]; then
    echo "automatic1111/ already exists, skipping clone"
else
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui "$INSTALL_DIR"
fi

# Link our launch config
cp "${REPO_ROOT}/configs/a1111/webui-user.sh" "${INSTALL_DIR}/webui-user.sh"
chmod +x "${INSTALL_DIR}/webui-user.sh"

echo ""
echo "A1111 cloned. Launch config linked."
echo "First run sets up its own venv automatically."
echo "Run: cd ${INSTALL_DIR} && ./webui.sh"
