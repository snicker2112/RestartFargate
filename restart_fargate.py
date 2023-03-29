"""
### Import the functions and run.
example script that imports the functions we've defined in a separate file called ecs_functions.py
"""

import ecs_functions

# Check prerequisites
ecs_functions.check_prerequisites()

# Configure AWS credentials
session = ecs_functions.configure_aws_credentials()

# Test AWS connectivity
ecs_functions.test_aws_connectivity(session)

# Select a service to restart
service_name = ecs_functions.select_service_to_restart(session)

# Test service restart
ecs_functions.test_service_restart(session, service_name)
