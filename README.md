# LaTeX Compileservice

A Flask based web service that compiles LaTex projects to document form and uses the Jinja2 engine to render templates and data to .tex files.  Ready to deploy with `docker-compose`, or other container orchestration system.  Can be installed directly on a server OS with a bit more effort.

## Quickstart

*This describes a quick-start deployment using the `docker-compose.yaml` file included in the repository, which is the fastest way to get started. More complex deployments can be assembled by modifying the compose file, using the `docker-compose.dev.yaml` file, starting docker images manually, or using kubernetes.  The service can also be installed directly on the OS of a physical or virtual server.*

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

This project is essentially a small Flask app built on top of an ubuntu docker image with `texlive-full` installed, inspired by `blang/latex:ubuntu` ([Github](https://github.com/blang/latex-docker), [DockerHub](https://hub.docker.com/r/blang/latex)) but derived from `ubuntu:bionic` (rather than `xenial`) for the considerable improvements in the 3.6 version of python. 

Additionally, `jinja2` can be used to render templates to LaTeX files which will then be compiled with other source files, allowing for a slightly more sane scripting environment than plain TeX.  The `jinja2` grammar was slightly altered to be more compatible with LaTeX's quirks in a way that is inspired by, but slightly different from, [this blog post by Brad Erikson](http://eosrei.net/articles/2015/11/latex-templates-python-and-jinja2-generate-pdfs).

### Why as a service, and why containerized?
LaTeX, though quite powerful, can be a frustrating toolset to install and maintain, especially across platforms. A comprehensive installation can be several gigabytes in size, and seems to be easily broken.  Online tools like [Overleaf](https://www.overleaf.com) ([source on GitHub](https://github.com/overleaf)) clearly show how much pain can be saved by not maintaining individual installations, but Overleaf itself is structured towards the concepts of users and projects and isn't quite a lightweight service meant to be consumed by other services. 

Deploying a containerized service that houses a `texlive-full` installation and can live on any platform capable of hosting a Docker container takes nearly all of the pain out of managing it.  There's nothing to be broken during upgrades, and no complex setup to be lost when a server dies.  By making this app nearly stateless (it does store information, but only for a few minutes at a time) it is also extremely easy to migrate from host to host and to scale up or down as needed.  It's also easy to upgrade and redeploy.

In my experience, the additional layer of abstraction induced by Docker is a net benefit, because I have found the additional complexity of Docker to be far less than the complexity of managing LaTeX.  However, a determined user/sysadmin can deploy this service outside of a container by installing the Flask app, the Celery worker, and the Celery scheduler as system services on a physical or virtual machine with a LaTeX toolchain, and pointing them at either a local or network-accessible Redis server.

### What makes this project different?

There are a few projects out there which put LaTeX compilation tools in a Docker image with a web application over them.  The most comprehensive seems to be [vsfexperts/LaTeX](https://github.com/vsfexperts/LaTeX) which unfortunately takes the entire content to be rendered in the POST request, meaning that multiple files (like custom classes, or images) cannot be rendered.  There is also [DMOJ/Texoid](https://github.com/DMOJ/texoid), but it is focused on rendering LaTeX math symbols to graphics formats.  There are an additional handful of similar projects, but most suffer from inadequate documentation or the limitation of using POST to submit a single document to be rendered.

What I think the benefits of this project over the existing projects are:

1. Send multiple files to the service, including a local nested directory structure. For example, you can set the main compilation target to `./sample.tex` and have that file reference several other files, such as `./diagram.png`, `./common/logo.png`, `./common/classes/org-doc.cls`, and `./common/classes/org.sty`

2. Specify your choice of compiler for each compilation session.  You can use `pdflatex`, `xelatex`, or `lualatex`, some of which are capable of different things.

3. Use the `jinja2` engine to render `.tex` template files containing `jinja`'s python-like syntax to valid LaTeX, which will then be compiled as part of your project.  Submit the data to render to the template as a `json` dictionary. This is an easier way of producing generated documents for most people than trying to use LaTeX's programming mechanisms directly.

4. Ample documentation and examples to clearly demonstrate
    1. How to set up and deploy the service
    2. How to use the service, with all of its different features
    3. How to develop or extend the project

## Getting Started - User
### Deploying the Service

#### Deploying with Docker Compose or Swarm Mode
If using Docker, and specifically Docker Compose or Docker Swarm Mode, the setup and deployment of the service is extremely straightforward and can mostly be accomplished by the use of the included YAML files. 

In the main directory of this git repository, there are two `docker-compose.*.yaml` files. One is aimed at a production environment, and the other is for development.

In either case, four containers will be created, one for the Flask app itself, one for the Celery worker, one for the Celery scheduler, and one for Redis.  The Celery worker and the Flask app will need to be able to share file storage, so must have a common volume in which the Flask app can store and retrieve files and the worker can run the LaTeX compilers.

> As a note: because of Docker's copy-on-write Union File System, the running of the three separate containers does not translate into multiple copies of the frankly massive 3+ Gb base image, since almost all of it is shared between the different containers.  With some shell scripting effort, a user/sysadmin can combine all of the processes into a single container, but this will strip away any external orchestration tool's ability to manage the health of the different processes with little tangible benefit in exchange.

##### Production: "docker-compose.yaml"
For a production-oriented environment use the `docker-compose.yaml` file. It uses gunicorn as the WSGI server and has the Flask environment set for production.  Celery's loglevel is set to "info" and the shared volume is set up in the compose file.  

There is only one worker container specified.  I do not currently know what the load is which would require a second or third worker and what benefits that would have over multiple copies of the service itself, but if you're using Docker swarm mode there should be no harm in using the "replicas" option to scale the number of workers.  It is *not* safe to scale the number of Celery beat schedulers, however, which is why the worker and beat scheduler were separated into two different containers instead of running the worker with the embedded scheduler via the `-B` option.  You can alter the `run.sh` shell script to include the `-B` option on the worker and remove the scheduler container if you know for a fact that you will never, in that case, run more than one worker.  However I don't believe there is any benefit to doing so.

### Using the Service
#### Overview of the API
#### Using the Template Rendering
#### Example Code

## Getting Started - Developer
### The Development Environment
### Project Structure
#### The Three Processes




