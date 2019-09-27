# LaTeX Renderservice

> _This project is currently in a proof of concept state. LaTeX tools are run as a python `subprocess` by the main Flask app and block. Sessions (uploaded sets of files to be rendered) are stored in directories inside the container and are never cleaned up after they complete._
> 
> _My actual goal for the project is to use Redis and a RQ message queue to offload tasks to background workers, and have the completed renderings stored only for a brief amount of time before being cleaned up._
> 
> _In the much longer term, I'd like to add a simple web frontend that will allow a user to manually upload or edit files and retrieve the results, like a much simpler version of Overleaf._

## Quickstart

With the project currently in a proof-of-concept state, there isn't yet much to see.  You can currently:

1. Use `docker-compose` to build and run the app 
    * From the main project directory, `docker-compose up -d --build`
    * the app should be reachable at http://localhost:5000
2. Send files to be rendered
    * See `test_client.py` for an example of how to use python to interact with the API
    * You will need to send the files in the POST request to http://localhost:5000/api/1.0/session
    * You will also need to send (as form data) a `compiler` and `target` field 
    * `compiler` can currently be either `"xelatex"` or `"pdflatex"`
    * `target` is the file that was sent which is to be the main input file given to the compiler, it can reference other files which were provided by their relative paths
    * for example: `{"compiler": "xelatex", "target": "my_tex_file.tex"}` in python
    * you will get a JSON response, either it will contain an `error` field if something went gracefully wrong, or a `success` field if it went right.  If it went right you will also get a `session_key` in the response, which is how you can retrieve the rendered file, and a field that contains the entire log of the tex compiler
3. Retrieve your rendered file
    * create a GET request to http://localhost:5000/api/1.0/product/SESSION_KEY
    * the SESSION_KEY comes from the POST request above
    * the server will return your file

## Overview

This project is a LaTeX rendering web service intended to run in a Docker container, and interacted with by other software through a REST api. It is written in Python3 and uses Flask.

This software was developed as a lightweight (as lightweight as one can reasonably call something housing a full LaTeX installation) infrastructure service for automated document generation. It is meant to be simple and reliable, able to be deployed once for an organization or group and provide the rendering of latex files for many other applications without requiring them to each maintain their own LaTeX toolchain.

This project is essentially a small Flask app built on top of an ubuntu docker image with `texlive-full` installed, inspired by `blang/latex:ubuntu` ([Github](https://github.com/blang/latex-docker), [DockerHub](https://hub.docker.com/r/blang/latex)) but derived from `ubuntu:bionic` (rather than `xenial`) for the 3.6 version of python. 

### Why as a service, and why Docker?
LaTeX, though quite powerful, can be a frustrating toolset to install and maintain, especially across platforms. A comprehensive installation can be several gigabytes in size, and seems to be easily broken.  Online tools like [Overleaf](https://www.overleaf.com) ([source on GitHub](https://github.com/overleaf)) clearly show how much pain can be saved by not maintaining individual installations, but Overleaf itself is structured towards the concepts of users and projects and isn't quite a lightweight service meant to be used by other services. 

Over the past 10 years, I've often relied on LaTeX to generate business documents as part of automated information systems in small business environments.  I would develop the code and the LaTeX templates on my windows workstation with a MikTeX installation, then end up having to re-install everything onto the target machine.  Invaribly some considerable time would pass and either I'd have upgraded laptops or the deployment machine would become unreliable or broken by some update, and putting everything back together would become an all day affair.  Adding another system that needed LaTeX compilation would never end up being as simple as using the existing machine with the already installed toolchain, as I would always end up breaking something.

Docker is great for a lot of reasons, but the one I'm most fond of is that it has largely eliminated the dependency hell involved in setting up machines to host applications that rely on less widely used components.  In the SME world, it's difficult to overstate the value of being able to trivally redeploy an important service after the ancient tower running in a neglected closet that hosted it for the better part of the past decade finally decides it's too tired to carry on.

### What makes this project different?

There are a few projects out there which put LaTeX compilation tools in a Docker image with a web application over them.  The most comprehesive seems to be [vsfexperts/LaTeX](https://github.com/vsfexperts/LaTeX) which unfortunately takes the entire content to be rendered in the POST request, meaning that multiple files (like custom classes, or images) cannot be rendered.  There is also [DMOJ/Texoid](https://github.com/DMOJ/texoid), but it is focused on rendering LaTeX math symbols to graphics formats.  There are an additional handful of similar projects, but most suffer from inadequate documentation or the limitation of using POST to submit a single document to be rendered.

## Getting Started - User
### Deploying the Service

### Using the Service

## Getting Started - Developer



