import boto3
import os
import time
from datetime import datetime, timedelta
from collections import deque

# 환경변수로 설정
aws_access_key_id = os.environ.get("accessID")
aws_secret_access_key = os.environ.get("accessKey")
region_name = 'eu-north-1'  # 사용하려는 AWS 리전을 지정하세요

print(aws_access_key_id)

# AWS 클라이언트 생성
ec2 = boto3.client('ec2', region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
ssm = boto3.client('ssm', region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
cloudwatch = boto3.client('cloudwatch', region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
sts_client = boto3.client('sts', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def list_instances():
    print("Listing instances....")
    reservations = ec2.describe_instances()

    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            print(f"[id] {instance['InstanceId']}, "
                  f"[AMI] {instance['ImageId']}, "
                  f"[type] {instance['InstanceType']}, "
                  f"[state] {instance['State']['Name']}, "
                  f"[monitoring state] {instance['Monitoring']['State']}")
    

def available_zones():
    print("Available zones....")
    availability_zones = ec2.describe_availability_zones()
    for zone in availability_zones['AvailabilityZones']:
        print(f"[id] {zone['ZoneId']}, "
              f"[region] {zone['RegionName']}, "
              f"[zone] {zone['ZoneName']}")
    print(f"You have access to {len(availability_zones['AvailabilityZones'])} Availability Zones.")

def start_instance(instance_id):
    try:
        # 현재 상태 확인
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']

        # 인스턴스 상태에 따라 처리
        if state == 'running':
            print(f"Instance {instance_id} is already running.")
        elif state == 'stopped':
            print(f"Starting .... {instance_id}")
            ec2.start_instances(InstanceIds=[instance_id])
            print(f"Successfully started instance {instance_id}")
        else:
            print(f"Cannot start instance {instance_id} in the current state: {state}")
    except Exception as e:
        print(f"Error starting instance {instance_id}: {e}")

def available_regions():
    print("Available regions....")
    regions_response = ec2.describe_regions()
    for region in regions_response['Regions']:
        print(f"[region] {region['RegionName']}, [endpoint] {region['Endpoint']}")

def stop_instance(instance_id):
    print(f"Stopping .... {instance_id}")
    ec2.stop_instances(InstanceIds=[instance_id])
    print(f"Successfully stopped instance {instance_id}")

def create_instance(ami_id):
    print(f"Creating instance with AMI {ami_id}")
    instances = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t3.micro',
        MaxCount=1,
        MinCount=1
    )
    instance_id = instances['Instances'][0]['InstanceId']
    print(f"Successfully created EC2 instance {instance_id} based on AMI {ami_id}")

def reboot_instance(instance_id):
    print(f"Rebooting .... {instance_id}")
    ec2.reboot_instances(InstanceIds=[instance_id])
    print(f"Successfully rebooted instance {instance_id}")

def list_images():
    print("Listing images....")
    # filters = [{'Name': 'name', 'Values': ['masterimg']}]

    aws_account_id = sts_client.get_caller_identity().get('Account')
    image_ids = []

    images = ec2.describe_images(Owners=[aws_account_id])
    for image in images['Images']:
        print(f"[ImageID] {image['ImageId']}, [Name] {image['Name']}, [Owner] {image['OwnerId']}")
        image_ids.append(image['ImageId'])
    
    return image_ids

def command_input():
    ins_id = input("Enter Instance id: ")
    command = input("Enter command: ")
    command_response = ssm.send_command(
        InstanceIds=[ins_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': [command],
            'executionTimeout': ['3600'], },
        TimeoutSeconds=30, )
    command_id = command_response['Command']['CommandId']
    time.sleep(5)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=ins_id,
    )
    print(output['StandardOutputContent'])

def get_instance_monitoring_data(instance_id):
    try:
        # 인스턴스의 상태 확인
        instance_status = ec2.describe_instance_status(InstanceIds=[instance_id])
        print("Instance Status:")
        for status in instance_status['InstanceStatuses']:
            print(f"  - Availability Zone: {status['AvailabilityZone']}")
            print(f"  - Instance ID: {status['InstanceId']}")
            print(f"  - Instance State: {status['InstanceState']['Name']}")
            print(f"  - System Status: {status['SystemStatus']['Status']}")
            print(f"  - Instance Status: {status['InstanceStatus']['Status']}")
            print("\n")

        # 인스턴스의 모니터링 데이터 확인
        monitoring_data = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'm1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': 'CPUUtilization',
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': instance_id
                                },
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Average',
                    },
                    'ReturnData': True,
                },
            ],
            StartTime=int((datetime.utcnow() - timedelta(seconds=3600)).timestamp()),  # 1 hour ago
            EndTime=int(datetime.utcnow().timestamp()),
        )

        print("Monitoring Data:")
        for result in monitoring_data['MetricDataResults']:
            print(f"  - Query ID: {result['Id']}")
            print(f"  - Metric Data:")
            for timestamp, value in zip(result['Timestamps'], result['Values']):
                formatted_time = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"    - Time: {formatted_time}, Value: {value}")
            print("\n")

    except Exception as e:
        print(f"Error: {e}")

