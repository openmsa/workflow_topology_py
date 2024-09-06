#!/bin/bash
. /usr/share/install-libraries/il-lib.sh

pushd /opt/fmc_repository/Process || exit;
emit_step "Linking %b" "Topology"
mk_meta_link "OpenMSA_Workflow_Topology" "Topology"
popd || exit

