# Setting Up AWS Bedrock Access (For Newcomers to AWS)

This project's live agent calls Amazon Bedrock. If you've never worked with
an AWS account, IAM, or the AWS CLI before, this walks through every step.
If you already have Bedrock access configured, you can skip straight to
[README.md](README.md)'s Setup section.

**Do you even need this?** Only if you want to run the *live* agent
(`python main.py "..."`). `python evaluation.py` needs no AWS account, no
credentials, and no model access at all — it's a deterministic check that
runs entirely offline.

---

## 1. Get an AWS account

If you don't already have one, create a standard AWS account at
[aws.amazon.com](https://aws.amazon.com). Any account works — this doesn't
need to be special-purpose.

## 2. Create an IAM user with Bedrock access

Don't use your account's root credentials for this. Create a dedicated IAM
user instead:

1. Open the **IAM console** → **Users** → **Create user**. Give it a name
   like `bedrock-demo-user`.
2. Leave "Provide user access to the AWS Management Console" **unchecked** —
   you only need programmatic (API/CLI) access, not a console login.
3. On the permissions step, choose **"Attach policies directly"**, then
   either:
   - **Fast path:** search for and attach the AWS-managed policy
     `AmazonBedrockFullAccess`. Broader than needed, but quick.
   - **Least-privilege path (recommended):** click **"Create policy"**,
     switch to the **JSON** tab, and paste this in:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Sid": "BedrockInvoke",
           "Effect": "Allow",
           "Action": [
             "bedrock:InvokeModel",
             "bedrock:InvokeModelWithResponseStream"
           ],
           "Resource": "*"
         },
         {
           "Sid": "BedrockDiscovery",
           "Effect": "Allow",
           "Action": [
             "bedrock:ListFoundationModels",
             "bedrock:ListInferenceProfiles",
             "bedrock:GetFoundationModel"
           ],
           "Resource": "*"
         }
       ]
     }
     ```
     Name it something like `bedrock-invoke-policy`, create it, then go back
     and attach it to your user.
4. Finish creating the user.

## 3. Generate an access key

1. Open the user you just created → **Security credentials** tab.
2. Scroll to **Access keys** → **Create access key**.
3. Choose **"Command Line Interface (CLI)"** as the use case, confirm, and
   create it.
4. You'll see an **Access Key ID** and a **Secret Access Key** — this is the
   only time the secret is shown. Copy both somewhere safe now.

**Never paste these into a chat window, an AI assistant, a committed file,
or anywhere else that isn't your local credential store.** If a key ever
does leak, deactivate and delete it in the IAM console immediately and
generate a new one.

## 4. Install the AWS CLI

- **macOS:** `brew install awscli`
- **Linux/Windows:** see
  [AWS's official install instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

## 5. Configure a named profile

In your own terminal (not through any AI assistant):
```
aws configure --profile bedrock-demo
```
It prompts for:
- **AWS Access Key ID** — from step 3
- **AWS Secret Access Key** — from step 3
- **Default region name** — e.g. `us-east-1` (needs to be a region where your
  chosen model is enabled — see step 7)
- **Default output format** — `json` is fine

## 6. Verify the credentials work

```
aws sts get-caller-identity --profile bedrock-demo
```
Should print your account id and the user's ARN. If it errors, re-check the
access key/secret you entered in step 5.

## 7. Confirm the model is enabled in your region

```
aws bedrock list-inference-profiles --region us-east-1 --profile bedrock-demo
```
Look for the model id in `.env.example`'s `BEDROCK_MODEL_ID`
(`us.anthropic.claude-haiku-4-5-20251001-v1:0` by default) with
`"status": "ACTIVE"`. If it's missing, either try a different region or pick
a different model id that is enabled for your account.

## 8. Point this project at your profile

Copy the env template if you haven't already:
```
cp .env.example .env
```
Then either export the profile for your shell session:
```
export AWS_PROFILE=bedrock-demo
```
or add it directly to `.env`:
```
AWS_PROFILE=bedrock-demo
```
Make sure `.env`'s `AWS_REGION` matches the region you verified in step 7.

## Common pitfalls

- **A shell-level `AWS_REGION` silently wins over `.env`.** This project's
  `.env` loader only sets a variable if it isn't already set in your shell.
  If you have `AWS_REGION` exported somewhere in your shell profile already
  (check with `echo $AWS_REGION`), that value is used instead of `.env`'s —
  even though nothing on screen tells you that's happening. If your model
  works in one region but `.env` says another, this is almost always why.
- **Static access keys don't expire like SSO session tokens do**, but they
  can be deactivated by an administrator or rotated out. If `aws sts
  get-caller-identity` suddenly fails after previously working, check
  whether the key is still active in the IAM console before assuming
  anything else is wrong.
- **Model ids get retired.** If you hit `ResourceNotFoundException`, the
  model id in `.env` may no longer exist — rerun the `list-inference-profiles`
  command from step 7 to find a current one.

## When you're done

If this was a throwaway setup (a demo, a one-off test), clean up afterward:
delete the access key and the IAM user in the console, and remove the local
profile from `~/.aws/credentials` and `~/.aws/config`.
