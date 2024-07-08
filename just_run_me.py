#This script will run create checked list and scrape checked list back to back. If you
#already have a list thats been checked you can just run scrape checked list on it's own. 

import subprocess

def run_script(script_name):
    subprocess.run(["python", script_name])

def main():
    run_script("create_checked_list.py")
    run_script("scrape_checked_list.py")

if __name__ == "__main__":
    main()
    
    
