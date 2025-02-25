# Tutorial: Setting Up a Permission Set for KMS Security Team in AWS IAM Identity Center

## Overview 🎯🔐✅

This tutorial walks you through setting up **a secure permission set** for managing AWS Key Management Service (KMS) keys using **AWS IAM Identity Center (AWS SSO)**. You will create an **IAM Identity Center group**, assign it a **permission set**, and link it to an **IAM role** with KMS administrative privileges.

📌 *Before proceeding with this tutorial, you must first complete the setup in the tutorial: **`setup-first-admin-iam-identity-center.md`**

## KMS Administrators 🔑🔍🛡️

KMS administrators are responsible for managing encryption keys within AWS KMS. They ensure proper access controls, key rotation policies, and security compliance for cryptographic operations. KMS administrators should have **least privilege access** and should be restricted to managing keys rather than using them for encryption/decryption operations. Their responsibilities include:

- Creating, enabling, and disabling keys.
- Managing key policies and permissions.
- Scheduling and canceling key deletions.
- Monitoring key usage through AWS CloudTrail.
- Ensuring compliance with security policies and audits.

### **Step 1: Create an IAM Identity Center KMS-Administrators Group** 👥🏢🔑

To manage AWS KMS keys effectively, you need to create an IAM Identity Center group specifically for KMS administrators. This group will be assigned necessary permissions via a permission set.

1. **Sign in using the AWS access portal** `company-name.awsapps.com/start`.
2. Navigate to **IAM Identity Center (AWS SSO)**.
3. In the left menu, select **Groups**.
4. Click **Create Group**.
5. **Enter a Group Name** (e.g., `KMS-Administrators`).
6. **Enter a Description** (optional but recommended). This should clearly state the purpose of the group, such as 'Group for administrators managing KMS encryption keys'. This helps with organization and clarity.
7. **Add Users** who need administrative access to KMS.
8. Click **Create Group**.

📌 *This group ensures that only authorized administrators have access to manage KMS keys securely and in alignment with best practices.*.

---

### **Step 2: Create a Permission Set and Add Inline KMS Admin Permissions** 🔑💾🛠️ 👥🏢🔑 🔑💾🛠️ 🔑💾🛠️

To ensure KMS administrators have direct access to manage encryption keys, you need to create a **Permission Set** in IAM Identity Center and add an **inline policy** for KMS administration. This ensures that permissions are consistently applied across identity-based access and role-based access control mechanisms. By using inline policies, we keep the permissions centralized within the permission set and prevent exhausting the limit of custom policies, ensuring better management and scalability.

#### Steps to Create a Permission Set and Add Inline KMS Access:

1. Navigate to **IAM Identity Center (AWS SSO)** → **Permission Sets**.
2. Click **Create permission set**.
3. Select **Custom permission set**.
4. Under **Inline policy**, paste the following **JSON policy**.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:CreateKey",
                "kms:DescribeKey",
                "kms:EnableKey",
                "kms:DisableKey",
                "kms:ScheduleKeyDeletion",
                "kms:CancelKeyDeletion",
                "kms:ListAliases",
                "kms:TagResource",
                "kms:PutKeyPolicy",
                "kms:GetKeyPolicy",
                "tag:GetResources",
            ],
            "Resource": "*"
        }
    ]
}
```

11. Click **Next**, then name the **permission set**: `SecurityTeam-KMS-Administrators`. Keep in mind that this is the permission the user will see in the AWS Portal at `company-name.awsapps.com/start`.

12. **Enter a Description** (optional but recommended). This should clearly state the purpose of the **permission set**, such as `Custom permission set for administrators managing KMS encryption keys.` Keeping permissions centralized within the **permission set** ensures easier access control and scalability while preventing exhaustion of the custom policy limit.

13. Set Session Duration (Recommended: 1 hour for security reasons).

    Click **Review Policy**, name the policy **KMSAdminInlinePolicy**, and click **Create Policy**.

14. Click **Create** to finalize the permission set.

📌 *This ensures that KMS administrators have precise and restricted access tailored to the organization's security requirements.*

---

### **Step 3: Provision the Permission Set by Assigning It to an AWS Account** 🔑🔄🛠️

After creating the **KMS-Admin-PermissionSet**, you need to provision it by assigning it to an AWS account and linking it to the **KMS-Administrators** group.

#### Steps to Provision the Permission Set:

1. Navigate to **IAM Identity Center (AWS SSO)** → **AWS Accounts**.
2. Select the **AWS account** where you want to grant KMS administrative access.
3. Click **Assign Users or Groups**.
4. Search for and select the **KMS-Administrators** group.
5. In the **Permission sets** section, search for and select **KMS-Admin-PermissionSet**.
6. Click **Next**.
7. Click **Submit**.
8. Wait for the status to change to **Provisioned**, indicating that the assignment is complete.

📌 *This ensures that users in the **************************************`KMS-Administrators`************************************** group have access to manage KMS resources within the assigned AWS account.*

---

## **🎯 Final Verification** ✅🔍🛠️

- Log in as an **Identity Center user** from `company-name.awsapps.com/start`.
- Under **AWS Accounts**, select the account where the `SecurityTeam-KMS-Administrators` group is provisioned.
- Test permissions by trying to **create, describe, and manage KMS keys**.

## Conclusion 🎉🔐✅

By following this tutorial, you have successfully set up a secure permission set for your KMS administrators using AWS IAM Identity Center. This setup ensures that your KMS administrators have the necessary permissions to manage encryption keys while adhering to the principle of least privilege. Regularly review and update permissions to maintain security compliance and adapt to any changes in your organization's requirements.

Thank you for completing this tutorial! If you have any questions or need further assistance, refer to the AWS documentation or reach out to your AWS support team.

Happy securing! 🚀🔒

