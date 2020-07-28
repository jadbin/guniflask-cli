#!/usr/bin/env bash

bin=$(dirname ${BASH_SOURCE[0]})
bin=$(cd "$bin"; pwd)

export GUNIFLASK_HOME=${GUNIFLASK_HOME:-$(cd "$bin"/../; pwd)}
export GUNIFLASK_CONF_DIR=${GUNIFLASK_CONF_DIR:-"$GUNIFLASK_HOME"/conf}

if [ -f "$GUNIFLASK_CONF_DIR"/app-env.sh ]; then
    . "$GUNIFLASK_CONF_DIR"/app-env.sh
fi
