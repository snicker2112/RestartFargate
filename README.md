temporary file to xport

# MSK Rolling Restart

## CloudFormation : Pipeline

Below is a CloudFormation template that creates an AWS CodePipeline which triggers a Lambda function to check if the specified Amazon Managed Streaming for Apache Kafka (MSK) cluster is active. This template assumes you have an existing Amazon S3 bucket for storing the Lambda deployment package and a GitHub repository for storing the Lambda source code.

```
AWSTemplateFormatVersion: "2010-09-09"
Description: "A CloudFormation template for creating a CodePipeline that runs a Lambda function to check if an MSK cluster is active."

Resources:
  LambdaDeploymentBucket:
    Type: "AWS::S3::Bucket"
    Properties:
      BucketName: "your-lambda-deployment-bucket-name"

  LambdaExecutionRole:
    Type: "AWS::IAM::Role"
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Action: "sts:AssumeRole"
            Effect: "Allow"
            Principal:
              Service: "lambda.amazonaws.com"

      Policies:
        - PolicyName: "LambdaMSKAccessPolicy"
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Action:
                  - "logs:CreateLogGroup"
                  - "logs:CreateLogStream"
                  - "logs:PutLogEvents"
                  - "kafka:DescribeCluster"
                Effect: "Allow"
                Resource: "*"

  LambdaFunction:
    Type: "AWS::Lambda::Function"
    Properties:
      Code:
        S3Bucket: !Ref LambdaDeploymentBucket
        S3Key: "path/to/your/lambda/deployment/package.zip"
      FunctionName: "MSKClusterStatusChecker"
      Handler: "lambda_function.lambda_handler"
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: "python3.8"
      Timeout: 15

  Pipeline:
    Type: "AWS::CodePipeline::Pipeline"
    Properties:
      ArtifactStore:
        Location: !Ref ArtifactStoreBucket
        Type: "S3"
      RoleArn: !GetAtt PipelineRole.Arn
      Stages:
        - Name: "Source"
          Actions:
            - Name: "SourceAction"
              ActionTypeId:
                Category: "Source"
                Owner: "ThirdParty"
                Provider: "GitHub"
                Version: "1"
              Configuration:
                Owner: "your-github-username"
                Repo: "your-github-repo-name"
                Branch: "main"
                OAuthToken: !Ref GitHubToken
              OutputArtifacts:
                - Name: "SourceArtifact"
          RunOrder: 1
        - Name: "InvokeLambda"
          Actions:
            - Name: "InvokeLambdaAction"
              ActionTypeId:
                Category: "Invoke"
                Owner: "AWS"
                Provider: "Lambda"
                Version: "1"
              Configuration:
                FunctionName: !Ref LambdaFunction
                UserParameters: !Sub |
                  {
                    "MSKClusterARN": "arn:aws:kafka:your-region:your-account-id:cluster/your-cluster-name/your-cluster-id"
                  }
              InputArtifacts:
                - Name: "SourceArtifact"
          RunOrder: 2

  ArtifactStoreBucket:
    Type: "AWS::S3::Bucket"

  PipelineRole:
    Type: "AWS::IAM::Role"
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Action: "sts:AssumeRole"
            Effect: "Allow"
            Principal:
              Service: "codepipeline.amazonaws.com"
      Policies:
        - PolicyName: "CodePipelineAccessPolicy"
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Action:
                  - "s3:GetObject"
                  - "s3:GetObjectVersion"
                  - "s3:GetBucketVersioning"
                  - "s3:PutObject"
                Effect: "Allow"
                Resource:
                  - !Sub "arn:aws:s3:::${ArtifactStoreBucket}/*"
                  - !Sub "arn:aws:s3:::${LambdaDeploymentBucket}/*"
              - Action:
                  - "lambda:InvokeFunction"
                Effect: "Allow"
                Resource: !GetAtt LambdaFunction.Arn
              - Action:
                  - "iam:PassRole"
                Effect: "Allow"
                Resource: !GetAtt LambdaExecutionRole.Arn

  GitHubToken:
    Type: "AWS::SSM::Parameter::Value<String>"
    Default: "/path/to/your/github/token"

Outputs:
  LambdaDeploymentBucketName:
    Description: "The name of the Lambda deployment S3 bucket."
    Value: !Ref LambdaDeploymentBucket
  LambdaFunctionARN:
    Description: "The ARN of the Lambda function."
    Value: !GetAtt LambdaFunction.Arn
  CodePipelineARN:
    Description: "The ARN of the CodePipeline."
    Value: !GetAtt Pipeline.Arn
                 
```



