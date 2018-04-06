# bbpypline
Run bitbucket pipeline locally

## Requirements
For mac user the only requirements is an updated version of Docker installed.
For linux you will need python3.6 or later and an update version of Docker

## Install
### Mac 
`brew install WellDone2094/bbpypeline/bbpypeline`

### Linux
Install the requirements with pip<br>
`pip3 install -r requirements.txt`

Install the package<br>
`python3 setup.py install`

Now you should be able to run `python3 bbpypeline.py`

If you want to crate an executable checkout [pyinstaller](https://www.pyinstaller.org/)

## Usage
Move inside your project folder and run the follow command to execute the bitbucket-pipeline.<br>
`bbpypeline`<br>
This will load bitbucket-pipeline.yml file and copy all the files in the current directory inside 
the docker container specified inside the pipeline and execute the default pipeline.

`bbpypeline -f my-pipeline.yml` execute my-pipeline.yml<br>
`bbpypeline --stop` stop execution as soon as a step fails<br>
`bbpypeline --verbose` display console output while running the pipeline

### Exclude files from docker
To exclude files from being copied inside the docker container (eg. node_modules) crate a file 
called `.bbignore` as follow.

```
src/ignore_this_file.txt
**/*.pyc
**/node_modules
```

The first line exclude a specific file, the second line exclude all the file with extension .pyc
the last line remove all the folders called node_modules at every depth





