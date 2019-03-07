#!/bin/bash -v

# Function app and storage account names must be unique.
resourceGroup=geoaiFunctionGroup
storageName=geoaistor$RANDOM
functionAppName=geoai-bicycle
resourceLocation=westus

# Create a resource group.
az group create \
    --name $resourceGroup \
    --location $resourceLocation

# Create an Azure storage account in the resource group.
az storage account create \
  --name $storageName \
  --location $resourceLocation \
  --resource-group $resourceGroup \
  --sku Standard_LRS

# Create a serverless function app in the resource group. 
az functionapp create \
  --name $functionAppName \
  --storage-account $storageName \
  --consumption-plan-location $resourceLocation \
  --resource-group $resourceGroup \
  --os-type Linux \
  --runtime python
  
# Remove all the CORS rules
az functionapp cors remove \
    --resource-group $resourceGroup \
    --name $functionAppName \
    --allowed-origins \
        https://functions.azure.com \
        https://functions-staging.azure.com \
        https://functions-next.azure.com
    
# CORS allow all
az functionapp cors add \
    --resource-group $resourceGroup \
    --name $functionAppName \
    --allowed-origins "*"
    
# upload the local application
func azure functionapp publish $functionAppName --build-native-deps --no-bundler

