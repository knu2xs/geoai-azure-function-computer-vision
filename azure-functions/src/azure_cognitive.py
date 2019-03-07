import requests
from io import BytesIO
from PIL import Image
import math
from tempfile import TemporaryDirectory
import os

class _CognitiveService(requests.Session):
    """
    Provide single interface for working with Azure Cognitive services.
    :param subscription_key: Azure Subscription key for accessing services.
    :param service_url_suffix: Suffix to the base path for accessing specific service.
    :param region_code: URL prefix specifying the region to make calls to.
    """

    def __init__(self, subscription_key, region_code='eastus'):

        # ensure not clobbering parent init
        super().__init__()

        # set a few variables
        self._region_code = region_code
        self._url_suffix = ''

        # set the session header to include the subscription key
        self.headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-Type': 'application/json'
        }

    @property
    def url(self):
        return 'https://{}.api.cognitive.microsoft.com{}'.format(self._region_code, self._url_suffix)


class ComputerVision(_CognitiveService):
    """
    Provide interface for working with Azure Computer Vision.
    :param subscription_key: Azure Subscription key for accessing services.
    :param service_url_suffix: Suffix to the base path for accessing specific service.
    :param region_code: URL prefix specifying the region to make calls to.
    """

    # parameters to use as part of the request
    params = {'visualFeatures': 'Categories,Description,Color'}

    def __init__(self, *args):

        # ensure not clobbering parent init
        super().__init__(*args)

        # set the url suffix for this resource
        self._url_suffix = '/vision/v2.0/analyze'

    def _get_image_mb(self, image):
        """
        Helper function to quickly get a PIL Image object size in megabytes
        """
        one_mb = 1048576.0
        return len(image.tobytes()) / one_mb

    def _image_oversize(self, image):
        """
        Helper function to assess if an image is oversize for Azure Computer Vision.
        """ 
        oversize_mb = 4
        return self._get_image_mb(image) > oversize_mb

    def _submit_img(self, img):
        """
        Helper function to handle PIL Image objects - used when working with local file
        """
        # if the image is oversize, need to downsize before submitting
        if self._image_oversize(img):

            # now, just keep whittling down the image until it falls below the threshold
            # while the image oversize
            while self._image_oversize(img):
                
                # decrease the dimensions of the image by 3%
                img_dimensions = tuple(math.floor(0.97 * val) for val in img.size)
                img.thumbnail(img_dimensions)

        # although not likely the most elegant, since BytesIO did not work, saving locally to get working
        tmp_dir = TemporaryDirectory()
        img_file = os.path.join(tmp_dir.name, 'tmp_file.jpg')
        img.save(img_file, format='jpeg')

        # add the header to be able to upload the image
        self.headers['Content-Type'] = 'application/octet-stream'

        # now, with the image at an acceptable size, submit for evaluation
        return self.post(self.url, params=self.params, data=open(img_file, 'rb').read())

    def submit(self, image):
        """
        Submit an image for evaluation.
        :param image: Path, either local or url, to the image to be evaluated.
        :return: JSON response.
        """
        # check to see if the image is a remote or local resource
        if image.startswith('http'):

            # download the image and convert to PIL Image object
            img_resp = requests.get(image, stream=True)
            img_resp.raw.decode_content = True
            img = Image.open(img_resp.raw)

            # if the image is an acceptable size, just send it
            if not self._image_oversize(img):

                # submit the image url for evaluation
                response = self.post(self.url, params=self.params, json={'url': image})

            # if the image is oversize, handle as file
            else:

                response = self._submit_img(img)

        # if a local file
        else:
            # convert the image to a PIL Image object to start working with
            img = Image.open(image)

            # hand off to helper function
            response = self._submit_file(img)

        return response.json()

    def get_tags(self, image):
        """
        Submit an image for evaluation.
        :param image: Path, either local or url, to the image to be evaluated.
        :param search_tags: List of tags (as strings) to check for against Azure Computer Vision.
        :return: List of strings with assigned tags.
        """ 
        # get the response from Azure Computer Vision
        resp_dict = self.submit(image)

        # extract the tags 
        return resp_dict['description']['tags']

    def get_image_tag_match(self, image, search_tags):
        """
        Submit an image for evaluation.
        :param image: Path, either local or url, to the image to be evaluated.
        :param search_tags: List of tags (as strings) to check for against Azure Computer Vision.
        :return: Tuple containing a list of assigned tags from Computer Vision and boolean indicating whether any of
            the search tags were found.
        """
        # get the tags
        tag_list = self.get_tags(image)

        # compare the tags against the serach tags to get a match status
        match_status = not set(search_tags).isdisjoint(tag_list)

        return {'tag_list': tag_list, 'match_status': match_status}
