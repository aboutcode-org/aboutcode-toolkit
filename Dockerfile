#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/aboutcode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

FROM python:3.6-slim-buster 

RUN apt-get update \
 && apt-get install -y bash bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libgomp1 libpopt0\
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create directory for aboutcode sources
RUN mkdir aboutcode-toolkit

# Copy sources into docker container
COPY . aboutcode-toolkit

# Set workdir
WORKDIR aboutcode-toolkit

RUN bash -c "source ./configure"

# Add aboutcode to path
#ENV PATH=$HOME/aboutcode-toolkit:$PATH

# Set entrypoint to be the aboutcode command, allows to run the generated docker image directly with the aboutcode arguments: 
# `docker run (...) <containername> <about arguments>`
# Example: docker run --rm --name "aboutcode" -v ${PWD}:/project -v /tmp/result:/result aboutcode-toolkit attrib /project /result/c.html
ENTRYPOINT ["./bin/about"]
