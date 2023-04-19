import sys
import time

try:
    import boto3
except ImportError:
    print("Error: boto3 library is not installed. Please install it using 'pip install boto3'")
    sys.exit(1)

def check_aws_credentials():
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print("Error: AWS credentials are not set. Please set your AWS credentials as environment variables or in a configuration file.")
        sys.exit(1)

def get_msk_broker_ids(cluster_arn):
    client = boto3.client('kafka')
    response = client.list_nodes(ClusterArn=cluster_arn)

    broker_ids = []
    for node_info in response['NodeInfoList']:
        broker_id = node_info['BrokerNodeInfo']['BrokerId']
        broker_ids.append(str(broker_id))

    return broker_ids

def reboot_msk_brokers(cluster_arn, broker_ids, sleep_time=120):
    client = boto3.client('kafka')

    for broker_id in broker_ids:
        print(f"Restarting broker with ID: {broker_id}")
        client.reboot_broker(
            ClusterArn=cluster_arn,
            BrokerIds=[broker_id]
        )
        print(f"Waiting {sleep_time} seconds before restarting the next broker...")
        time.sleep(sleep_time)
    print("Rolling restart complete.")

if __name__ == "__main__":
    # Check for prerequisites
    check_aws_credentials()

    # Replace with your MSK cluster ARN
    cluster_arn = "arn:aws:kafka:REGION:ACCOUNT_ID:cluster/CLUSTER_NAME/UUID"

    broker_ids = get_msk_broker_ids(cluster_arn)
    print(f"Discovered broker IDs: {broker_ids}")

    reboot_msk_brokers(cluster_arn, broker_ids)
