FROM alpine:3.18

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apk add --no-cache curl

COPY attack-loop.sh /attack-loop.sh
RUN chmod +x /attack-loop.sh

CMD ["/bin/sh", "/attack-loop.sh"]
