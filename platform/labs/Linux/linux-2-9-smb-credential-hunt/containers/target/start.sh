#!/bin/bash
smbd --foreground --no-process-group &
nmbd --foreground --no-process-group &
exec sleep infinity
