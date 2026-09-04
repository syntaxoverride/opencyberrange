#!/bin/bash
# Start SSH
/usr/sbin/sshd -D &
SSH_PID=$!

# Start WinRM simulator on port 5985
python3 /usr/local/bin/winrm-simulator.py 5985 &
WINRM1_PID=$!

# Start WinRM simulator on port 5986
python3 /usr/local/bin/winrm-simulator.py 5986 &
WINRM2_PID=$!

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
