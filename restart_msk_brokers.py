import boto3
import time


def restart_msk_brokers(cluster_arn):
    """
    Restarts AWS MSK brokers one at a time, testing each before moving on to the next.
    """
    client = boto3.client("kafka")

    # Get a list of all brokers in the cluster
    response = client.list_nodes(ClusterArn=cluster_arn)
    brokers = response["NodeInfoList"]

    # Loop through each broker
    for broker in brokers:
        broker_id = broker["BrokerNodeInfo"]["BrokerNodeId"]
        print(f"Restarting broker {broker_id}...")

        # Stop the broker
        client.update_broker_storage(
            ClusterArn=cluster_arn,
            BrokerIds=[broker_id],
            CurrentVersion="KAFKA_V2_8_0",
            TargetBrokerEBSVolumeInfo=[],
        )

        # Wait for the broker to stop
        while True:
            response = client.describe_cluster_operation(
                ClusterArn=cluster_arn, OperationArn=response["ClusterOperationArn"]
            )
            status = response["OperationState"]
            if status == "COMPLETED":
                print(f"Broker {broker_id} stopped successfully.")
                break
            elif status == "FAILED":
                print(f"Failed to stop broker {broker_id}.")
                return

        # Start the broker
        client.update_broker_storage(
            ClusterArn=cluster_arn,
            BrokerIds=[broker_id],
            CurrentVersion="KAFKA_V2_8_0",
            TargetBrokerEBSVolumeInfo=[
                {
                    "BrokerEBSVolumeInfo": {
                        "KafkaBrokerNodeId": broker_id,
                        "VolumeSizeGB": 1000,
                        "VolumeType": "gp2",
                    }
                }
            ],
        )

        # Wait for the broker to start
        while True:
            response = client.describe_cluster_operation(
                ClusterArn=cluster_arn, OperationArn=response["ClusterOperationArn"]
            )
            status = response["OperationState"]
            if status == "COMPLETED":
                print(f"Broker {broker_id} started successfully.")
                break
            elif status == "FAILED":
                print(f"Failed to start broker {broker_id}.")
                return

        # Test the broker
        print(f"Testing broker {broker_id}...")
        time.sleep(60)  # Wait for the broker to become fully available
        response = client.get_bootstrap_brokers(ClusterArn=cluster_arn)
        bootstrap_brokers = response["BootstrapBrokerString"].split(",")
        if f"kafka://{broker['BrokerNodeInfo']['Endpoints'][0]}" in bootstrap_brokers:
            print(f"Broker {broker_id} is working correctly.")
        else:
            print(f"Failed to verify broker {broker_id}.")
            return

    print("All brokers have been restarted and tested successfully.")


"""
To use this function, simply call it with the ARN of your AWS MSK cluster:
restart_msk_brokers('arn:aws:kafka:us-west-2:123456789012:cluster/my-cluster/abcd1234-5678-90ab-cdef-0123456789ab')
"""