## Lambda : Check Active

Below is a simple Python Lambda function that checks if an MSK cluster is active. The function takes the cluster ARN from the user parameters and uses the Boto3 library to interact with the AWS SDK.

lambda_function.py:

```
import json
import boto3
from botocore.exceptions import ClientError

def check_msk_cluster_status(cluster_arn):
    client = boto3.client('kafka')
    try:
        response = client.describe_cluster(
            ClusterArn=cluster_arn
        )
        return response['ClusterInfo']['State']
    except ClientError as e:
        print(f"Error getting MSK cluster status: {e}")
        return None

def lambda_handler(event, context):
    user_parameters = json.loads(event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters'])
    msk_cluster_arn = user_parameters['MSKClusterARN']

    cluster_status = check_msk_cluster_status(msk_cluster_arn)

    if cluster_status == 'ACTIVE':
        print(f"MSK cluster {msk_cluster_arn} is active.")
    else:
        print(f"MSK cluster {msk_cluster_arn} is not active. Current status: {cluster_status}")

    return {
        'statusCode': 200,
        'body': json.dumps(f'MSK cluster status: {cluster_status}')
    }
```

Before uploading the Lambda deployment package to S3, you'll need to create a .zip file containing the lambda_function.py file and any dependencies, such as the boto3 library if you're using a custom runtime.

To create the deployment package, follow these steps:

* If you don't have the boto3 library installed, install it using pip:

```
pip install boto3
```

* Create a new directory for the deployment package, e.g., msk_status_checker:

```
mkdir msk_status_checker
```

* Copy the lambda_function.py file and the boto3 library to the msk_status_checker directory. If you're using a virtual environment, the boto3 library is located inside the site-packages directory within the virtual environment's lib folder. If you're not using a virtual environment, the boto3 library should be located in your system's Python site-packages directory. For example:

```
cp lambda_function.py msk_status_checker/
cp -R /path/to/site-packages/boto3 msk_status_checker/
cp -R /path/to/site-packages/botocore msk_status_checker/
cp -R /path/to/site-packages/dateutil msk_status_checker/
cp -R /path/to/site-packages/jmespath msk_status_checker/
cp -R /path/to/site-packages/s3transfer msk_status_checker/
cp -R /path/to/site-packages/urllib3 msk_status_checker/

```
Make sure to replace /path/to/site-packages with the actual path to your Python site-packages directory.

* Change your working directory to msk_status_checker:

```
cd msk_status_checker
```

* Create a .zip archive of the contents within the msk_status_checker directory:

```
zip -r ../msk_status_checker.zip .
```

* Upload the msk_status_checker.zip file to the S3 bucket specified in the CloudFormation template. You can use the AWS CLI or the AWS Management Console to upload the file. For example, using the AWS CLI:

```
aws s3 cp msk_status_checker.zip s3://your-lambda-deployment-bucket-name/path/to/your/lambda/deployment/package.zip
```
Replace your-lambda-deployment-bucket-name with the actual bucket name and path/to/your/lambda/deployment/ with the desired path within the bucket.

Once you've created and uploaded the Lambda deployment package, update the CloudFormation template's LambdaFunction resource with the correct S3 bucket and key for the uploaded .zip file.


