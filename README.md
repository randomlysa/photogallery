# Setting up
You may need to install the following:
python-imaging, pip, sqlalchemy, oauth2client, Flask, requests
```
sudo apt-get install python-imaging
sudo apt-get install python.pip
sudo pip install sqlalchemy
sudo pip install oauth2client
sudo pip install Flask
sudo pip install requests
```


Run database_setup.py:
```
python database_setup.py
```

Optional: add example catalog
```
python example_catalog.py
```
And unzip example_photos.zip to /catalog/uploads/photos/

Run the project:
```
python project.py
```
Access it in your browser:
http://localhost:5000

# Using:

PIL for creating thumbnails (apt-get install python-imaging)

Isotope for image layout (http://isotope.metafizzy.co/)

lightbox2 for lightbox (http://lokeshdhakar.com/projects/lightbox2/)

jscolor picker (http://jscolor.com/)
