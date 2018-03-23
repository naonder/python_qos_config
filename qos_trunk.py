#!/usr/bin/env python3

import netmiko
import datetime
import getpass

"""Used to setup QoS on switches including applying policies to trunk and access ports. This will determine
which form of QoS to use (MQC vs. MLS) based on the output from "show version"."""

# Note, this needs to be looked at again and heavily refactored!

name = input("Input your username: ")
passwrd = getpass.getpass("Input your password: ")
ios = "cisco_ios"

log_file = open("/path/to/logfile.txt", "a")
device_list = open("/path/to/device/list.txt", "r")

netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                      netmiko.ssh_exception.NetMikoAuthenticationException)

start_time = datetime.datetime.now()
for device in device_list:

    try:
        connect = netmiko.ConnectHandler(username=name, password=passwrd, device_type=ios, ip=device)

        # Check if running regular IOS(MLS QOS) or IOX-XE(MQC QOS)
        connect.send_command("terminal length 0")
        show_version = connect.send_command("show version")
        version_line = show_version.splitlines()[0]

        if "XE Software" in version_line:
            # Utilitze MQC QOS syntax
            mqcqos_file = "/path/to/file/for/mqcqos/contect.txt"
            connect.send_command("send log 5 Starting QoS config.")
            print(device)
            print("Sending MQC QoS config now...")
            mqc_qos = connect.send_config_from_file(mqcqos_file)
            print("MQC QoS config finished.")
    
            # Initialize a blank config and a trunk/routed interface list
            config = []
            interface_list = connect.send_command("sh int status | i what|you|need")
            lines = interface_list.splitlines()
    
            # Go through each interface and add to a "running" interface config
            for line in lines:
                interface = line.split()[0]
                config.append("interface " + interface)
                config.append(" service-policy output EGRESS-POLICE-1G")
                config.append("!")
            "\n".join(config)
            print("Configuring trunks and routed interfaces...")
            connect.send_config_set(config)
            print("Finished configuring trunks and routed interfaces")
    
            # Same as above, but this time w/ only access or non server ports
            config = []
            interface_list = connect.send_command("sh int status | e access|ports|etc.")
            lines = interface_list.splitlines()[1:]
            for line in lines:
                interface = line.split()[0]
                config.append("interface " + interface)
                config.append(" no auto qos voip cisco-phone")
                config.append(" no auto qos trust cos")
                config.append(" service-policy output EGRESS-POLICE-1G")
                config.append(" service-policy input INGRESS-POLICE-1G")
            "\n".join(config)
            print("Configuring all other interfaces...")
            connect.send_config_set(config)
            print("Finished configuring final interfaces")
    
            connect.send_command("send log 5 Finished QoS config")
            connect.send_command("write mem")
    
        else:
            # Utilize MLS QOS syntax
            qos_file = "/path/to/file/for/mlsqos/contect.txt"
    
            connect.send_command("send log 5 Starting QoS config.")
            print(device)
            print("Sending MLS QoS config now...")
            mls_qos = connect.send_config_from_file(qos_file)
            print("MLS QoS config finished.")
    
            # Rest of the script is similar to above except different CLI syntax
            config = []
            interface_list = connect.send_command("sh int status | i what|you|need")
            lines = interface_list.splitlines()
            for line in lines:
                interface = line.split()[0]
                config.append("interface " + interface)
                config.append(" srr-queue bandwidth share 1 30 35 5")
                config.append(" priority-queue out")
                config.append(" mls qos trust dscp")
                config.append("!")
            "\n".join(config)
            print("Configuring trunks and routed interfaces...")
            connect.send_config_set(config)
            print("Finished configuring trunks and routed interfaces.")
    
            config = []
            interface_list = connect.send_command("sh int status | e access|ports|etc.")
            lines = interface_list.splitlines()[1:]
            for line in lines:
                interface = line.split()[0]
                config.append("interface " + interface)
                config.append(" srr-queue bandwidth share 1 30 35 5")
                config.append(" priority-queue out")
                config.append(" mls qos trust dscp")
                config.append(" service-policy input INGRESS-POLICE-1G")
                config.append("!")
            "\n".join(config)
            print("Configuring all other interfaces...")
            connect.send_config_set(config)
            print("Finished configuring final interfaces.")
    
            connect.send_command("send log 5 Finished QoS config")
            connect.send_command("write mem")
        
    except netmiko_exceptions as e:
        print("Failed to {}, {}".format(device, e))
        log_file.write("Failed to {}, {}".format(device, e))
        log_file.write("\r\n")
        continue

    connect.disconnect()
device_list.close()
log_file.close()
end_time = datetime.datetime.now()
total_time = end_time - start_time
print(total_time)
