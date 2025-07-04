import argparse
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from loguru import logger
import argparse
import os
import random
import time

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from videogeneration.config import TOKEN_FILE, SCOPES
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib2.ServerNotFoundError,)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 10

def get_authenticated_service():
    logger.info("Getting creds")
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        logger.info("Found authorization file")
    else:
        logger.warning("No token file found")
        raise ValueError("No token file found")
    if creds:
        logger.debug(f"Does creds valid? {creds.valid}")

    
    return build("youtube", "v3", credentials=creds)

def upload_video(file_path, title, category="1", privacy="public", madeForKids=False, description="", defaultAudioLanguage="RU", defaultLanguage="RU"):
    logger.info(f"Starting uploading video {file_path} with title {title} to category {category} with privacy {privacy}")
    youtube = get_authenticated_service()

    body = {
      "status": {
        "madeForKids": madeForKids,
        "privacyStatus": privacy

      },
      "snippet": {
        "title": title[:99],
        "categoryId": category,
        "tags":  [
            "NeuroArt", "ArtificialIntelligence", "IdeaGeneration", "AIVideo",
            "DigitalCreativity", "NeuroImagery", "FuturisticDesign", "AIVoiceover",
            "InnovationInArt", "VirtualWorlds", "AICreativity", "FutureTech",
            "PhotoGeneration", "AutomatedCreation", "NeuralNetworkArt", "DigitalArt",
            "AIArt", "NeuroVideo", "AIGeneration", "ArtSynthesis"
        ]  ,
        "description": description[:5000],
        "defaultAudioLanguage": defaultAudioLanguage,
        "defaultLanguage": defaultLanguage

      }
    }

    logger.info(f"Uploading video with body: {body}")
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds} seconds and then retrying...")
            time.sleep(sleep_seconds)

    logger.success(f"Video id '{response['id']}' was successfully uploaded.")
    return response["id"]

if __name__ == "__main__":
    get_authenticated_service()