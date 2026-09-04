FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

COPY traffic-loop.sh /traffic-loop.sh
RUN chmod +x /traffic-loop.sh

CMD ["/traffic-loop.sh"]
