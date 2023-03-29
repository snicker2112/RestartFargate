import os
import sys
import subprocess
import boto3

# Check if AWS CLI and Boto3 are installed
def check_prerequisites():
    """
    Check if AWS CLI and Boto3 are installed.
    If not, prompt the user to install them using pip.
    """
    try:
        subprocess.check_output(["aws", "--version"])
        subprocess.check_output(["pip", "show", "boto3"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: AWS CLI and/or Boto3 is not installed.")
        install_prerequisites = input(
            "Do you want to install AWS CLI and Boto3? (y/n): "
        )
        if install_prerequisites.lower() == "y":
            try:
                subprocess.check_output(["pip", "install", "awscli", "boto3"])
                print("AWS CLI and Boto3 have been installed successfully.")
            except subprocess.CalledProcessError:
                print("Error: Failed to install AWS CLI and/or Boto3.")
        else:
            sys.exit()


# Configure AWS credentials
def configure_aws_credentials():
    """
    Configure AWS credentials either by using a named profile or programmatically.
    """
    config_type = input(
        "Choose your AWS credentials configuration type (named profile/programmatic): "
    )
    if config_type.lower() == "named profile":
        profile_name = input("Enter the name of your AWS CLI profile: ")
        session = boto3.Session(profile_name=profile_name)
    elif config_type.lower() == "programmatic":
        access_key_id = input("Enter your AWS access key ID: ")
        secret_access_key = input("Enter your AWS secret access key: ")
        region_name = input("Enter your preferred AWS region name: ")
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )
    else:
        print("Invalid configuration type.")
        configure_aws_credentials()

    return session


# Test AWS connectivity
def test_aws_connectivity(session):
    """
    Test AWS connectivity by trying to retrieve information from EC2.
    """
    try:
        ec2_client = session.client("ec2")
        ec2_client.describe_instances()
        print("AWS connectivity test passed.")
    except:
        print("Error: AWS connectivity test failed.")
        sys.exit()


# List Fargate instances and select a service to restart
def select_service_to_restart(session):
    """
    List all available ECS clusters and prompt the user to choose one.
    Then list all services in the selected cluster and prompt the user to choose one to restart.
    """
    fargate_client = session.client("ecs")
    clusters = fargate_client.list_clusters()["clusterArns"]
    if len(clusters) == 0:
        print("Error: No ECS clusters found.")
        sys.exit()
    else:
        print("Available ECS clusters:")
        for i, cluster in enumerate(clusters):
            print(f"{i+1}. {cluster.split('/')[-1]}")
        cluster_number = int(input("Enter the number of the cluster to use: "))
        cluster_arn = clusters[cluster_number - 1]
        cluster_name = cluster_arn.split("/")[-1]
        print(f"Selected ECS cluster: {cluster_name}")
    try:
        services = fargate_client.list_services(cluster=cluster_arn)["serviceArns"]
        if len(services) > 0:
            print("Services in the selected cluster:")
            for i, service in enumerate(services):
                print(f"{i+1}. {service.split('/')[-1]}")
            service_number = int(input("Enter the number of the service to restart: "))
            service_arn = services[service_number - 1]
            print(f"Restarting service {service_arn.split('/')[-1]}...")
            response = fargate_client.update_service(
                cluster=cluster_arn, service=service_arn, forceNewDeployment=True
            )
            print("Service restarted successfully.")
        else:
            print("Error: No services found in the selected cluster.")
            sys.exit()
    except:
        print("Error: Failed to list services or restart service.")
        sys.exit()


def test_service_restart(session):
    """
    Test service restart by checking the deployment status of the latest task in the selected service.
    Repeat the check until the deployment is active or a timeout occurs.
    """
    fargate_client = session.client("ecs")
    task_arnc = None
    timeout_seconds = 300
    start_time = time.time()
    while True:
        try:
            task = fargate_client.list_tasks(
                cluster=cluster_arn, serviceName=service_arn
            )["taskArns"][0]
            if task != task_arnc:
                task_arnc = task
                task_details = fargate_client.describe_tasks(
                    cluster=cluster_arn, tasks=[task_arnc]
                )["tasks"][0]
                task_status = task_details["lastStatus"]
                if task_status == "RUNNING":
                    print("Service restart test passed.")
                    break
                elif task_status == "STOPPED":
                    reason = task_details["stoppedReason"]
                    print(
                        f"Error: Service restart failed. Task stopped with reason: {reason}"
                    )
                    break
            else:
                time.sleep(5)
            if time.time() - start_time > timeout_seconds:
                print("Error: Service restart test timed out.")
                break
        except:
            print("Error: Failed to test service restart.")
            sys.exit()
