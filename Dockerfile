#
# Interactive Debian-based container for the
# "build_fabric" Ansible setup procedure.
#
# Contains Ansible, Napalm, and the right
# configuration to start.
#
# A copy of the repo is copied to /build_fabric,
# the virtual environment with the python
# dependencies in /venv
#
# Run with:
# $ ansible-playbook -i inv_from_vars_cfg.yml PB_build_fabric.yml
#
# Validate with:
# $ ansible-playbook -i inv_from_vars_cfg.yml PB_post_validate.yml
#
# View inventory with:
# $ ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph

FROM debian:11

# Target directory to copy stuff to
ENV TARGET=/build_fabric
# Virtual environment directory
ENV VENV=/venv
# The python binary/directory name
ENV PYTHON=python3.9

# Copy everything to target
# TODO: be more specific
RUN mkdir $TARGET
COPY . $TARGET

# Install Debian / Python requirements
RUN apt-get update && \
  apt-get install -y python3 python3-pip python3-virtualenv && \
  virtualenv $VENV && \
  apt-get autoremove -y && \
  rm -rf /var/lib/apt/lists/* /var/cache/apt

RUN . $VENV/bin/activate && pip3 install -r ./build_fabric/requirements.txt

# Patch the paths in the ansible.cfg to fit the image layout
RUN sed \
-e "s#^library = .*#library = $VENV/lib/$PYTHON/site-packages/napalm_ansible/modules#" \
-e "s#^action_plugins = .*#action_plugins = $VENV/lib/$PYTHON/site-packages/napalm_ansible/plugins/action#" \
-e "s#^python_interpreter = .*#python_interpreter = /usr/bin/env $VENV/bin/$PYTHON#" \
< $TARGET/ansible.cfg.template > $TARGET/ansible.cfg

# Copy ansible config to /etc/ansible just in case we overwrite the volume $TARGET
RUN mkdir -p /etc/ansible && cp $TARGET/ansible.cfg /etc/ansible

# Include the virtual environment in the shell environment
ENV PATH=$PATH:$VENV/bin
ENV VIRTUAL_ENV=$VENV
ENV ANSIBLE_INVENTORY_PLUGINS=$TARGET

# chdir to $TARGET
WORKDIR $TARGET
