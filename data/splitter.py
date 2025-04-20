import csv
import os
from urllib.parse import urlparse

# Function to convert a URL into a valid filename
def url_to_filename(url):
    parsed = urlparse(url)
    # Extract the path, remove slashes, and replace '/' with '_'
    path = parsed.path.strip('/').replace('/', '_')
    query = parsed.query
    if query:
        # Replace '=' and '&' with '_' for query parameters
        query_part = query.replace('=', '_').replace('&', '_')
        filename = f"{path}_{query_part}.txt"
    else:
        filename = f"{path}.txt"
    return filename

# Dictionary to store data: {agent: {site: [prompts]}}
data = {}

# Step 1: Read the CSV file
with open('remaining_trials_count.csv', 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        agent = row['agent']
        site = row['site']
        prompt = row['prompt']
        trials = int(row['remaining_trials'])  # Convert remaining_trials to integer
        
        # Step 2: Organize data by agent and site
        if agent not in data:
            data[agent] = {}
        if site not in data[agent]:
            data[agent][site] = []
        
        # Repeat the prompt 'remaining_trials' times
        for _ in range(trials):
            data[agent][site].append(prompt)

# Step 3: Create folders and write text files
for agent in data:
    # Create agent folder if it doesn’t exist
    os.makedirs(agent, exist_ok=True)
    for site in data[agent]:
        # Generate filename from site URL
        filename = url_to_filename(site)
        filepath = os.path.join(agent, filename)
        
        # Write to the text file
        with open(filepath, 'w') as f:
            # Write the site URL on the first line
            f.write(site + '\n')
            # Write each prompt on a new line
            for prompt in data[agent][site]:
                f.write(prompt + '\n')