# cpu 용량 확인하는 코드
def ins_credit(instance_id):                       
    print("Instance credit ....")
    ins_list = []
    ins_list.append(instance_id)
    credits = ec2.describe_instance_credit_specifications(InstanceIds=ins_list)
    print("[ID] " + instance_id + ", [CPU Credits] " + credits['InstanceCreditSpecifications'][0]['CpuCredits'])


# 실행중인 인스턴스 개수 리턴
def running_instances():
    reservations = ec2.describe_instances()

    running_instances = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running' or instance['State']['Name'] == 'pending':
                running_instances.append(instance['InstanceId'])

    return running_instances

def terminated_instances():
    reservations = ec2.describe_instances()

    stop_instances = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'stopped' or instance['State']['Name'] == 'stopping':
               stop_instances.append(instance['InstanceId'])

    return stop_instances

# 모든 인스턴스 리턴
def all_instances():
    reservations = ec2.describe_instances()

    all_instances = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] != 'terminated':
                all_instances.append(instance)

    return all_instances

# 원하는 개수 만큼 인스턴스를 실행하는 함수
def desired_instances(desired_instances_count):
    print('함수 실행 중...')
    # 실행중이거나, 멈춰있는 인스턴스의 개수 총합
    all_instance_count = len(running_instances()) + len(terminated_instances())
    running_instances_list = running_instances()

    # 총 인스턴스가 요구된 인스턴스보다 적으면 추가로 인스턴스 생성
    while desired_instances_count > all_instance_count:
        print('인스턴스 개수가 모자라',(desired_instances_count) - (len(all_instances)) , '개의 인스턴스를 추가 생성합니다')
        image_list = list_images()
        create_instance(image_list[0])
        all_instance_count += 1

    if desired_instances_count > len(running_instances_list):
        # 원하는 수가 실행 중인 수보다 크면 부족한 만큼의 인스턴스를 시작합니다.
        instances_to_start = desired_instances_count - len(running_instances_list)
        terminated_instances_list = terminated_instances()[:instances_to_start]
        ec2.start_instances(InstanceIds=terminated_instances_list)

    elif desired_instances_count < len(running_instances_list):
        # 실행 중인 수가 원하는 수보다 크면 초과한 만큼의 인스턴스를 중지합니다.
        instances_to_stop = len(running_instances_list) - desired_instances_count
        instances_to_stop_list = running_instances_list[:instances_to_stop]
        ec2.stop_instances(InstanceIds=instances_to_stop_list)

    else:
        print('현재 인스턴스 개수가 원하는 수와 같습니다')

    list_instances()


while True:
    print("                                                            ")
    print("                                                            ")
    print("------------------------------------------------------------")
    print("           Amazon AWS Control Panel using SDK               ")
    print("------------------------------------------------------------")
    print("  1. list instance                2. available zones        ")
    print("  3. start instance               4. available regions      ")
    print("  5. stop instance                6. create instance        ")
    print("  7. reboot instance              8. list images            ")
    print("  9. input command               10. instance monitoring    ")
    print(" 11. instance credit             12. instance scaling       ")
    print("                                 99. quit                   ")
    print("------------------------------------------------------------")

    number = input("Enter an integer: ")

    if number.isnumeric():
        number = int(number)
    else:
        print("Invalid input!")
        break
    if number == 1:
        list_instances()
    elif number == 2:
        available_zones()
    elif number == 3:
        instance_id = input("Enter instance id: ")
        start_instance(instance_id)
    elif number == 4:
        available_regions()
    elif number == 5:
        instance_id = input("Enter instance id: ")
        stop_instance(instance_id)
    elif number == 6:
        ami_id = input("Enter AMI id: ")
        create_instance(ami_id)
    elif number == 7:
        instance_id = input("Enter instance id: ")
        reboot_instance(instance_id)
    elif number == 8:
        list_images()
    elif number == 9:
        command_input()
    elif number == 10:
        instance_id = input("Enter instance id: ")
        get_instance_monitoring_data(instance_id)
    elif number == 11:
        instance_id = input("Enter instance id: ")
        ins_credit(instance_id)
    elif number == 12:
        num = int(input("원하는 인스턴스 개수를 입력하세요: "))
        desired_instances(num)
    elif number == 99:
        print("Goodbye!")
        break
    else:
        print("Invalid input!")
