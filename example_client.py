"""
    This script contains examples of working with the LaTeX compile service via the HTTP/JSON API.

    This code is in python3, but deliberatey no special python client libraries specific to the
    service are used here, so the interaction with the API should translate to any other language
    and framework.

    This script uses the test files included in the repository, so will need access to the
    contents of the ./tests/test_files directory.  The directory itself can be changed as needed
    with the TEST_FILE_DIRECTORY constant.

    As is standard practice for Python, the third party 'requests' module is used. Install with
    'pip install requests' or 'pip3 install requests' depending on your environment if you don't
    already have it installed.
"""

import os
import json
import time
from urllib.parse import urljoin, urlparse
import requests
from pprint import pprint

SERVICE_URL = "http://localhost:5000"
TEST_FILE_DIRECTORY = "./tests/test_files"


def _patch_url(url: str) -> str:
    """
    In Flask, if the environmental variable SERVER_NAME is not set, the internal URL generation will
    produce relative URLs instead of absolute ones (since the server does not know its own name).

    This helper method takes a URL and if it already has a hostname, will return it unaltered, while if
    it does not have a hostname it will append it to the SERVICE_URL above to return a usable url.
    """
    parsed = urlparse(url)
    if not parsed.netloc:
        return urljoin(SERVICE_URL, url)
    else:
        return url


def get_create_form():
    """
    A GET request to the main API endpoint will return a json form which can guide you through the
    session creation process.  A session is a single compilation session which specifies a main target
    file and a compiler.  A session can have many source files and/or templates, but will produce a
    single output.
    """
    api_url = urljoin(SERVICE_URL, "api")
    response = requests.get(api_url)
    pprint(response.json())


def render_sample_tex():
    """
    This example demonstrates the compilation and retrieval of a simple, single file sample .tex
    document with an image into a PDF.  We will use xelatex as the compiler.

    Process overview:

    First, we will create a session.  We will set the compiler and the name of the file which will
    be the ultimate target of the compiler.  Then we will upload two files the the session, one which
    is the actual target .tex file and the other which is a jpeg to put in the image.  These can be
    uploaded in separate requests, or in the same request.  Finally we will set the session as
    'finalized', which means that we will no longer be able to add files or make changes to it.  Last
    we will poll the session until its status has changed to either 'success' or 'error', at which
    time we will either retrieve the completed PDF or the log file.
    """

    # First we will create a new session by POST-ing a compiler and target to the general sessions
    # endpoint.  We will get back a HTTP code and, if successful, a redirect URL to the session
    # resource. Once the session is created at this step, its time-to-live clock is running.  The
    # default TTL for a session is 5 minutes, but can be set by an environmental variable in the server.
    session_api_url = urljoin(SERVICE_URL, "api/sessions")
    session_data = {"compiler": "xelatex", "target": "sample1.tex"}
    response = requests.post(session_api_url, json=session_data, allow_redirects=True)

    assert response.status_code == 201  # resource should have been created, returning 201
    my_session_url = response.headers['Location']  # will contain <SERVICE_URL>/api/sessions/<session_id>

    # With the session now created and the session base URL captured as my_session_url, we can
    # post the file to /api/sessions/<session_id>/files, which can be built off of the returned
    # my_session_url, or followed from the json form that will be returned by making a GET request
    # to my_session_url
    session_response = requests.get(my_session_url)
    add_file_url = _patch_url(session_response.json()['add_file']['href'])

    with open(os.path.join(TEST_FILE_DIRECTORY, "sample1.tex"), "rb") as file_handle:
        # When posting files to the /api/<session_id>/files endpoint, the name/key of the file is the
        # relative path to the session working directory which the server will save the uploaded file.
        # If you need files to be saved to different folders, it can be done here.  The server will
        # ensure that uploaded files are contained within the temporary working directory it creates, so
        # escaping the working directory via ../ or / will not work.
        files = {"sample1.tex": file_handle}
        file_response = requests.post(add_file_url, files=files)

    with open(os.path.join(TEST_FILE_DIRECTORY, "cat.jpg"), "rb") as file_handle:
        files = {"cat.jpg": file_handle}
        file_response = requests.post(add_file_url, files=files)

    assert file_response.status_code == 201

    # Now we can finalize the session
    finalize_response = requests.post(my_session_url, json={"finalize": True})
    assert finalize_response.status_code == 202

    # At some point a worker should pick up the task and complete the compilation, at which point
    # we can retrieve the product from the provided url.  Here we simply wait until the status changes
    # to either 'success' or 'error'
    session_resource = requests.get(my_session_url).json()
    while session_resource['status'] not in ['success', 'error']:
        time.sleep(2.0)
        session_resource = requests.get(my_session_url).json()

    # If successful, the url for retrieving the product is /api/sessions/<session_id>/product, which
    # you can build yourself, or follow the link provided under the 'product' key in the session
    # resource. Making a GET request to this url will download the completed file.
    if session_resource['status'] == "success":
        product_url = _patch_url(session_resource['product']['href'])
        product_response = requests.get(product_url)

        # The file is in the 'content' field of the response. Here we'll save it to a file.
        with open('sample1-example.pdf', 'wb') as file_handle:
            file_handle.write(product_response.content)

    # If the result was not successful, we can retrieve and print the log for some clue as to what
    # went wrong during the process.
    elif session_resource['status'] == "error":
        log_url = _patch_url(session_resource['log']['href'])
        log_response = requests.get(log_url)
        print(log_response.content)


