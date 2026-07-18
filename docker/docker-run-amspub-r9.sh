#!/bin/bash

AMSPUB_SOURCE="${HOME}/my_work/srce/git.ams-publisher/ams-publisher"

docker rm ams-publisher; \
docker run \
--log-driver json-file \
--log-opt max-size=10m \
--name ams-publisher \
-u user \
--privileged \
--net host \
-v /etc/localtime:/etc/localtime:ro \
\
-e "SSH_AUTH_SOCK=${SSH_AUTH_SOCK}" \
--mount type=bind,src="${SSH_AUTH_SOCK}",target="${SSH_AUTH_SOCK}" \
\
-v "${HOME}":/mnt/ \
-v "${HOME}/.docker_zsh_history":/home/user/.zsh_history \
-v "${AMSPUB_SOURCE}":/home/user/amspub-source \
\
-h docker-amspub \
--rm -ti -v /dev/log:/dev/log ipanema:5000/ams-publisher
