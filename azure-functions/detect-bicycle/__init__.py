import os
import logging
from arcgis.gis import GIS, Item
from dotenv import load_dotenv, find_dotenv
import azure.functions as func
import json
import ast

from ..src.azure_cognitive import ComputerVision

# load the .env settings
load_dotenv(find_dotenv())

def main(req: func.HttpRequest) -> func.HttpResponse:

    try:

        # if the invocation method is OPTION, just respond with 200 to let the client know the endpoint is working
        if req.method == 'OPTIONS':
            return func.HttpResponse(
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Max-Age': '3600'
                    },
                    status_code=200
                )

        # otherwise, if the request method is POST, get to work!
        elif req.method == 'POST':

            # extract the Object ID from the submitted feature
            req_str = req.get_body().decode('utf-8')
            req_dict = json.loads(req_str)
            feature_oid = req_dict['feature']['result']['objectId']

            logging.info(f'Feature Object ID: {feature_oid}')

            # retrieve values from environment file
            gis_url = os.getenv('GIS_URL')
            gis_username = os.getenv('GIS_USERNAME')
            gis_password = os.getenv('GIS_PASSWORD')
            feature_service_item_id = os.getenv('SURVEY_LAYER_ITEM_ID')
            feature_service_detection_field = os.getenv('FEATURE_SERVICE_DETECTION_FIELD')
            feature_service_tags_field = os.getenv('FEATURE_SERVICE_TAGS_FIELD')
            azure_key = os.getenv('AZURE_KEY')
            azure_region_code = os.getenv('AZURE_REGION_CODE')
            tag_search_lst = ast.literal_eval(os.getenv('OBJECT_TAGS'))

            # connect to the web gis, and create a layer using the item ID
            gis = GIS(gis_url, username=gis_username, password=gis_password)
            lyr_pt = Item(gis, feature_service_item_id).layers[0]

            logging.info(f'Using layer {lyr_pt.url}')

            # get the image from the attachment list and create a url to access it
            attachment_lst = lyr_pt.attachments.get_list(feature_oid)
            attachment_id = attachment_lst[0]['id']
            image_url = f'{lyr_pt.url}/{feature_oid}/attachments/{attachment_id}?token={gis._con.token}'

            logging.info('Successfully processed JSON, now sending to computer vision.')
            logging.info(f'Image url: {image_url}')

            # determine if a weapon exists using computer vision, and format the responses
            vision = ComputerVision(azure_key, azure_region_code)
            tag_match_dict = vision.get_image_tag_match(image_url, tag_search_lst)
            detection_status = tag_match_dict['match_status']
            tags_assigned = ', '.join(tag_match_dict['tag_list'])

            logging.info(f'Tags assigned by Azure Computer Vision: {tags_assigned}')
            logging.info(f'Object Detection Status: {detection_status}')

            # geat a feature object, modify the attribute to reflect the status, and push the results to ArcGIS Online
            feat = lyr_pt.query(object_ids=f'{feature_oid}').features[0]
            feat.attributes[feature_service_detection_field] = detection_status
            feat.attributes[feature_service_tags_field] = tags_assigned
            update_resp = lyr_pt.edit_features(updates=[feat])
            
            # if the process was successful, return success code
            if update_resp['updateResults'][0]['success']:

                logging.info('Successfully processed image and updated feature service.')

                return func.HttpResponse(
                    'Successfully processed image and updated feature service.',
                    status_code=202
                )

            # otherwise, let the user know not so great
            else:

                logging.warning('Although the image was successfully categorized, updating the feature service failed.')

                return func.HttpResponse(
                    'Although the image was successfully categorized, updating the feature service failed.',
                    status_code=400
                )

        # if it isn't an OPTIONS or POST request, homie don't play 'dat.
        else:
            return func.HttpResponse(
                    f'Request must be either a OPTIONS or POST. You submitted a {req.method}, which is unacceptable.',
                    status_code=404
                )

    except ValueError as err:

        logging.error(err)

        return func.HttpResponse(
            f'Request Data Type - {type(req)}\n' +
            f'Request Body Type - {type(req.get_body())}\n' +
            f'Request Body Decoded - {req_body}\n' +
            f'Request Body - {req.get_body()}\n' +
            f'Headers:\n {req.headers.__dict__["__http_headers__"]}\n' +
            f'Request Parameters - {req.params}\n' +
            f'Request Route Params - {req.route_params}\n' +
            f'\nError Message:\n\n{err}',
            status_code=404
        )