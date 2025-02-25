# Setting Up the First Admin User from Root User in IAM Identity Center (AWS SSO)

## Why Set Up an Admin User Instead of Using the Root Account? 🚫🔑

Setting up an admin user allows for safer and more manageable account administration while ensuring security and compliance.

The AWS root user has unrestricted access to all resources and settings within an AWS account, making it a critical security risk if compromised. Best practices recommend setting up an admin user through IAM Identity Center to minimize risk and implement proper access controls. By creating a dedicated admin user, you can:

- **Enhance security**: Reduce exposure of root credentials and enforce multi-factor authentication (MFA).
- **Improve access control**: Assign only necessary permissions to administrators instead of using unrestricted root access.
- **Enable better auditing**: Track activities performed by specific users rather than using the root account for all administrative tasks.
- **Follow AWS best practices**: AWS strongly recommends avoiding routine use of the root account.

Setting up an admin user allows for safer and more manageable account administration while ensuring security and compliance.

## Why Use IAM Identity Center for Human Users Instead of IAM Users? 🤔👥

Use AWS IAM Identity Center instead of standard IAM when you need a centralized way to manage user access across multiple AWS accounts within an organization, providing a single sign-on experience and simplifying identity management, especially when dealing with a large number of accounts or applications beyond just AWS services; essentially, IAM Identity Center offers a more streamlined approach for managing workforce access across various cloud applications, while standard IAM is better for managing access within a single AWS account. 

Key differences:
- Multi-account management: IAM Identity Center allows you to manage user access across all accounts within an AWS Organization, whereas standard IAM is primarily focused on managing access within a single account. 

- Single Sign-On (SSO): IAM Identity Center provides a unified SSO experience for users to access various applications and AWS accounts with a single set of credentials, while standard IAM does not offer this built-in functionality. 

- Centralized Identity Source: With IAM Identity Center, you can connect to your existing identity provider (like Active Directory) and use it to manage user access across your AWS environment. 

## Note on Permission Sets

In this tutorial, we are setting up the `AdministratorAccess` permission set for simplicity. However, best practices recommend creating a **custom permission set** that follows the **principle of least privilege**. This means granting users only the permissions they need to perform their tasks, reducing security risks and limiting potential damage in case of compromised credentials.

## Prerequisites

- A free AWS account with IAM Identity Center (AWS SSO) enabled.
- Access to the AWS root user account.

## Step 1: Enable IAM Identity Center 🚀🔐

1. Sign in to the AWS Management Console using the **root user**.
2. Navigate to **IAM Identity Center**.
3. Click **Enable IAM Identity Center** if it is not already enabled.

## Step 2: Create the First Admin User 👤🔧

1. In the **IAM Identity Center** console, go to **Users**.
2. Click **Create user**.
3. Enter user details:
   - **Username** (e.g., `admin`)
   - **Email address**
   - **First and last name**
4. (Optional) Set up **phone number** for multi-factor authentication (MFA). This is critical for both production and development environments to enhance security and prevent unauthorized access. However, configuring MFA is beyond the scope of this tutorial.
5. Click **Next**. ✅

## Step 3: Create an Admin Group and Assign the First Admin User 👥🔧

1. Navigate to **Groups** in the left navigation pane.
2. Click **Create group**.
3. Enter a **Group name** (e.g., `Administrators`).
4. (Optional) Add a **Description**.
5. From the **Add users to group** section:
   1. Select the newly created admin user.
6. Click **Create group**. ✅

## Step 4: Assign AWS Accounts to the Admin Group 🗂️🔑

1. Navigate to **IAM Identity Center** > **AWS accounts**.
2. Select the AWS account where you want to assign access.
3. Click on **Assign users or groups**.
4. Choose the **Groups** tab. Assigning permissions to groups rather than individual users is a best practice because it simplifies access management, ensures consistency, and reduces administrative overhead. By managing access at the group level, you can easily onboard and offboard users while maintaining security and compliance.
5. Select the **Administrators** group.
6. Click **Next**.
7. Select a **Permission Set** (or create one, as described in Step 5).
8. Click **Finish** to assign access. ✅

## Step 5: Create a Permission Set for Admin Access 🛠️🔑

1. Navigate to **IAM Identity Center** > **Permission sets**.
2. Click **Create permission set**.
3. Choose **Predefined AWS managed policies**.
4. Select `AdministratorAccess` to grant full permissions.
5. Configure session settings (optional):
   - Set session duration (e.g., `1 hour`, `12 hours`).
   - Enable or disable access to AWS Management Console and CLI/API.
6. Click **Next**. ✅
7. Review settings and click **Submit**. 📋

## Step 6: Configure AWS Access Portal URL 🌐🔧

1. Navigate to **IAM Identity Center** > **Settings**.
2. Locate the **Identity Source** section.
3. Click **Actions** to modify the URL to a more user-friendly name.
4. Click on **Customize AWS access portal URL**.
5. Enter a unique, meaningful name (e.g., `company-name.awsapps.com`).
6. Click **Save changes**. ✅

## Step 7: Test Admin User Access 🧪🔍

1. Have the admin user go to `company-name.awsapps.com/start` and sign in. 🌐🔑
2. Ensure they can assume the correct role and access designated AWS accounts with administrator privileges. ✅
3. If access is incorrect, review group assignments and permission sets. 🔄🔧

## Conclusion

By following these steps, you can securely set up the first admin user from the root user in IAM Identity Center. This ensures a structured and scalable access control strategy for managing AWS resources efficiently.

