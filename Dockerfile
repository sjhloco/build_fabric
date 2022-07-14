FROM debian:11

# Target directory to copy stuff to
ENV TARGET=/build_fabric
# Virtual environment directory
ENV VENV=/build_fabric/venv
# The python binary/directory name
ENV PYTHON=python3.9

# Copy everything to target
# TODO: be more specific
RUN mkdir $TARGET
COPY . $TARGET

# Install Debian / Python requirements
RUN apt-get update && \
  apt-get install -y python3 python3-pip python3-virtualenv && \
  virtualenv $VENV
RUN . $VENV/bin/activate && pip3 install -r ./build_fabric/requirements.txt

# Patch the paths in the ansible.cfg to fit the image layout
RUN sed -i \
-e "s#^library = .*#library = $VENV/lib/$PYTHON/site-packages/napalm_ansible/modules#" \
-e "s#^action_plugins = .*#action_plugins = $VENV/lib/$PYTHON/site-packages/napalm_ansible/plugins/action#" \
-e "s#^python_interpreter = .*#python_interpreter = /usr/bin/env $VENV/bin/$PYTHON#" \
$TARGET/ansible.cfg

# Include the virtual environment in the shell environment
ENV PATH=$PATH:$VENV/bin
ENV VIRTUAL_ENV=/build_fabric/venv
