# GeoAI Azure Function Computer Vision
## Universal
### Setup - Install Tooling
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2) for setup, configuration and local testing.
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) is required for building binary packages locally for deployment.
- Install .NET 2.1 support (include more documentation)

### Mac

```bash
brew tap azure/functions
brew update
brew install azure-functions-core-tools
brew install azure-cli
az login
```

__NOTE:__
If Homebrew was installed prior to updating macOS, it is likely an error will be encountered when installing dependencies for the azure-cli, notably the Python dependency. If this occurs, run the following, and you should be good to go!

```bash
brew uninstall azure-functions-core-tools
brew uninstall azure-cli
sudo mkdir /usr/local/Frameworks
sudo chown $(whoami):admin /usr/local/Frameworks
brew install azure-functions-core-tools
brew install azure-cli
az login
```

### Windows

```bash
choco install azure-functions-core-tools
choco install azure-cli
az login
```

## Create Project and Function

```bash
mkdir azure-functions && cd azure-functions
python3.6 -m venv .env
source .env/bin/activate
func init --worker-runtime python --source-control true --docker true
func new -t "HTTP Trigger" -n function-name
```

## Add Esri Python API

Using editor of choice, add the following packages to `requirements.txt`.

```
requests2==2.16.0
arcgis>=1.5.2
python-dotenv>=0.5.1
```

Next, install the requirements.

```bash
pip install -r requirements.txt
```

## Publishing to Azure

### Create Function Resources

[Reference](https://docs.microsoft.com/en-us/azure/azure-functions/scripts/functions-cli-create-serverless)

Create a resource group for this project.

```bash
az group create --name geoaiFunctionGroup --location westus
```

Create Azure storage account in the resource group.

```bash
az storage account create \
  --name geoaifunctionstorage \
  --location westus \
  --resource-group geoaiFunctionGroup
```

Create Azure Function application in the resource group.

```bash
az functionapp create \
  --name esri-geoai \
  --storage-account geoaifunctionstorage \
  --consumption-plan-location westus \
  --resource-group geoaiFunctionGroup \
  --os-type Linux \
  --runtime python
```

[Publish to Azure by compiling locally](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python#publishing-to-azure) (requires Docker)

```bash
func azure functionapp publish esri-geoai --build-native-deps --no-bundler
```

Building locally due to error when publishing. 

```
There was an error restoring dependencies.ERROR: cannot install tornado-5.1.1 dependency: binary dependencies without wheels are not supported.  Use the --build-native-deps option to automatically build and configure the dependencies using a Docker container. More information at https://aka.ms/func-python-publish
```

Clean up when done.

```bash
az group delete --name geoaiFunctionGroup
```

#### Full Bash Script

```bash
#!/bin/bash

# Function app and storage account names must be unique.
resourceGroup=geoaiFunctionGroup
storageName=geoaifuncstorage$RANDOM
functionAppName=esri-geoai-fedgis
resourceLocation=eastus

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
```