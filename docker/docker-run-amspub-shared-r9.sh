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
-v "${AMSPUB_SOURCE}"/bin:/usr/local/bin/:ro \
-v "${AMSPUB_SOURCE}"/config/ams-publisher-testing.conf:/etc/ams-publisher/ams-publisher.conf:ro \
-v "${AMSPUB_SOURCE}"/config/metric_data.avsc:/etc/ams-publisher/metric_data.avsc:ro \
-v "${AMSPUB_SOURCE}"/pymod:/usr/lib/python3.9/site-packages/ams_publisher/:ro \
-v "${AMSPUB_SOURCE}"/init/ams-publisher-sensu.service:/usr/lib/systemd/system/ams-publisher-sensu.service:ro \
\
-h docker-amspub \
--rm -ti -v /dev/log:/dev/log ipanema:5000/ams-publisher

# \
# -v "${HOME}/my_work/srce/git.ARGOeu-Metrics/argo-probe-ams-publisher":/home/user/amspub-probe-source \
