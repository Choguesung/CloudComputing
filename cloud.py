import boto3
import os
import time
from datetime import datetime, timedelta
from collections import deque

# 환경변수로 설정
aws_access_key_id = os.environ.get("accessID")
aws_secret_access_key = os.environ.get("accessKey")
region_name = 'eu-north-1'  # 사용하려는 AWS 리전을 지정하세요

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
        
        list_instances()

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

    list_instances()

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

    list_instances()

def reboot_instance(instance_id):
    print(f"Rebooting .... {instance_id}")
    ec2.reboot_instances(InstanceIds=[instance_id])
    print(f"Successfully rebooted instance {instance_id}")

    list_instances()

def list_images():
    print("Listing images....")

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
            'executionTimeout': ['4000'], },
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
        instance_status = ec2.describe_instance_status(InstanceIds=[instance_id])
        print("Instance Status:")
        for status in instance_status['InstanceStatuses']:
            print(f"  - Availability Zone: {status['AvailabilityZone']}")
            print(f"  - Instance ID: {status['InstanceId']}")
            print(f"  - Instance State: {status['InstanceState']['Name']}")
            print(f"  - System Status: {status['SystemStatus']['Status']}")
            print(f"  - Instance Status: {status['InstanceStatus']['Status']}")
            print("\n")

    except Exception as e:
        print(f"Error: {e}")

# cpu 용량 확인하는 코드 (얼마나 사용할수있는가)
def ins_credit(instance_id):                       
    print("Instance credit ....")
    ins_list = []
    ins_list.append(instance_id)
    credits = ec2.describe_instance_credit_specifications(InstanceIds=ins_list)
    
    # 추가: 현재 인스턴스의 유형 확인
    instance_type = ec2.describe_instances(InstanceIds=ins_list)['Reservations'][0]['Instances'][0]['InstanceType']
    
    print("[ID] " + instance_id + ", [Instance Type] " + instance_type + ", [CPU Credits] " + credits['InstanceCreditSpecifications'][0]['CpuCredits'])


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
    # 실행중이거나, 멈춰있는 인스턴스의 개수 총합 (terminated는 포함하지 아니한다)
    all_instance_count = len(running_instances()) + len(terminated_instances())
    running_instances_list = running_instances()

    # 총 인스턴스가 요구된 인스턴스보다 적으면 추가로 인스턴스 생성
    while desired_instances_count > all_instance_count:
        print(f'인스턴스 개수가 모자라 {desired_instances_count - all_instance_count} 개의 인스턴스를 추가 생성합니다')
        image_list = list_images()
        create_instance(image_list[0])
        all_instance_count += 1

    if desired_instances_count > len(running_instances_list):
        # 원하는 수가 실행 중인 수보다 크면 부족한 만큼의 인스턴스를 시작합니다.
        print(f'{desired_instances_count - len(running_instances_list)} 개의 인스턴스를 추가 실행 합니다.')
        instances_to_start = desired_instances_count - len(running_instances_list)
        terminated_instances_list = terminated_instances()[:instances_to_start]
        ec2.start_instances(InstanceIds=terminated_instances_list)

    elif desired_instances_count < len(running_instances_list):
        # 실행 중인 수가 원하는 수보다 크면 초과한 만큼의 인스턴스를 중지합니다.
        print(f'{len(running_instances_list) - desired_instances_count} 개의 인스턴스를 종료합니다.')
        instances_to_stop = len(running_instances_list) - desired_instances_count
        instances_to_stop_list = running_instances_list[:instances_to_stop]
        ec2.stop_instances(InstanceIds=instances_to_stop_list)

    else:
        print('현재 인스턴스 개수가 원하는 수와 같습니다')

    list_instances()

# 인스턴스 용량 정보 출력
def storage_info(instance_id):
    print("Fetching storage information...")
    ins_list = [instance_id]

    try:
        # 스토리지 정보 확인
        storage_info = ec2.describe_instance_attribute(InstanceId=instance_id, Attribute='blockDeviceMapping')
        block_devices = storage_info['BlockDeviceMappings']

        print(f"[ID] {instance_id}, Storage Information:")
        for device in block_devices:
            device_name = device['DeviceName']
            ebs_info = device['Ebs']
            volume_id = ebs_info['VolumeId']
            volume_size = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]['Size']

            # 디바이스 이름, 볼륨 id 볼륨 사이즈에 대한 정보를 출력한다
            print(f"  - Device: {device_name}, Volume ID: {volume_id}, Volume Size: {volume_size} GB")
    except Exception as e:
        print(f"Error fetching storage information: {e}")

def modify_instance_type():
    instance_id = input("Enter the instance ID: ")
    new_instance_type = input("Enter the new instance type (e.g., t3.nano): ")

    try:
        # 현재 인스턴스 유형 확인
        current_instance_type = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['InstanceType']
        print(f"Current instance type: {current_instance_type}")

        # 인스턴스 유형 변경
        response = ec2.modify_instance_attribute(
            InstanceId=instance_id,
            InstanceType={'Value': new_instance_type}
        )
        print(f"Instance type modified successfully. New instance type: {new_instance_type}")
        
        # 기존 인스턴스 유형에서 새로운 인스턴스 유형으로 변경되었다는 메시지 출력
        print(f"기존 인스턴스 {current_instance_type} 에서 {new_instance_type} 로 변경되었습니다")
        
        # 추가로 다른 정보 출력 등의 작업 수행 가능

        ins_credit(instance_id)
    except Exception as e:
        print(f"Error modifying instance type: {e}")

# 볼륨 사이즈 변경하는 함수
def modify_volume_size():
    volume_id = input("Volume ID:")
    new_size_gb = int(input("New size GB:"))  # 문자열을 정수로 변환

    try:
        response = ec2.modify_volume(
            VolumeId=volume_id,
            Size=new_size_gb
        )
        print("Volume size modified successfully:", response)
    except Exception as e:
        print(f"Error modifying volume size: {e}")

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
    print(" 13. storage info                14. modify instance type   ")
    print(" 15. modify volume size          99. quit                   ")
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
    elif number == 13:
        instance_id = input("Enter instance id: ")
        storage_info(instance_id)
    elif number == 14:
        modify_instance_type()
    elif number == 15:
        modify_volume_size()
    elif number == 99:
        print("Goodbye!")
        break
    else:
        print("Invalid input!")
