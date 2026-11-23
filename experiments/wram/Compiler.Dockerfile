FROM ubuntu:22.04@sha256:f64b2ffc2f10ab8f8505aa56b2664bd846cbb9df87c7e2532e30f7667021c0e6
# Copy the build host's trusted public CA bundle into the ignored build context.
COPY ca-bundle.crt /etc/ssl/certs/ca-certificates.crt
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    libedit2 libtinfo6 libxml2 libzstd1 ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*
COPY upmem-2023.1.0-Linux-x86_64 /opt/upmem
ENV PATH="/opt/upmem/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/upmem/lib"
WORKDIR /work
