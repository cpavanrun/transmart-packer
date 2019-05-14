# transmart-packer Docker image

[![Docker Hub](https://img.shields.io/docker/pulls/thehyve/transmart-packer.svg)](https://hub.docker.com/r/thehyve/transmart-packer)

```bash
# Fetch images with tag 'latest'
docker pull thehyve/transmart-packer:latest
```

## Configuration

The image requires the following environment variables to be present:

Variable              | Description
:-------------------- |:-------------------------------------------------------
`TRANSMART_URL`       | The URL of the TranSMART API server
`KEYCLOAK_SERVER_URL` | Keycloak server URL, e.g., `https://keycloak-dwh-test.thehyve.net/auth`
`KEYCLOAK_REALM`      | The Keycloak realm, e.g., `transmart-dev`
`KEYCLOAK_CLIENT_ID`  | The Keycloak client ID, e.g., `transmart-client`


## Ports

The image exposes the following ports:

Value    | Type  | Description
:------- |:----- |:-----------------
8999     | `tcp` | Port of the transmart-packer web app


## Volumes

`/app/tmp_data_dir`: the export data directory.