# Azure DICOM Proxy

This repository has taken a portion of code from https://github.com/UCLH-Foundry/PIXL/ (Apache 2.0, not yet public) to provide a very simple demonstration (not for production use) on how Orthanc can be used to proxy files from DIMSE to the Azure DICOM service.

By using an Orthanc plugin additonal operations can be carried out on imaged prior to being sent to the Azure DICOM service. For example in UCLH's Pixl de-identification of the DICOM images.

# Orthanc

Orthanc - https://www.orthanc-server.com/ - is responsible for receiving from PACS/VNA and forwarding to Azure DICOM service.

## Setup 

### Prerequisites

The following assumptions are made:
- The Azure AD`Tenant ID`, `App ID` and `Client Secret` have been configured.
- The Azure DICOM service endpoint is available and has been configured.
- Outbound HTTPS access to the Azure DICOM service is available.
- There is sufficient local storage for the `orthanc-data` volume.

### Configuration

- The Docker image is based on `osimis/orthanc`. 
- Configuration is driven through customised JSON config. files stored in the [config](./config/) directory. 
- The files are populated with values from environment variables and injected into the container as secrets. Orthanc interprets all `.json` files in the `/run/secrets` mount as config. files.
- The instance configuration comprises three files:
  - `dicom.json` - Controls the AE Title for this instance, the details of the `Raw` instance and the config stub for DICOMWeb (to enable configuration of the Azure DICOM service at runtime).
  - `orthanc.json` - Controls the instance name, RBAC, storage and enabling plugins. (Plugins are required to enable the Python plugins)
- `pixl.py` is responsible for the auto-routing of anonymised studies to the Azure DICOM service.
- Study auto-routing is only enabled when the `ENV` environment variable is `staging` or `prod`

### Step 1
Save credentials `.env` for 'Orthanc' and the Azure DICOM Service.
```
# Orthanc instance
ORTHANC_USERNAME=
ORTHANC_PASSWORD=     
ORTHANC_AE_TITLE=
ORTHANC_HTTP_TIMEOUT=60
ENABLE_DICOM_WEB=true

# DICOMweb endpoint
AZ_DICOM_ENDPOINT_NAME=
# https://<workspace>-<dicomservicename>-node.dicom.azurehealthcareapis.com/v1/
AZ_DICOM_ENDPOINT_URL=
AZ_DICOM_ENDPOINT_CLIENT_ID=
AZ_DICOM_ENDPOINT_CLIENT_SECRET=
AZ_DICOM_ENDPOINT_TENANT_ID=

# Exposed ports for debugging / testing.
ORTHANC_DICOM_PORT=XXXX
ORTHANC_WEB_PORT=YYYY
```

### Step 2

Start the instance via Docker compose.

```
docker compose --env-file local.env up
```

### Step 3

If you have chosen to expose the ports, you should now be able to navigate the web interface at `http://localhost:<YYYY>`, supply the chosen credentials and will be presented with the Orthanc web interface.

### Step 4
From the interface, you can view data stored on the instance or perform Query/Retrieves against the Azure DICOM service. Similarly you can target the instance over DIMSE on port `XXXX`, if exposed.

## Step 5
The advanced user interface can be found at `http://localhost:YYYY/ui/app/`. This can be used to check connectivity to the other modalities and the running configuration.

## Step 6
The Azure DICOM service can be accessed via the `DICOMWeb client`.

## Local development
- It is assumed that you will be using docker compose, if not, then you need to mount the contents of the `config` directory onto `/run/secrets` within the container.

## Troubleshooting

- If modifying any of the `.json` configuration files, any typo will cause the instance to fail to start.
- To use the REST interface, the web port must be exposed.
- To use DIMSE, the DICOM port must be exposed.
- DICOMWeb is enabled on this instance. _Any data pushed to this instance will be forwarded via STOW to the configured Azure DICOM service target_.

## References
 - [Cheat sheet of the REST API](https://book.orthanc-server.com/users/rest-cheatsheet.html)
 - [MIPAV](https://mipav.cit.nih.gov/) Tool that can be used to test the sending DICOM images via DIMSE to Orthanc

