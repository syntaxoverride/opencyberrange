FROM alpine:3.19

RUN apk add --no-cache \
    tcpdump \
    socat \
    iproute2 \
    bash

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9999

ENTRYPOINT ["/entrypoint.sh"]
