##
## Build with:
##
##    docker build -t animalid:latest .
##
## Run with:
##
##    docker run -p 8000:8000 -it animalid:latest ./manage.py runserver 0.0.0.0:8000
##

# Our base image is ubuntu with one of our hardest dependencies already installed
FROM python:3.7-buster

# Python should not be allowed to poop .pyc files (non-empty string=true)
ENV PYTHONDONTWRITEBYTECODE 1

# When we get to python 3.8, we can use this instead
ENV PYTHONPYCACHEPREFIX /tmp

# Python should not buffer stdin or stdout (non-empty string=true)
ENV PYTHONUNBUFFERED 1

# Set up our user
RUN groupadd --non-unique --gid 888 --system animalid && \
    useradd --non-unique --uid 888 --system animalid --gid animalid --home /animalid/ && \
    chsh -s /bin/bash animalid && \
    chsh -s /bin/bash root
COPY bashrc /animalid/.bashrc
COPY bashrc /root/.bashrc
WORKDIR /animalid/

# Build/Install python dependencies
RUN pip install --upgrade pip
COPY requirements.txt /animalid/requirements.txt
RUN pip install -r /animalid/requirements.txt

# Snapshot the codebase
COPY . /animalid
RUN chown -R animalid:animalid .

# Set up database
RUN ./manage.py migrate
