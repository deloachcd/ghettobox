#!/bin/bash

COMPOSE_HTTP_TIMEOUT=900 tmux new-session -d -s "ghettobox" docker-compose up

cat << EOF
 __  __ __  __  ___  ____  _   _    _    ____  
        _        _   _       _             
   __ _| |_  ___| |_| |_ ___| |__  _____ __
  / _\` | ' \/ -_)  _|  _/ _ \ '_ \/ _ \ \ /
  \__, |_||_\___|\__|\__\___/_.__/\___/_\_\\
  |___/                                    
 __  __ __  __  ___  ____  _   _    _    ____

Created a tmux session for container services to run in.

You can see their status by attaching to the session:
    tmux attach-session -t "ghettobox"

Once inside the session, you can detach from it with:
    CTRL-b d

You can take down the services with:
    docker-compose down
EOF
