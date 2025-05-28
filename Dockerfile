FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]
ENV BASH_ENV=~/.bashrc           \
    MAMBA_ROOT_PREFIX=/srv/conda \
    PATH=$PATH:/srv/conda/envs/env_app_snuggs/bin

ADD environment.yml /tmp/environment.yml

RUN apt-get update                                                                                                          && \
    apt-get install -y ca-certificates ttf-dejavu file wget bash bzip2                                                      && \
    wget -qO- https://micromamba.snakepit.net/api/micromamba/linux-64/latest | tar -xvj bin/micromamba --strip-components=1 && \
    ./micromamba shell init -s bash                                                                                         && \
    apt-get clean autoremove --yes                                                                                          && \
    rm -rf /var/lib/{apt,dpkg,cache,log}                                                                                    && \
    cp ./micromamba /usr/bin                                                                                                && \
    micromamba create -f /tmp/environment.yml
    
COPY . /tmp

RUN cd /tmp                                                    && \
    /srv/conda/envs/env_app_snuggs/bin/python setup.py install && \
    rm -fr /srv/conda/pkgs                                     && \
    rm -fr /tmp/*

