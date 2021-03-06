# LaTeX Compile Service

A Flask based web service that compiles LaTex projects to document form and uses the Jinja2 engine to render templates and data to .tex files.  Ready to deploy with docker-compose, docker swarm mode, or kubernetes.  Can be installed directly on a server OS with a bit more effort.

*This project is intended for use as an internal service being consumed by trusted clients. TeX is a general purpose programming language and its ability to read and write arbitrary text files through its macro system is [sufficient to allow maliciously crafted tex files to run arbitrary binaries](https://www.usenix.org/system/files/login/articles/73506-checkoway.pdf). Even if an attacker is unable to escape the worker process' container, the service itself can be degraded or disabled by malicious input data.*

## Quickstart

This describes a quick-start deployment using the `docker-compose.yaml` file included in the repository, which is the fastest way to get started. More complex deployments can be assembled by modifying the compose file, using the `docker-compose.dev.yaml` file, starting docker images manually, or using kubernetes.  The service can also be installed directly on the OS of a physical or virtual server.

1. Use `docker-compose` to build and run the app 
    * From the main project directory, `docker-compose up -d --build`
    * the app should be reachable at http://localhost:5000
2. Send files to be rendered
    * See `example_client.py` for an example of how to use python to interact with the API
    * Or, hit the http://localhost:5000/api end point to get a json form which will get you started
    * After creating a session, you can post files, `.tex`, images, etc, to the session
    * You can also post template text and data for the Jinja2 engine to render to a `.tex` file
    * Finalize a session and the service will asynchronously attempt to compile it to a `.pdf` file using the compiler of your choice. If successful, the product will be available for download, otherwise only the log will be available. 
3. Retrieve your compiled file
    * create a GET request to http://localhost:5000/api/<session_id>/product to retrieve the compiled file
    * create a GET request to http://localhost:5000/api/<session_id>/log to retrieve the log
    * The session will be automatically removed 5 minutes after creation, regardless of compilation status

## Overview

This project is a LaTeX compiling and template rendering web service intended to run in a Docker container, and interacted with by other software through a REST-like api. It is written in Python3 and uses Flask.

This software was developed as a lightweight (as lightweight as one can reasonably call something housing a full texlive installation) infrastructure service for automated document generation. It is meant to be simple and reliable, able to be deployed once for an organization or group and provide the rendering of latex files for many other applications without requiring them to each maintain their own LaTeX toolchain.

This project is essentially a small Flask app built on top of [thomasweise/docker-texlive-full](https://hub.docker.com/r/thomasweise/docker-texlive-full) an ubuntu-based docker image with `texlive-full` installed, plus `ghostscript` and `poppler-utils`, the latter which is used in the pdf to image conversion feature.

Additionally, `jinja2` can be used to render templates to LaTeX files which will then be compiled with other source files, allowing for a slightly more sane scripting environment than plain TeX.  The `jinja2` grammar was slightly altered to be more compatible with LaTeX's quirks in a way that is inspired by, but slightly different from, [this blog post by Brad Erikson](http://eosrei.net/articles/2015/11/latex-templates-python-and-jinja2-generate-pdfs).

### Why as a service, and why containerized?
LaTeX, though quite powerful, can be a frustrating toolset to install and maintain, especially across platforms. A comprehensive installation can be several gigabytes in size, and seems to be easily broken.  Online tools like [Overleaf](https://www.overleaf.com) ([source on GitHub](https://github.com/overleaf)) show how much pain can be saved by not maintaining individual installations, but Overleaf itself is structured towards the concepts of users and projects and isn't exactly a lightweight service meant to be consumed by other services. 

Deploying a containerized service that houses a `texlive-full` installation and can live on any platform capable of hosting a Docker container takes nearly all of the pain out of managing it.  There's nothing to be broken during upgrades, and no complex setup to be lost when a server dies.  By making this app nearly stateless (it does store information, but only for a few minutes at a time) it is also extremely easy to migrate from host to host and to scale up or down as needed.  It's also easy to upgrade and redeploy.

In my experience, the additional layer of abstraction induced by containerization is a net benefit, because I have found the additional complexity of Docker to be far less than the complexity of managing LaTeX.  However, a determined user/sysadmin can deploy this service outside of a container by installing the Flask app, the Celery worker, and the Celery scheduler as system services on a physical or virtual machine with a LaTeX toolchain, and pointing them at either a local or network-accessible Redis server.

### What makes this project different from others?

There are a few projects out there which put LaTeX compilation tools in a Docker image with a web application over them.  The most comprehensive seems to be [vsfexperts/LaTeX](https://github.com/vsfexperts/LaTeX) which unfortunately takes the entire content to be rendered in the POST request, meaning that multiple files (like custom classes, or images) cannot be rendered.  There is also [DMOJ/Texoid](https://github.com/DMOJ/texoid), but it is focused on rendering LaTeX math symbols to graphics formats.  There are an additional handful of similar projects, but most suffer from inadequate documentation or the limitation of using POST to submit a single document to be rendered.

What I think the benefits of this project over the existing projects are:

1. Send multiple files to the service, including a local nested directory structure. For example, you can set the main compilation target to `./sample.tex` and have that file reference several other files, such as `./diagram.png`, `./common/logo.png`, `./common/classes/org-doc.cls`, and `./common/classes/org.sty`

2. Specify your choice of compiler for each compilation session.  You can use `pdflatex`, `xelatex`, or `lualatex`, some of which are capable of different things.

3. Use the `jinja2` engine to render `.tex` template files containing `jinja`'s python-like syntax to valid LaTeX, which will then be compiled as part of your project.  Submit the data to render to the template as a `json` dictionary. This is an easier way of producing generated documents for most people than trying to use LaTeX's programming mechanisms directly.

4. Have the compiled PDF converted to a jpeg, png, or tiff with a simple optional setting

5. Ample documentation and examples to clearly demonstrate
    1. How to set up and deploy the service
    2. How to use the service, with all of its different features
    3. How to develop or extend the project

## Getting Started: Deployment
There are a few options for deploying this service. The application is designed to be deployed via containers, and docker-compose is the the simplest option.  The application can also be deployed via Docker Swarm Mode, Kubernetes, or installation directly onto a server operating system.

### Docker Compose/Swarm Mode
If using Docker, and specifically Docker Compose or Docker Swarm Mode, the setup and deployment of the service is extremely straightforward and can mostly be accomplished by the use of the included YAML files. 

In the main directory of this git repository, there are two `docker-compose.*.yaml` files. One is aimed at a production environment, and the other is for development.  Additionally, there is another production oriented compose file under `deployments/docker-hub/docker-compose.yaml` which pulls pre-built images directly from Docker Hub.

In any of these cases, four containers will be created, one for the Flask app itself, one for the Celery worker, one for the Celery scheduler, and one for Redis.  The Celery worker and the Flask app will need to be able to share file storage, so must have a common volume in which the Flask app can store and retrieve files and the worker can run the LaTeX compilers.

> Note: because of Docker's copy-on-write Union File System, the running of the three separate containers does not translate into multiple copies of the frankly massive 4+ Gb image, since almost all of it is shared between the different containers.  With some shell scripting effort, a user/sysadmin can combine all of the processes into a single container, but this will strip away any external orchestration tool's ability to manage the health of the different processes with little tangible benefit in exchange.


#### From Docker Hub

The pre-built image is [available on Docker Hub as `matthewjarvis/latex-compileservice`](https://hub.docker.com/repository/docker/matthewjarvis/latex-compileservice) and can be deployed directly with the [docker-compose.yaml](https://raw.githubusercontent.com/mattj23/latex-compileservice/master/deployment/docker-hub/docker-compose.yaml) file located under the `deployments/docker-hub` directory of this git repository.

Alternatively, from a clean directory you can download and apply the file:

```bash
wget https://raw.githubusercontent.com/mattj23/latex-compileservice/master/deployment/docker-hub/docker-compose.yaml
docker-compose up -d
```

#### From this Git Repo
For a production-oriented environment use the `docker-compose.yaml` file. It uses gunicorn as the WSGI server and has the Flask environment set for production.  Celery's loglevel is set to "info" and the shared volume is set up in the compose file.  

```bash
docker-compose build
docker-compose up -d
```

There is only one worker container specified.  I do not currently know what the load is which would require a second or third worker and what benefits that would have over multiple copies of the service itself, but if you're using Docker swarm mode there should be no harm in using the "replicas" option to scale the number of workers.  It is *not* safe to scale the number of Celery beat schedulers, however, which is why the worker and beat scheduler were separated into two different containers instead of running the worker with the embedded scheduler via the `-B` option.  You can alter the `run.sh` shell script to include the `-B` option on the worker and remove the scheduler container if you know for a fact that you will never, in that case, run more than one worker.  However I don't believe there is any benefit to doing so.

#### From this Git Repo (Development)
For a development environment use the `docker-compose.dev.yaml` file. It uses the built in WSGI server (which is *not* suitable for production) with the appropriate Flask environmental variables set for a development server with debugging.  

Additionally, the app directory is bind mounted to the local filesystem so that Flask should reload the server whenever files in that directory are updated in order to ease development.  The Celery log level is set to "DEBUG" by default but can be changed as needed.

The setup for the four individual processes are the same as described in the production setup.

```bash
docker-compose -f docker-compose.dev.yaml build
docker-compose -f docker-compose.dev.yaml up -d
```

### On K8s with kubectl

If you have a working kubernetes cluster, there is a set of YAML files for use with `kubectl` which can serve as a starting point for getting the application deployed on the cluster.  I am a beginner with K8s so I welcome any feedback.

The YAML files are located under the "./deployments/kubectl" directory.

[The README.md in the directory explains the contents and has a guide for beginners](https://github.com/mattj23/latex-compileservice/blob/master/deployment/kubectl/README.md)

### Deploying on a Server OS
Deploying this application directly on a server was not my intention for it, but is a viable option for someone with the right skillset.  As a general rule it will be easiest to do on a Linux based OS with a package manager that includes texlive.

I can't fully describe how to perform this setup, but can give some general information to help the process:

1. You will need three processes running for the flask application and access to a Redis server, which can be local or over the network.
2. The latex toolchain will need to be installed such that the Celery worker can call it from the shell
3. Python 3.6 or greater needs to be installed, along with the dependencies in `requirements.txt`

### Environmental Variables
The following are environmental variables which apply settings in the application.  They will need to be set regardless of whether you are running in a container or on a server OS.

|Variable|Notes|Default|
|--------|-----|-------|
|REDIS_URL|URL for the Redis service, required by Flask, the Celery worker, and the Celery beat scheduler|redis://:@localhost:6379/0
|WORKING_DIRECTORY|The working directory where the session files and templates are stored, required by Flask and the Celery worker|/working
|SESSION_TTL_SEC|Time in seconds after creation when the session will be cleared and all data removed.|300 (5 min)
|CLEAR_EXPIRED_INTERVAL_SEC|Interval (in seconds) on which the background process clears expired sessions| 60
|INSTANCE_KEY|A string which uniquely identifies a deployed instance. In the case that multiple instances are to share a single Redis server this value must be set to a unique value for each instance.|latex-compile-service
|DEBUG|Environmental variable for Flask to tell if the debugger should be running| False
|FLASK_ENV|Environmental variable for flask to know if it is running a production, development, or testing instance.|production
|COMPONENT|Tells `run.sh` which component to launch. Used to ease running the different components through docker.  Must be set to `web`, `worker`, or `scheduler`.|web

## Getting started: Using the Service
### Overview of the API
As seen from the client side, the API offers access to a single main resource: an ephemeral "session".  The session has a "state" attribute, which controls how it can be interacted with and how the service treats it.

Sessions are created by clients who want to compile a set of LaTeX source files into a single document.  The client specifies a compiler and a target, optional settings to convert to an image, posts a set of source files which may include Jinja2 templates+json objects to be rendered *into* source files. When the session is created, its state will be "editable".  When the client is finished uploading resources to the session it posts a "finalized" flag which triggers a state transition to "finalized" and prevents further alterations to the session.

Once the session transitions to "finalized", a background worker will eventually pick it up, after which time it will either be successfully compiled into a document, or the compilation will fail.  The session state will then change to either "success" or "error".

At that point, the session will contain a link to log files, and (if it completed successfully) a product, which the client may download. The product will either be in the form of a PDF or an image file, depending on whether or not the conversion option was set.

The session will only persist for a limited amount of time (set by the server) after creation.  It is the responsibility of the client to check and download the results before the session is removed.

### Endpoints

#### Main API Endpoint
Located at `/api`, this is GET only and returns a json form which can guide you through the process of managing the session resources.

#### Session Endpoint
The session endpoint is located at `/api/sessions` and allows for the creation of new sessions by POSTing json data with a compiler and a target file specified.

```json
{ "target": "example.tex", "compiler": "pdflatex" }
```

Currently, the supported compilers are `pdflatex`, `xelatex`, and `lualatex`.  
The POST should return a json resource specifying session information, as well as a `Location` header with a URL for the session.

The optional convert-to-image feature can be enabled by including information on the desired format and dpi under the top level key `"convert"`.  This information can also be posted after the session is created. The allowable formats are `"jpeg"`, `"png"`, and `"tiff"`, and DPI must be an integer value between 10 and 10000.  If no conversion information is specified the system will produce a PDF, if conversion information is malformed or invalid the POST will fail with an error, and if the conversion information is successful the final product will be a file of the specified format instead of the PDF.

```json
{ "target": "example.tex", "compiler": "pdflatex", "convert": {"format": "png", "dpi": 600}}
```

> Note: image conversions with high DPI or large PDFs may take a long time and run into issues with the session lifespan. Under the hood, `pdftoppm` is used with the `-singlefile` flag, which only converts the first page of the pdf and writes it to a single file. This feature is intended for quick conversions of small page PDFS like labels, stickers, and math equations, and not for converting large documents to an image form.  If you need to convert full LaTeX documents to images it's best to download the PDF and perform the conversion externally.

#### Specific Session Endpoint
Located at `/api/sessions/<session_key>`, a GET request will return the specific session resource associated with a given session key, including links to completed logs and products, as well as a json form to guide you through the usage of this resource.  A POST request of `{"finalize": true}` will transition the state to "finalized" so that a worker will pick up the session and attempt to compile it.  

Before finalizing the session, files and/or templates should be uploaded to it.

#### Session Files Endpoint
Located at `/api/sessions/<session_key>/files`, files can be posted here as multi-part form data.  

The name associated with each file will be the relative path which the associated file content data will be saved to (paths which try to escape the working directory will be disregarded) allowing the content to be named and structured, as many complex LaTeX projects which contain images and external style/class files often are.

#### Session Templates Endpoint
Templates to be rendered by the Jinja2 engine should be posted to `/api/sessions/<session_key>/templates` as json data.  The format is shown in the json form attached to the session resource when GET requesting the specific session endpoint as described above.

Three things will need to be specified, a path/name that the rendered file will be saved to, a text payload of the template text itself, and a json dictionary of data for Jinja2 to use in the template.  These three things will need to be posted simultaneously. 

Here is an example:
```json
{
  "name": "example.tex",
  "text": "\\documentclass{article}\\begin{document}\\section{\\EXPR{section_name}}\\end{document}",
  "data": {"section_name": "This is a Section Header"}
}
```

For more information on how the template grammar works see the section "Using Template Rendering" below.

#### Completed Product Endpoint
If a session is compiled successfully, the product can be retrieved with a GET request to `/api/sessions/<session_key>/product`

#### Log Endpoint
After compilation, regardless of whether the session's status is now "success" or "error" the log can be retrieved with a GET request to `/api/sessions/<session_key>/log`

#### Status Endpoint
The health of the service can be checked through the status endpoint, located at `/api/status`.

This will return the server's current time (in seconds) and a count of the number of extant sessions in the different states.

### Using the Template Rendering
[Jinja2](https://jinja.palletsprojects.com/en/2.11.x/) is a template rendering language/engine used in the Flask web framework and was designed to render template documents and dynamic data into HTML for a browser to display. However, with a slight change to the grammar, it fits neatly within LaTeX's syntax and can be used to generate documents with a less esoteric language than TeX.  

To that end, most documentation and tutorials for Jinja will apply for the template rendering on this service, with the current exception of template inheritance (this feature can be added if users would find it useful).  However, some replacements to the grammar will need to be taken into account.

#### Jinja2 Grammar Changes
In order to use reference material for Jinja2, note that the following substitutions have been made to the grammer to make it fit within LaTeX.

|Token|Jinja|LaTeX|
|-----|-----|-----|
|Block Start|{%|\BLOCK{|
|Block End|%}|}|
|Block (combined)|{% ... %}|\BLOCK{...}
|Expression Start|{{|\EXPR{
|Expression End|}}|}
|Expression (combined)|{{ ... }}|\EXPR{...}|
|Comment Start|{#|\\#{
|Comment End|#}|}
|Comment (combined)|{# ... #}|\\#{...}
|Line Statement|#|%#
|Line Comment|##|%##

#### Template Context
Jinja requires a data *context* when rendering a template.  This is a data dictionary full of content which is accessible to the various statements and expressions in the template itself.  

In the latex compile service, these are provided to the template in the form of a json dictionary uploaded with the template.  The keys in this dictionary are callable from within the template directly by name.  See Jinja's documentation for more details.

#### Simple Template Example

Imagine the following template:
```latex
\documentclass{article}
\begin{document}
    \BLOCK{ for s in sections }
        \section{\EXPR{s.name}}
        \EXPR{s.content}
    \BLOCK{ endfor }
\end{document}
```

When provided with the following context data:
```json
{
  "sections": [
        {"name": "This is Section A", "content": "This is the text content for section A"},
        {"name": "This is Section B", "content": "This is the text content for section B"}
    ]
}
```

Should produce the following output:
```latex
\documentclass{article}
\begin{document}
        \section{This is Section A}
        This is the text content for section A
        \section{This is Section B}
        This is the text content for section B
\end{document}
```

### Example Code
For an example of how to use the API, the file [example_client.py](https://github.com/mattj23/latex-compileservice/blob/master/example_client.py) demonstrates two use cases:

1. Compiling a document with an external image
2. Rendering a template and compiling it

To run the example client you will need Python 3 and a running instance of the service to point it at.

## Getting Started: Development

### The Development Environment

Because there are several parts of a working deployment, and because this repository contains a handful of integration tests, it will be easiest to perform development in an environment which can natively use Docker or docker-compose for debugging and testing.  I used PyCharm, which worked acceptably well with docker integration on both Windows and Linux.

There are currently no automated tests as part of the build pipeline to Docker Hub. I would like to implement this someday when I find the time.

### Project Structure

The folder structure of this repositiory has several top level directories.

* `deployment/` contains sample configuration files for deploying the service on/from different platforms
* `latex/` is the core source for the application, including the flask configuration and routes, the code for rendering and compiling, and shared data models
* `tests/` contains both the `pytest` unit and integration test code, as well as a subfolder containing .tex and image files for testing and for the example client

The top level folder also contains some files for docker and docker-compose including the primary Dockerfile for building the application container, and the python files which serve as entrypoints for the celery processes.

#### The Three Processes

In a deployment there are three different python processes which need to run.
1. The flask app itself, which is created by the wsgi server (or gunicorn) via the `create_app()` function in `latex/__init__.py`
2. The celery worker, which is launched with celery on the `worker.py` script. 
    * The internal plumbing is handled by celery itself, but this process is the one which executes the LaTeX compilers and `pdftoppm` for image conversion
    * It requires a shared directory with the flask app so that files uploaded to flask are accessible to the worker and its compilers
3. The celery scheduler, which is launched with celery on the `scheduler.py` script.   
    * The scheduler is only responsible for scheduling the worker task to clean up expired sessions

In a containerized environment like docker, the `run.sh` script in the root folder is used to deploy the correct process in a container based off of the environmental variable `COMPONENT`.  

### Where to Look For Stuff

This is a quick overview of where to look to find different parts of the project.  If you have some feature or modification in mind, this section may help you figure out where in the codebase to start looking.

#### Flask
* All flask routes are located in `latex/api_routes.py`.  If you're trying to extend or modify the API, this is where to start.
* Configuration is in `latex/config.py`, which both declares global configuration variables and sets their defaults.

#### Celery
* The celery processes are launched through `worker.py` and `scheduler.py` in the root folder, but these are just to set up and start the processes
* Celery tasks are located in `latex/tasks.py`, which are effectively declarations of what functions are accessible to the workers. They wrap code from other parts of the project, but if you need to add a potential background task at the very least you'll need to declare it here.

#### Session
The underlying resource for the application is a `Session`, which is in turn managed by `SessionManager`.  Everything related to these two python classes is located in `latex/session.py`.

`Session` stores data about a particular compilation job. It exists to store, display, and enforce the correctness of information relating to the job. One session is created for each job.

`SessionManager` is responsible for creating, persisting, deleting, and retrieving session information to and from the Redis server.  

If you want to modify what the sessions store and contain, start with the `Session` class and also check the `SessionManager`.

For changes to how the sessions are persisted, retrieved, etc, start with the `SessionManager`.

There is one additional construct of note, the `FileService` class which resides in `latex/services/file_service.py` and provides recursive abstraction over file system directories.  Its main purpose is to prevent path escape via symlinks or `../`, and to provide a very minimal abstraction over filesystem operations. If you need to extend or alter how the sessions and other elements interact with the filesystem, you will likely need to to do it here.

#### Rendering/Compilation/Image Conversion
All code related to the direct rendering of `jinja2` templates, the running of the different LaTeX compilers, and the running of the `pdftoppm` pdf to image converter are contained in `latex/rendering.py`.  These are not directly invoked by the flask app, but rather from the celery worker. 

For changes to compilation, the gathering of logs, working with files, this is a good starting place.

#### Unit and Integration Tests

All tests are located in `tests/`, and are separated by what they test.

* `test_file_service.py` is a set of tests related to the `FileService` class and its encapsulation of the filesystem, be aware that it relies on creating temporary files and folders through the `tempfile` module and so any environment running the tests will need that capability
* `test_latex_api.py` checks the correctness of the HTTP API, and also relies on the `tempfile` module to verify that the flask app is storing files correctly
* `test_rendering.py` verifies that compilation actions work, and so both relies on `tempfile` and being in an environment in which has the LaTeX compilers and `pdftoppm` installed, since these are invoked through python's `subprocess` module
* `test_sessions.py` mostly tests the `SessionManager` class and its ability to persist the sessions to a Redis server, and so needs to have an accessible Redis instance running at `REDIS_URL` in the configuation during the test.  It would be preferable to have this be a disposable instance created exclusively for the tests, because in the case that the test teardown doesn't happen properly there will be data left in the server.




