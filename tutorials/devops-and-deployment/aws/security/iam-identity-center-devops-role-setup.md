# Tutorial: Setting Up IAM Identity Center Group and Permission Set for AWS Infrastructure

## Overview 🎯🛠️✅

This tutorial guides **DevOps Engineers** through setting up **AWS IAM Identity Center (AWS SSO) groups and permission sets** for managing infrastructure components such as **Amazon MSK, PostgreSQL, Databricks, and AWS Database Migration Service (DMS)**. This setup ensures secure access control, role-based permissions, and efficient team collaboration.

📌 *Before proceeding, ensure you have administrative access to AWS IAM Identity Center.*

---

## **Step 1: Create an IAM Identity Center Group for DevOps Engineers** 👥🔑

To manage AWS infrastructure securely, create an **IAM Identity Center group** specifically for **DevOps Engineers**.

### **Steps to Create an IAM Identity Center Group:**
1. **Sign in to AWS IAM Identity Center** via `company-name.awsapps.com/start`.
2. Navigate to **IAM Identity Center (AWS SSO)**.
3. In the left menu, select **Groups**.
4. Click **Create Group**.
5. **Enter a Group Name** (e.g., `DevOpsEngineers`).
6. **Enter a Description** (e.g., `Group for DevOps engineers managing AWS infrastructure`).
7. **Add Users** who need access.
8. Click **Create Group**.

📌 *This ensures that only authorized DevOps engineers have access to manage AWS resources securely.*

---

## **Step 2: Create a Permission Set for DevOps Infrastructure Access** 🔑🛠️

To grant DevOps engineers the necessary permissions to manage AWS infrastructure, create a **custom permission set**.

### **Steps to Create a Permission Set:**
1. Navigate to **IAM Identity Center (AWS SSO)** → **Permission Sets**.
2. Click **Create permission set**.
3. Select **Custom permission set**.
4. Under **Inline policy**, paste the following **JSON policy** to grant access to MSK, RDS (PostgreSQL), Databricks, and DMS:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudshell:CreateEnvironment",
                "cloudshell:GetEnvironmentStatus",
                "cloudshell:CreateSession",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "kafka:DescribeCluster",
                "kafka:GetBootstrapBrokers",
                "kafka:ListClusters",
                "rds:DescribeDBInstances",
                "rds:ListTagsForResource",
                "rds:ModifyDBInstance",
                "dms:DescribeReplicationInstances",
                "dms:DescribeEndpoints",
                "dms:CreateReplicationTask",
                "dms:ModifyReplicationTask",
                "cloudshell:DescribeEnvironments",
                "cloudshell:DeleteEnvironment"
            ],
            "Resource": "*"
        }
    ]
}
```

5. Click **Next**, then name the **permission set**: `DevOpsEngineers`. Remember this is the permission set user will see in the AWS Portal at `company-name.awsapps.com/start`.
6. **Enter a Description** (e.g., `Permission set for DevOps engineers managing AWS MSK, RDS, Databricks, DMS, and others.`).
7. Set **Session Duration** (Recommended: 1 hour for security compliance).
8. Click **Review Policy**, name the policy **DevOpsInfraPolicy**, and click **Create Policy**.
9. Click **Create** to finalize the permission set.

📌 *This permission set ensures that DevOps engineers have controlled access to AWS services relevant to infrastructure management.*

---

## **Step 3: Assign the Permission Set to an AWS Account** 🔄🔑

After creating the `DevOpsEngineers` permission set, assign it to an AWS account and link it to the `DevOpsEngineering` group.

### **Steps to Assign the Permission Set:**
1. Navigate to **IAM Identity Center (AWS SSO)** → **AWS Accounts**.
2. Select the **AWS account** where the permission set should be applied.
3. Click **Assign Users or Groups**.
4. Search for and select the **DevOpsEngineers** group.
5. In the **Permission sets** section, select **DevOpsEngineers**.
6. Click **Next**.
7. Click **Submit**.
8. Wait for the status to change to **Provisioned**.

📌 *This ensures that users in the `DevOpsEngineers` group have secure and controlled access to AWS resources.*

---

## Conclusion 🎉🚀✅

By following this tutorial, **DevOps Engineers** have successfully set up **IAM Identity Center groups and permission sets** for managing AWS infrastructure, ensuring **secure, role-based access to MSK, PostgreSQL, Databricks, and AWS DMS**.

Regularly review and update permissions to align with **security best practices** that conform with **least privilege** principles. This setup enhances **security compliance** and **organizational requirements**.

**Happy Deploying! 🚀🔧**

