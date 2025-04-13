# Setting Up a  Private Provisioned MSK with Quick Create in AWS

## 1. Ensure Two Private Subnets are Available

To create a Serverless MSK, AWS requires at least two **private** subnets in different Availability Zones.

### Steps to Verify or Create Private Subnets

1. **Go to the AWS Console** > Navigate to **VPC**.

2. **Check Existing Subnets:**

   - Under **Your VPCs**, identify the VPC where you want to set up MSK.
   - Click **Subnets** in the left panel.
   - Ensure at least **two private subnets** exist in **different availability zones**, which is crucial for **high availability, fault tolerance, and disaster recovery**. Distributing resources across multiple AZs ensures that failures in one zone do not disrupt the entire system, enhances load balancing, and improves resilience against outages.
   - If they exist, verify that they **do not have an internet gateway or NAT gateway**.

3. **Create Private Subnets (if necessary):**

   - Click **Create Subnet**.
   - Select your **VPC**.
   - Choose an **availability zone**.
   - Assign a **CIDR block** (e.g., `10.0.1.0/24` and `10.0.2.0/24`).
   - Repeat to create a second subnet in a different availability zone.

4. **Ensure No Internet Access for Private Subnets:**

   - Click on each subnet and check the **Route Table**.
   - Ensure it **does not contain routes to an internet gateway or NAT gateway** by following these steps:
     - In the `Route Table` section, examine the destination column and ensure that there is no `0.0.0.0/0` entry, as this route directs traffic to the internet, compromising the private nature of the subnet.
     - If the subnet is linked to a public route table, navigate to **Edit route table association** and under **Subnet route table settings**, switch it to a private route table to ensure no direct internet access.

## 3. Create Development Provisioned MSK Cluster with Quick Create

AWS provides a **Quick Create** option to set up a **Serverless MSK** cluster with minimal configuration.

### Steps to Create MSK Serverless

1. **Go to the AWS Console** > Navigate to **Amazon MSK**.
2. **Click "Create Cluster"**.
3. **Choose "Quick create"**.
4. **Configure the Cluster:**
   - **Cluster name**: Choose a descriptive name (e.g., `msk-silveraiwolf-useast1-cluster-private`). It is good practice to include the region in the naming convention to quickly identify in which region the cluster is deployed.
   - **Cluster type**: Select **Provisioned**.
   - Apache Kafka version: Select recommended
   - Standard brokers: Select kafka.t3.small. Development provisioned clusters are generally more cost-effective compared to serverless, making them a better option for budget-conscious deployments. See pricing: [MSK Pricing]\([https://aws.amazon.com/msk/pricing/](https://aws.amazon.com/msk/pricing/))
   - Storage: Use 1 GiB for testing.
   - Ensure that your **Default VPC** contains at least two private subnets, each located in a different Availability Zone, to avoid conflicts and enhance redundancy.
5. **Click "Create Cluster"** and wait for the cluster to be provisioned (this can take a few minutes).

## 5. Test the MSK Cluster

To test the MSK cluster, create an **EC2 instance** within the same VPC and subnets:

1. **Launch an EC2 Instance** in one of the private subnets by following these steps:
   1. **Go to the AWS Console** and navigate to **EC2**.
   2. Click **Launch Instance**.
   3. Enter a name for your instance (e.g., `ec2-silveraiwolf-msk-instance`).
   4. Select an **Amazon Machine Image (AMI)**, such as Amazon Linux 2.
   5. Choose an **instance type**, such as `t2.micro` for testing.
   6. Under **Key Pair**, select `Proceed without a key pair` if you do not have an existing key pair.
   7. In **Network settings**, choose the same **VPC** as the MSK cluster and place it in one of the **private subnets**.
   8. **Disable auto-assign public IP** to ensure it remains private.
   9. Adjust the **security group** to allow inbound traffic from the VPC for Kafka communication.
   10. Click **Launch Instance** and wait for it to initialize.
   11. Once running, connect using SSH from another instance within the same VPC or through AWS Systems Manager Session Manager if configured.
2. **Install Apache Kafka Client**:
   ```bash
   sudo yum install -y java-1.8.0-openjdk
   wget https://downloads.apache.org/kafka/2.8.1/kafka_2.13-2.8.1.tgz
   tar -xvzf kafka_2.13-2.8.1.tgz
   cd kafka_2.13-2.8.1
   ```
3. **List Topics to Verify Connection**:
   ```bash
   bin/kafka-topics.sh --list --bootstrap-server <msk-bootstrap-broker>
   ```
   If the connection is successful, you should see a list of Kafka topics.

## 6. Conclusion

You have successfully set up a **Serverless MSK cluster with Quick Create** in AWS using **private subnets with no internet access**. Your Kafka cluster is now ready for secure, internal communication within your AWS environment.



