import boto3
import os

aws_access_key_id = os.environ.get("AccessID")
aws_secret_access_key = os.environ.get("AccessKey")
region_name = 'eu-north-1'  # 사용하려는 AWS 리전을 지정하세요

# AWS 클라이언트 생성
ec2 = boto3.client('ec2', region_name=region_name, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


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
    print(f"Starting .... {instance_id}")
    ec2.start_instances(InstanceIds=[instance_id])
    print(f"Successfully started instance {instance_id}")

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
        InstanceType='t2.micro',
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
    filters = [{'Name': 'name', 'Values': ['htcondor-slave-image']}]
    images = ec2.describe_images(Filters=filters)
    for image in images['Images']:
        print(f"[ImageID] {image['ImageId']}, [Name] {image['Name']}, [Owner] {image['OwnerId']}")

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
    elif number == 99:
        print("Goodbye!")
        break
    else:
        print("Invalid input!")
