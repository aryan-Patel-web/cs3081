import boto3, os
s3 = boto3.client("s3", endpoint_url="http://localhost:8333", aws_access_key_id="minio", aws_secret_access_key="minio123", region_name="us-east-1")
for b in ["datasets", "models"]:
    try:
        s3.create_bucket(Bucket=b)
        print("created bucket", b)
    except Exception as e:
        print(b, e)
def up(local, bucket, key):
    s3.upload_file(local, bucket, key)
    print("uploaded", bucket, key)
up("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
up("datasets/v1/train.jsonl", "datasets", "v1/train.jsonl")
for f in os.listdir("models/v1"):
    up(f"models/v1/{f}", "models", f"v1/{f}")
for f in os.listdir("models/v2"):
    up(f"models/v2/{f}", "models", f"v2/{f}")
print("done")
