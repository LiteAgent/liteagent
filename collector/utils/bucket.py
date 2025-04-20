# utils/bucket_utils.py

import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import json
import logging

logger = logging.getLogger(__name__)


class Uploader:
    def __init__(self):
        self.use_s3 = all(
            [
                os.getenv("S3_BUCKET_NAME"),
                os.getenv("AWS_ACCESS_KEY_ID"),
                os.getenv("AWS_SECRET_ACCESS_KEY"),
            ]
        )
        if self.use_s3:
            self.s3_bucket = os.getenv("S3_BUCKET_NAME")
            try:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
                # Verify credentials by listing buckets
                self.s3_client.list_buckets()
                logger.info("Successfully connected to S3.")
            except NoCredentialsError:
                logger.error("AWS credentials not available.")
                self.use_s3 = False
            except ClientError as e:
                logger.error(f"Failed to connect to S3: {e}")
                self.use_s3 = False
        else:
            logger.info("S3 environment variables not set. Using local uploader.")

    def save_data(
        self, data: bytes, s3_path: str, content_type: str = "application/octet-stream"
    ):
        """
        Save data directly to S3 or locally based on configuration.

        :param data: Data to be saved.
        :param s3_path: Path in S3 bucket where the data should be saved.
        :param content_type: MIME type of the data.
        """
        if self.use_s3:
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_path,
                    Body=data,
                    ContentType=content_type,
                )
                logger.info(
                    f"Uploaded data to S3 bucket '{self.s3_bucket}' at '{s3_path}'"
                )
            except (NoCredentialsError, ClientError) as e:
                logger.error(f"Failed to upload data to S3: {e}")
        else:
            # Save locally
            local_path = os.path.join(
                os.getcwd(), s3_path
            )  # Adjust base directory as needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            logger.info(f"Saved data locally at '{local_path}'")

    def save_text(self, text: str, s3_path: str):
        """
        Save text data directly to S3 or locally based on configuration.

        :param text: Text data to be saved.
        :param s3_path: Path in S3 bucket where the text should be saved.
        """
        self.save_data(text.encode("utf-8"), s3_path, content_type="text/plain")

    def save_json(self, obj: dict, s3_path: str):
        """
        Save JSON data directly to S3 or locally based on configuration.

        :param obj: JSON-serializable dictionary to be saved.
        :param s3_path: Path in S3 bucket where the JSON should be saved.
        """
        json_bytes = json.dumps(obj, indent=4).encode("utf-8")
        self.save_data(json_bytes, s3_path, content_type="application/json")

    def save_html(self, html_content: str, s3_path: str):
        """
        Save HTML content directly to S3 or locally based on configuration.

        :param html_content: HTML content to be saved.
        :param s3_path: Path in S3 bucket where the HTML should be saved.
        """
        self.save_data(html_content.encode("utf-8"), s3_path, content_type="text/html")

    def save_python_script(self, script_content: str, s3_path: str):
        """
        Save Python script directly to S3 or locally based on configuration.

        :param script_content: Python script content to be saved.
        :param s3_path: Path in S3 bucket where the script should be saved.
        """
        self.save_data(
            script_content.encode("utf-8"), s3_path, content_type="text/x-python"
        )


# Initialize a global uploader instance
uploader = Uploader()


def save_data(
    data: bytes, s3_path: str, content_type: str = "application/octet-stream"
):
    uploader.save_data(data, s3_path, content_type)


def save_text(text: str, s3_path: str):
    uploader.save_text(text, s3_path)


def save_json(obj: dict, s3_path: str):
    uploader.save_json(obj, s3_path)


def save_html(html_content: str, s3_path: str):
    uploader.save_html(html_content, s3_path)


def save_python_script(script_content: str, s3_path: str):
    uploader.save_python_script(script_content, s3_path)