def render_with_template():
    """
    This example demonstrates the rendering, compilation, and retrieval of a jinja2 template.  The
    process is very straightforward.

    Process overview:

    First, we will create a session.  We will set the compiler and the name of the file which will
    be the ultimate target of the compiler.  Then we will upload the contents of the template file
    along with a data dictionary for the template to render into the document. Finally we will set
    the session as 'finalized' and poll the session until its status has changed to either 'success'
    or 'error', at which time we will either retrieve the completed PDF or the log file.
    """

    # First we will create a new session by POST-ing a compiler and target to the general sessions
    # endpoint.  We will get back a HTTP code and, if successful, a redirect URL to the session
    # resource. Once the session is created at this step, its time-to-live clock is running.  The
    # default TTL for a session is 5 minutes, but can be set by an environmental variable in the server.
    session_api_url = urljoin(SERVICE_URL, "api/sessions")

    # The target here will refer to a file which we will not actually upload directly. Rather, we will
    # upload a template which we will instruct the service to render to the name 'rendered.tex', so
    # that when the compiler is actually called, there will be a file with that name for it to
    # operate on.
    session_data = {"compiler": "xelatex", "target": "rendered.tex"}
    response = requests.post(session_api_url, json=session_data, allow_redirects=True)
    assert response.status_code == 201  # resource should have been created, returning 201
    my_session_url = response.headers['Location']  # will contain <SERVICE_URL>/api/sessions/<session_id>

    # With the session now created and the session base URL captured as my_session_url, we can
    # post the file to /api/sessions/<session_id>/templates, which can be built off of the returned
    # my_session_url, or followed from the json form that will be returned by making a GET request
    # to my_session_url
    session_response = requests.get(my_session_url)
    templates_url = _patch_url(session_response.json()['add_templates']['href'])

    # This is the data which we will insert into the template.  It needs to be a json dictionary, and
    # the rendering mechanism will take all its contents and make it accessible to the template. First
    # level keys will be callable directly by name, and sub-elements can be called by either python
    # index notation (first_level_element['key_name']) or dot notation (first_level_element.key_name).
    # Be careful with the latter, as jinja2 will convert the json to a native python dictionary which
    # has builtin sub-elements, like the 'items' sub-key here. See the README for more info.
    template_data = {
        "name_1": "This is the title of the first section",
        "data2": {
            "name": "Another Section",
            "items": ["Apple", "Orange", "Pamplemousse", "Watermelon"]
        }
    }

    # Take a look at the ./tests/test_files/sample_template1.tex file, and refer to the README
    # documentation for a better understanding of the jinja2 template grammar.  We are going to post
    # a single json document to the api/sessions/<session_id>/templates endpoint, and it will
    # contain three things: (1) the text content of the template file, (2) a data dictionary to be
    # rendered into the template, and (3) a name for the renderer to save the completed document.
    with open(os.path.join(TEST_FILE_DIRECTORY, "sample_template1.tex"), "r") as file_handle:
        template_post_data = {
            "text": file_handle.read(),
            "data": template_data,
            "target": "rendered.tex"
        }
        file_response = requests.post(templates_url, json=template_post_data)

    assert file_response.status_code == 201

    # Now we can finalize the session
    finalize_response = requests.post(my_session_url, json={"finalize": True})
    assert finalize_response.status_code == 202

    # At some point a worker should pick up the task and complete the compilation, at which point
    # we can retrieve the product from the provided url.  Here we simply wait until the status changes
    # to either 'success' or 'error'
    session_resource = requests.get(my_session_url).json()
    while session_resource['status'] not in ['success', 'error']:
        time.sleep(2.0)
        session_resource = requests.get(my_session_url).json()

    # If successful, the url for retrieving the product is /api/sessions/<session_id>/product, which
    # you can build yourself, or follow the link provided under the 'product' key in the session
    # resource. Making a GET request to this url will download the completed file.
    if session_resource['status'] == "success":
        product_url = _patch_url(session_resource['product']['href'])
        product_response = requests.get(product_url)

        # The file is in the 'content' field of the response. Here we'll save it to a file.
        with open('sample2-example.pdf', 'wb') as file_handle:
            file_handle.write(product_response.content)

    # If the result was not successful, we can retrieve and print the log for some clue as to what
    # went wrong during the process.
    elif session_resource['status'] == "error":
        log_url = _patch_url(session_resource['log']['href'])
        log_response = requests.get(log_url)
        print(log_response.content)


if __name__ == '__main__':
    render_sample_tex()
    render_with_template()
