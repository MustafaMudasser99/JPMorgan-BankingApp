# Dummy Banking Application Project

## Instructions 
### Week 1 - Agile
### Week2 - Running the project

Clone the project with git
Fork the repo in github first to your account .
After forking clone your repo to which you will have push rights.

`git clone https://github.com/ [your_gh_account_here] /bu_banking.git`

Change directory to application

`cd bu_banking`

Activate python virtual environment to keep your environment clean - we will install all python dependencies inside python venv

`python3 -m venv venv`


Activate virtual env (you will have to do it each time if you wont automate)
**Linux:**

`source venv/bin/activate`

**Windows:**
cmd.exe |  <C:\> <venv>\Scripts\activate.bat
PowerShell |  C:\> <venv>\Scripts\Activate.ps1

Install python packages within this virtualenvironment

`pip3 install -r requirements.txt`

Run the application

`python3 manage.py runserver 0.0.0.0:8000`

Access website on your localhost http://127.0.0.1:8000/api/

Endpoints

Django rest default page: http://127.0.0.1:8001/api/
Redoc : http://127.0.0.1:8001/api/redoc/
Swagger : http://127.0.0.1:8001/api/swagger/

Explore!!

To create superuser stop running server and run (within venv)

`python3 manage.py createsuperuser`

### Week3 - Containerization

Make sure you have docker installed. (docker-desktop/wsl on windows)

* withing your project directory create Dockerfile with content
`FROM python:3.12

WORKDIR /app

COPY . /app

RUN ["pip3","install","-r","requirements.txt"]

CMD ["python3","manage.py","runserver","0.0.0.0:8000"]`

Build image out of above Dockerfile

`docker build -t banking .`

Check your images

`docker image ls`

After succesfull build run the container from image you have build 

`sudo docker run -p 8001:8000 banking`

Access website on your localhost http://127.0.0.1:8000/api/

now kill the server Ctrl+C

and run docker compose which will share local drive to the container - this way you will be able to edit files and see changes in container.
Make sure you have docker-compose installed try with running 

`docker-compose` or `docker compose`

Create docker-compose.yml within project directory

```
version: '3.8'

services:
  agent-zero-run:
    image: banking
    build: . #this will build from current dir if banking image is not on your system
    ports:
      - "8000:8000"
    env_file:
      - ./.env #env vars if you need them in app container
    volumes:
      - ./:/app    
    restart: "no"

```

Run 
`docker-compose up` or `docker compose up`
 you should see similar:

```
 sudo docker compose up
[+] Running 2/2
 ✔ Network bu_banking_default             Created                                                                  0.2s
 ✔ Container bu_banking-agent-zero-run-1  Created                                                                  0.0s
Attaching to bu_banking-agent-zero-run-1
bu_banking-agent-zero-run-1  | Watching for file changes with StatReloader
```
access page on http://127.0.0.1:8000/api/


### Week4 - SDLC CICD

Enter project directory and then cicd dir

`cd cicd`

run cicd stack with 

`docker-compose up`

That will take a while as will need to pull 8 different images 

After it's run access Jenkins on 8080




Create ssh key pair with 

`ssh-keygen -t ed25519 -C "your_email@example.com"`

You will have public and private keys in your home directory

ls /home/greg/.ssh/
id_ed25519  id_ed25519.pub 

Private key is without any extension this goes to Jenkins

### Week5 - Automation Testing 

## OPENPROJECT:

https://twopointzero.me/

**Epics** are tied to each week’s overall theme (e.g., “Introduction to Containers” or “SDLC”).

**User Stories** capture what each group (Leadership or Engineering) needs in order to fulfill that theme.

**Tasks** are concrete actions or deliverables needed to complete the User Stories.

Engineering:
Feel free to assign yourselk to the tasks and resolve them.
Leadership: 
Collaborate with engineering - comment on tasks/epics/user stories to validate if the user stories were delivered.

