FROM debian:11
ENV TARGET=/build_fabric
ENV VENV=/build_fabric/venv
ENV PYTHON=python3.9
RUN mkdir $TARGET
COPY . $TARGET
# Install Debian / Python requirements
RUN apt-get update && \
  apt-get install -y python3 python3-pip python3-virtualenv && \
  virtualenv $VENV
RUN . $VENV/bin/activate && pip3 install -r ./build_fabric/requirements.txt
# Tweak the paths in the ansible.cfg to fit the image layout
RUN sed -i \
-e "s#^library = .*#library = $VENV/lib/$PYTHON/site-packages/napalm_ansible/modules#" \
-e "s#^action_plugins = .*#action_plugins = $VENV/lib/$PYTHON/site-packages/napalm_ansible/plugins/action#" \
-e "s#^python_interpreter = .*#python_interpreter = /usr/bin/env $VENV/bin/$PYTHON#" \
$TARGET/ansible.cfg

ENV PATH=$PATH:$VENV/bin
