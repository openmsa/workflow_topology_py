Kibana Deployment Workflow
=========

This repository provides the workflow for deploying the workflow that creates the Topology dataset.

Alternatively, see below "Installing this repo on a local MSA".


Installing this repo for local environment
------------------------------------------

The procedure below is for developer who are going to code changes on a MSActivator. The installation of the workflow for operational use can be done by running a container based installer

Login to a live MSA as root and perform the following:

	cd /opt/fmc_repository
	git clone https://github.com/openmsa/workflow_kibana.git OpenMSA_Workflow_Topology
	cd Process/
	ln -s ../OpenMSA_Workflow_Topology/ OpenMSA_Workflow_Topology
	
	# Disable the automatic update to prevent unintended changes to workflows during local development.
	mkdir -p /opt/fmc_repository/OpenMSA_Workflow_Topology/.devops 


The new entry "Topology" should be available and browsable under `Automation > Workflows`.
