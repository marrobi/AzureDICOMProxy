#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
from decouple import config
from io import BytesIO

from pydicom import dcmread, dcmwrite
from pydicom.filebase import DicomFileLike

import hashlib
import json
import orthanc
import pprint
import requests
import sys
import threading
import yaml

import logging 

def AzureDICOMTokenRefresh():
    global TIMER
    TIMER = None

    orthanc.LogWarning("Refreshing Azure DICOM token")

    ORTHANC_USERNAME = config('ORTHANC_USERNAME')
    ORTHANC_PASSWORD = config('ORTHANC_PASSWORD')

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config('AZ_DICOM_TOKEN_REFRESH_SECS'))
    AZ_DICOM_ENDPOINT_CLIENT_ID = config('AZ_DICOM_ENDPOINT_CLIENT_ID')
    AZ_DICOM_ENDPOINT_CLIENT_SECRET = config('AZ_DICOM_ENDPOINT_CLIENT_SECRET')
    AZ_DICOM_ENDPOINT_NAME = config('AZ_DICOM_ENDPOINT_NAME')
    AZ_DICOM_ENDPOINT_TENANT_ID = config('AZ_DICOM_ENDPOINT_TENANT_ID')
    AZ_DICOM_ENDPOINT_URL = config('AZ_DICOM_ENDPOINT_URL')
    AZ_DICOM_HTTP_TIMEOUT = int(config('HTTP_TIMEOUT'))

    url = "https://login.microsoft.com/" + AZ_DICOM_ENDPOINT_TENANT_ID \
    + "/oauth2/token"

    payload = {
        'client_id': AZ_DICOM_ENDPOINT_CLIENT_ID,
        'grant_type': 'client_credentials',
        'client_secret': AZ_DICOM_ENDPOINT_CLIENT_SECRET,
        'resource': 'https://dicom.healthcareapis.azure.com'
    }

    response = requests.post(url, data=payload)
    #logging.info(f"{payload}")
    #logging.info(f"{response.content}")

    access_token = response.json()["access_token"]

    #logging.info(f"{access_token}")

    bearer_str = "Bearer " + access_token

    dicomweb_config = {
        "Url" : AZ_DICOM_ENDPOINT_URL,
        "HttpHeaders" : {
          "Authorization" : bearer_str,
        },
        "HasDelete": True,
        "Timeout" : AZ_DICOM_HTTP_TIMEOUT
    }

    #logging.info(f"{dicomweb_config}")

    headers = {'content-type': 'application/json'}

    url = "http://localhost:8042/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME

    try:
        requests.put(url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), headers=headers, data=json.dumps(dicomweb_config))
    except requests.exceptions.RequestException as e:
        orthanc.LogError("Failed to update DICOMweb token")
        raise SystemExit(e)

    orthanc.LogWarning("Updated DICOMweb token")

    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()

def SendViaStow(resourceId):

    ORTHANC_USERNAME = config('ORTHANC_USERNAME')
    ORTHANC_PASSWORD = config('ORTHANC_PASSWORD')

    AZ_DICOM_ENDPOINT_NAME = config('AZ_DICOM_ENDPOINT_NAME')

    url = "http://localhost:8042/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME + "/stow"

    headers = {'content-type': 'application/json'}

    payload = {
        "Resources" : [
            resourceId
        ],
        "Synchronous" : False
    }

    logging.info(f"{payload}")

    try:
        requests.post(url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), headers=headers, data=json.dumps(payload))
        orthanc.LogInfo(f"Sent {resourceId} via STOW")
    except requests.exceptions.RequestException as e:
        orthanc.LogError(f"Failed to send {resourceId} via STOW")

def ShouldAutoRoute():
    return os.environ.get("ORTHANC_AUTOROUTE_TO_AZURE", "false").lower() == "true"

def OnChange(changeType, level, resource):
    if not ShouldAutoRoute():
        return

    orthanc.LogWarning(f"changeType: {changeType}, level: {level}, resource: {resource}")

    if changeType == orthanc.ChangeType.STABLE_STUDY and ShouldAutoRoute():
        print('Stable study: %s' % resource)
        SendViaStow(resource)

    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        orthanc.LogWarning("Starting the scheduler")
        AzureDICOMTokenRefresh()
    elif changeType == orthanc.ChangeType.ORTHANC_STOPPED:
        if TIMER != None:
            orthanc.LogWarning("Stopping the scheduler")
            TIMER.cancel()

def OnHeartBeat(output, uri, **request):
    orthanc.LogWarning("OK")
    output.AnswerBuffer('OK\n', 'text/plain')


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback('/heart-beat', OnHeartBeat)