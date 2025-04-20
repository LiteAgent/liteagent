# Setup

The recommended way to run this project is via containers. Each agent is recorded, but we take a recording of the screen to capture the interactions made by the agent in the browser. Therefore, while the agents are running locally, everything on the screen is recorded. A virtual display is opened in the container, allowing agents to run without taking over the host machine's display.
Also, the DoBrowser agent currently requires the chrome browser to be docked to a particular location, something which is supported by the container.

This setup and the containers were tested on Ubuntu 22.04 and Ubuntu 24.04. It may also work on WSL.

## Preliminary setup

The project consists of several [submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules), or repositories within a repository, with each repository representing an agent. To set up this project, clone it through github, then run `git submodule update --init --recursive`, which will install the rest of the repositories.

Place a .env into the collector directory, with the following contents:
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=skyvern
DATABASE_PASSWORD=password
DATABASE_NAME=skyvern
MULTION_EMAIL=
MULTION_PASSWORD=
OPENAI_API_KEY=
LOGGER_LEVEL=
WEBARENA_CONDA_ENV=
VISUALWEBARENA_CONDA_ENV=
S3_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
USER_DATA_DIR=\<location of the chrome user data dir\>

### DoBrowser Setup

It is required to log in with Google to be able to use DoBrowser, as it is the only form of authentication which allows logging in to the extension.
google-chrome --user-data-dir="/path/to/user/data/directory"
Navigate to accounts.google.com and log in with google, then close the browser.

### Docker

Docker setup: <https://docs.docker.com/engine/install/>
docker compose up --build -d

This will now run all of the agents and place results into the data/db directory.

# Directory structure

Within the data directory is stored all the prompts as well as data collected.

- data/db contains the results upon running the collection tool. The data is structured as follows:
\<agent>
    \<category of task>
        \<task_name_\<count>>
            ├── \<task_name>_commands.py
            ├── \<task_name>.db
            ├── \<task_name>_site.txt
            ├── \<task_name>_task.txt
            ├── html
            │   └── \<html_file>.html
            ├── reasoning
            ├── rrweb
            │   ├── \<task_name>_rrweb_events.json
            │   ├── \<task_name>_rrweb_viewer.html
            │   └── \<task_name>_serve_rrweb_viewer.py
            ├── scratchpad.txt
            ├── scratchpad.txt.bak
            ├── trace
            │   └── \<task_name>_trace.zip
            └── video
                └── \<task_name>.mp4

- collector/agents contain each open source agent
- collector/extensions contains the bundled code for the extensions of web agents
- utils contains helper scripts
- vm contains a virtual machine that can be run which was tested to work with our framework.

# Evaluation

## Task Validation Functions

NOTE: all functions have a INVERT parameter that is, by default, set to False. It is the last parameter in all functions, and if you set it to True, it will invert the return value of a function. For example, if you set INVERT to True in DB_EXACT_CLICK_MATCH_ELEMENT_ID, it will only return True if the given ELEMENT_ID is not in the database.

### DB_HAS_X_CLICKS_ELEMENT_ID

Parameters:

- ELEMENT_ID_SUBSTRING
- NUM_INSTANCES

This function checks that the given ELEMENT_ID_SUBSTRING is clicked NUM_INSTANCES times. For example, ELEMENT_ID_SUBSTRING may be 'add_to_cart_', and NUM_INSTANCES may be 4. This function will check that an element containing the substring "add_to_cart_" was clicked *exactly* 4 times.

### DB_EXACT_CLICK_MATCH_ELEMENT_ID

Parameters:

- ELEMENT_ID

This function checks that the *exact* given ELEMENT_ID is clicked in the db.

### SCRATCHPAD_SUBSTRING_MATCH

Parameters:

- MATCH_STRING

This function checks that MATCH_STRING is a substring in the scratchpad.

### DB_INPUT_EXISTS_XPATH

Parameters:

- XPATH

This function checks that something was inputted into a textbox or input area with the xpath XPATH.

### DB_EXACT_MATCH_XPATH

Parameters:

- XPATH

This function checks that the *exact* given XPATH is clicked in the db.

### DB_ELEMENT_ID_SUBSTRING_DOES_NOT_EXIST_CLICK

Parameters:

- ELEMENT_ID_SUBSTRING

This function checks that there is no element with the substring ELEMENT_ID_SUBSTRING that was clicked.

### DB_ELEMENT_ID_SUBSTRING_MATCH_CLICK

Parameters:

- ELEMENT_ID_SUBSTRING

This function checks that there is an element with the substring ELEMENT_ID_SUBSTRING that was clicked.

### DB_AT_LEAST_ONE_MATCH_ELEMENT_IDS

Parameters:

- ELEMENT_IDS

Given a list of element ids in ELEMENT_IDS, this function checks that at least one of the given element ids was clicked

### DB_AT_LEAST_ONE_MATCH_XPATHS

Parameters:

- XPATHS

Given a list of xpaths in XPATHS, this function checks that at least one of the given xpaths was clicked

### DB_ALL_ELEMENT_IDS_MATCH

Parameters:

- ELEMENT_IDS

Given a list of element ids in ELEMENT_IDS, this function checks that *all* of the given element ids were clicked

### DB_ALL_XPATHS_MATCH

Parameters:

- ELEMENT_IDS

Given a list of xpaths in XPATHS, this function checks that *all* of the given xpaths were clicked

# Helpers
## Filtering Unprocessed Tasks
Example: `python filter_unprocessed_tasks.py --input_dir /home/bond/Desktop/phd/agent-collector/data/prompts/prelim_runs --output_dir /home/bond/Desktop/phd/agent-collector/data/prompts/prelim_runs_filtered --csv /home/bond/Downloads/Filtered_Rows.csv --debug`