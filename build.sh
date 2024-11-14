DOCKER_FILE="docker/Dockerfile"

echo "Build deployment status provisioner image"
for docker_image_name in ${DOCKER_NAMES}; do
  docker build \
    --file=${DOCKER_FILE} \
    --pull \
    -t ${docker_image_name} \
    .
done