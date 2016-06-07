# Setting up

## Python / Requirements
You may need to install the following:
python-imaging, pip, sqlalchemy, oauth2client, Flask, requests
`
sudo apt-get install python-imaging
sudo apt-get install python.pip
sudo pip install sqlalchemy
sudo pip install oauth2client
sudo pip install Flask
sudo pip install requests
`

## G+ Sign in

- Go to https://console.cloud.google.com/ and sign in.
- In the top navbar, create a project.
- Name your project and click create.
- Go to API Manager / Credentials.
- Click Create credentials / OAuth Client ID.
- Configure the consent screen if necessary and click Save.
- For the Application type, select Web application.
- Select a name, then add
  - Authorized JavaScript origins: `http://localhost:5000`
  - Authorized redirect URIs: `http://localhost:5000/login`, `http://localhost:5000/gconnect`
- Click Create.
- You should see your OAuth client ID and client secret.
- In login.html, update `data-clientid="YOUR_CLIENT_ID_HERE"` with your client ID.
- You should have one OAuth 2.0 client ID, with a download arrow on the right side. Download the JSON file.
- Move the file to your project directory and rename it `client_secrets.json`.



Run database_setup.py:
`
python database_setup.py
`

Optional: add example catalog
`
python example_catalog.py
`
And unzip example_photos.zip to /catalog/uploads/photos/

Run the project:
`
python project.py
`
Access it in your browser:
http://localhost:5000

# Using:

PIL for creating thumbnails (apt-get install python-imaging)

Isotope for image layout (http://isotope.metafizzy.co/)

lightbox2 for lightbox (http://lokeshdhakar.com/projects/lightbox2/)

jscolor picker (http://jscolor.com/)
