FROM quay.io/centos/centos:stream9
LABEL authors="Luis Tomas Bolivar<luis5tb@gmail.com>"

RUN dnf upgrade -y \
    && dnf install -y epel-release \
    && dnf install -y --setopt=tsflags=nodocs python3-pip \
    && dnf install -y --setopt=tsflags=nodocs python3-devel

RUN pip3 --no-cache-dir install -U pip \
    && python3 -m pip install cloudevents kubernetes flask

WORKDIR /physics-cluster-registration

COPY ./cluster-registration/* ./

EXPOSE 8080

CMD [ "python3", "cluster-registration.py"]