#!/bin/bash
export GB_USER_UID=""
export GB_USER_GID=""
export PLEX_CLAIM=""
export SAMBA_USERNAME=""
export SAMBA_PASSWORD=""
export OPENVPN_USERNAME=""
export OPENVPN_PASSWORD=""
export OPENVPN_SERVER_REGIONS=""
export TRANSMISSION_USERNAME=""
export TRANSMISSION_PASSWORD=""
export SLSKD_USERNAME=""
export SLSKD_PASSWORD=""
export SOULSEEK_SHARE_PATH=""

docker compose "$@"