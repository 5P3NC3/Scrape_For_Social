IOT download the project run "git clone https://github.com/5P3NC3/Scrape_For_Social.git".
'just_run_me.py" will run create_checked_list.py and then scrape_checked_list.py. 
create_checked_list.py will ask for a list of fqdns without schemes. It will visit each site and create a list called checked_urls.txt full of accessable sites.
scrape_checked_list will scrape each site in checked_urls.txt for social links.
If you run scrape_checked_list without checked_urls.txt it will ask for a list of urls with schemes and check those urls for social links.
After all social links are found, scrape_checked_list.py with then connect to each social link and check for 404 status codes or error_messages.
Run test.py to make sure error_messages are still good and haven't been changed by the various social medias it reaches out to. 
