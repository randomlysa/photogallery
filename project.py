from flask import Flask, render_template, request, redirect, \
    jsonify, url_for, flash


from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, CatalogItem, User

from flask import session as login_session
import random
import string

# to make thumbnails
from PIL import Image
import glob

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# for uploads
import os
from flask import send_from_directory
# for securing uploads
from werkzeug import secure_filename

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Catalog Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/error')
def error():
    return render_template('error.html')


def makeThumbnail(path, imageExtension):
    try:
        # os.path.join(app.config['UPLOAD_FOLDER'], newFilename)
        original = Image.open(
            os.path.join(app.config['UPLOAD_FOLDER'], imageExtension)
        )
    except:
        print "image doesn't exist"

    # split name from extension
    imageName = imageExtension.rsplit('.', 1)[0]

    width, height = original.size  # ex 800x600
    ratio = float(height) / width  # ex: 0.75
    newWidth = 400
    newHeight = width * ratio  # 262.5 = 350 * 0.75
    size = (newWidth, newHeight)
    original.thumbnail(size)

    '''
    canceling the idea of cropped thumbnails for now
    if newHeight > 231:
        # image is portrait orientation. crop the height 231
        print "cropping" + imageName
        crop = original.crop((0,0,350,231))
        newTnName = imageName + "-tn.jpg"
        crop.save(os.path.join(app.config['UPLOAD_FOLDER'], newTnName))
    else:
    '''

    newTnName = imageName + "-tn.jpg"
    original.save(os.path.join(app.config['UPLOAD_FOLDER'], newTnName))
    # im.save(file + "-tn.", "jpg")
    return newTnName


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fblogin')
def fblogin():
    return render_template('fblogin.html')


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # short lived token (?)
    short_access_token = request.data
    print "access token received %s " % short_access_token

    app_id = 'YOUR_APP_ID' # update this line
    app_secret = 'YOUR_APP_SECRET' # update this line

    # get fb_exchange_token
    # https://developers.facebook.com/docs/facebook-login/access-tokens/expiration-and-extension
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (  # nopep8
        app_id, app_secret, short_access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.6/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    # this should be JSON formatted
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session
    # in order to properly logout,
    # let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token  # nopep8
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: \
                    150px;-webkit-border-radius: 150px;-moz-border-radius: \
                    150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'\
        % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                'Current user is already connected.'
        ),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;border-radius: \
                150px;-webkit-border-radius: 150px;-moz-border-radius: \
                150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(
                name=login_session['username'],
                email=login_session['email'],
                picture=login_session['picture']
    )
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Catalog Information
@app.route('/catalog/JSON')
def allCatalogsJSON():
    catalogs = session.query(Catalog).all()
    return jsonify(catalogs=[r.serialize for r in catalogs])


@app.route('/catalog/<int:catalog_id>/JSON')
def oneCatalogJSON(catalog_id):
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    items = session.query(CatalogItem).\
        filter_by(catalog_id=catalog_id).all()
    return jsonify(CatalogItems=[i.serialize for i in items])


@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/JSON')
def menuItemJSON(catalog_id, item_id):
    Catalog_Item = session.query(CatalogItem).filter_by(id=item_id).one()
    return jsonify(Catalog_Item=Catalog_Item.serialize)


# upload a photo for the catalog header or for a catalog item
'''
    problems:
        (edit) when a new image is uploaded, the old one is not deleted
        (edit or new) files are all stores in the same
        directory with the original filename
            if the same image is used for two items, and one item is delete,
            the image will be deleted for the other item
    possible solution - rename images:
        for catalog header: %user%_header_%catalogid% (since id is unique)
        for catalog items: %user%_%catalogid%_item_%itemid%
        - will not have to delete old image when editing
            since the new image will have the same
            name as the old image and overwrite it
        - each image will have a unique name
'''
UPLOAD_FOLDER = "/vagrant/catalog/uploads/photos"
ALLOWED_EXTENSIONS = set(['jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/uploads/<int:id>/<type>/')
# def show_file(filename):
def show_file(id, type):
    if type == 'header_image' or type == 'header_image_tn':
        # get the catalog that we want the header image for
        catalog = session.query(Catalog).filter_by(id=id).one()

        if type == 'header_image':
            filename = catalog.header_image
        if type == 'header_image_tn':
            filename = catalog.header_image_tn
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    if type == 'item_image' or type == 'item_image_tn':
        # get the item that we want the image for
        item = session.query(CatalogItem).filter_by(id=id).one()

        if type == 'item_image':
            filename = item.item_image
        if type == 'item_image_tn':
            filename = item.item_image_tn
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Show all catalogs
@app.route('/')
@app.route('/catalog/')
def showCatalogs():
    catalogs = session.query(Catalog).order_by(Catalog.user_id.asc())
    users = session.query(User).order_by(User.name.asc())

    if 'username' not in login_session:
        return render_template(
            'publicCatalogs.html', catalogs=catalogs, users=users
        )
    else:
        user = getUserInfo(login_session['user_id'])
        return render_template(
            'privateCatalogs.html', catalogs=catalogs, loggedInUser=user
        )


# Create a new catalog
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newCatalog():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        '''
            newCatalog = Catalog(
                name=request.form['name'], user_id=login_session['user_id'],
                header_image=request.form['image']
                )
            '''
        newCatalog = Catalog(
                name=request.form['name'],
                user_id=login_session['user_id'],
                header_color=request.form['header_color'],
                catalog_image_type=request.form['catalog_image_type']
        )

        session.add(newCatalog)

        # get id of catalog that was created
        # this is probably not the best way to do this...
        lastCatalog = session.query(Catalog).\
            order_by(Catalog.id.desc()).first()
        catalog_id = lastCatalog.id

        # check if an image was uploaded
        file = request.files['file']
        if file and allowed_file(file.filename):
            # print "in the upload app for newCatalog"

            extension = file.filename.rsplit('.', 1)[1]
            # original filename secured
            filename = secure_filename(file.filename)

            # renamed filename user#_catalog#_header.(extension)
            newFilename = "user" + str(login_session['user_id']) \
                + "_catalog" + str(catalog_id) + "_header" "." + extension

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], newFilename))
            # makeThumbnail(app.config['UPLOAD_FOLDER'], newFilename)
            # make sure to update the renamed filename in the database
            lastCatalog.header_image = newFilename
            lastCatalog.header_image_tn = \
                makeThumbnail(app.config['UPLOAD_FOLDER'], newFilename)

            session.add(lastCatalog)
            session.commit()
        # end of upload section

        flash('New Catalog \'%s\' Successfully Created' % newCatalog.name)
        session.commit()
        # return redirect(url_for('showCatalogs'))
        # send the user to the catalog that was just made
        return redirect(url_for('showCatalog', catalog_id=lastCatalog.id))
    else:
        return render_template('newCatalog.html')


# Edit a catalog
@app.route('/catalog/<int:catalog_id>/edit/', methods=['GET', 'POST'])
def editCatalog(catalog_id):
    if 'username' not in login_session:
        return redirect('/login')

    editedCatalog = session.query(
        Catalog).filter_by(id=catalog_id).one()

    # check if the user logged in is the catalog owner
    if editedCatalog.user_id != login_session['user_id']:
        return redirect('/error')

    # two lines for debugging
    print editedCatalog.user_id
    print login_session['user_id']

    '''
      if editedCatalog.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not \
                    authorized to edit this catalog. Please create your\
                    own!');}</script><body onload='myFunction()'>"
      '''

    if request.method == 'POST':
        # check if an image was uploaded
        file = request.files['file']
        if file and allowed_file(file.filename):
            # print "in the upload app for editCatalog"

            extension = file.filename.rsplit('.', 1)[1]
            # original filename secured
            filename = secure_filename(file.filename)

            # renamed filename user#_catalog#_header.(extension)
            newFilename = "user" + str(login_session['user_id']) \
                + "_catalog" + str(catalog_id) + "_header" "." + extension

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], newFilename))

            # make sure to update the renamed filename in the database
            editedCatalog.header_image = newFilename
            editedCatalog.header_image_tn = \
                makeThumbnail(app.config['UPLOAD_FOLDER'], newFilename)

        # end of upload section

        # check if header color was changed
        if request.form['header_color']:
            print "new header color"
            editedCatalog.header_color = request.form['header_color']

        # check if the catalog was renamed
        if request.form['name']:
            editedCatalog.name = request.form['name']

        # update catalog_image_type
        if request.form['catalog_image_type']:
            editedCatalog.catalog_image_type = \
                request.form['catalog_image_type']

        session.commit()
        flash('Catalog \'%s\' Successfully Edited' % editedCatalog.name)
        # return user to the catalog they edited
        return redirect(url_for('showCatalog', catalog_id=editedCatalog.id))
        # return redirect(url_for('showCatalogs'))
    else:
        return render_template('editCatalog.html', catalog=editedCatalog)


# Delete a catalog
@app.route('/catalog/<int:catalog_id>/delete/', methods=['GET', 'POST'])
def deleteCatalog(catalog_id):
    if 'username' not in login_session:
        return redirect('/login')

    catalogToDelete = session.query(
        Catalog).filter_by(id=catalog_id).one()

    # check if the user logged in is the catalog owner
    if catalogToDelete.user_id != login_session['user_id']:
        return redirect('/error')

    # items associated with the catalog, to be deleted
    catalogItemsToDelete = session.query(CatalogItem)\
        .filter_by(catalog_id=catalogToDelete.id)
    if request.method == 'POST':
        # delete images and thumbnails from /uploads
        for deleteThis in catalogItemsToDelete:
            os.remove(
                "/vagrant/catalog/uploads/photos/" + deleteThis.item_image
            )
            os.remove(
                "/vagrant/catalog/uploads/photos/" + deleteThis.item_image_tn
            )
            # delete items from the database
            session.delete(deleteThis)
        # if there is a header image, delete the image and thumbnails
        if (catalogToDelete.header_image):
            os.remove(
                    "/vagrant/catalog/uploads/photos/" +
                    catalogToDelete.header_image
            )
            os.remove(
                    "/vagrant/catalog/uploads/photos/" +
                    catalogToDelete.header_image_tn
            )
        session.delete(catalogToDelete)
        flash('Catalog \'%s\' Successfully Deleted' % catalogToDelete.name)
        session.commit()
        return redirect(url_for('showCatalogs', catalog_id=catalog_id))
    else:
        # flash('Catalog \'%s\' NOT Deleted' % catalogToDelete.name)
        return render_template('deleteCatalog.html', catalog=catalogToDelete)


# Show a catalog
@app.route('/catalog/<int:catalog_id>/')
# @app.route('/catalog/<int:catalog_id>/catalog/')
def showCatalog(catalog_id):
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    creator = getUserInfo(catalog.user_id)
    items = session.query(CatalogItem).filter_by(
        catalog_id=catalog_id).all()
    # can't figure out why I'm getting a pep8 error here
    if 'username' not in login_session \
        or creator.id != login_session['user_id']:

            return render_template(
                            'publicCatalog.html', items=items,
                            catalog=catalog, creator=creator
            )
    else:
        return render_template(
                        'privateCatalog.html', items=items,
                        catalog=catalog, creator=creator,
                        loggedInUser=login_session['user_id']
        )


# Create a new catalog item
@app.route('/catalog/<int:catalog_id>/item/new/', methods=['GET', 'POST'])
def newCatalogItem(catalog_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':

        # check if an image was uploaded
        file = request.files['file']
        if file and allowed_file(file.filename):
            # print "in the upload app for newCatalogItem"
            # print file.filename
            extension = file.filename.rsplit('.', 1)[1]
            filename = secure_filename(file.filename)
            lastId = session.query(CatalogItem).\
                order_by(CatalogItem.id.desc()).first()
            # for the first item in the database, lastId will not have an .id
            try:
                nextId = lastId.id + 1
            except AttributeError:
                nextId = 1

            # rename the file to user[id]_catalo[id]_item[id].extension
            filename = "user" + str(login_session['user_id']) + "_catalog" + \
                str(catalog_id) + "_item" + str(nextId) + "." + extension
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            item_image_tn = makeThumbnail(
                app.config['UPLOAD_FOLDER'], filename
            )

            newItem = CatalogItem(
                        name=request.form['name'],
                        description=request.form['description'],
                        item_image=filename,
                        item_image_tn=item_image_tn,
                        catalog_id=catalog_id,
                        user_id=catalog.user_id
            )
        # end of image upload section
        # if no image was uploaded, newItem will not have a filename
        else:
            newItem = CatalogItem(
                        name=request.form['name'],
                        description=request.form['description'],
                        catalog_id=catalog_id, user_id=catalog.user_id
            )
        session.add(newItem)
        session.commit()

        flash('New Item \'%s\' Successfully Created' % (newItem.name))
        return redirect(url_for('showCatalog', catalog_id=catalog_id))
    else:
        return render_template(
            'newCatalogItem.html',
            catalog_id=catalog_id, catalog_name=catalog.name
        )


# Edit a catalog item
@app.route(
        '/catalog/<int:catalog_id>/item/<int:item_id>/edit',
        methods=['GET', 'POST']
)
def editCatalogItem(catalog_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(CatalogItem).filter_by(id=item_id).one()
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()

    # check if the user logged in is the item owner
    if editedItem.user_id != login_session['user_id']:
        return redirect('/error')

    if request.method == 'POST':
        # check if an image was uploaded
        file = request.files['file']
        if file and allowed_file(file.filename):
            # print "in the upload app for newCatalogItem"

            extension = file.filename.rsplit('.', 1)[1]
            # original filename secured
            filename = secure_filename(file.filename)

            # renamed filename user#_catalog#_item#.(extension)
            newFilename = "user" + str(login_session['user_id']) \
                + "_catalog" + str(catalog_id) + "_item" + str(item_id) \
                + "." + extension

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], newFilename))

            # make sure to update the renamed filename in the database
            editedItem.item_image = newFilename
            editedItem.item_image_tn = \
                makeThumbnail(app.config['UPLOAD_FOLDER'], newFilename)

        # end of upload section

        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash('Catalog Item \'%s\' Successfully Edited' % editedItem.name)
        # return user to the catalog that they edited
        return redirect(url_for('showCatalog', catalog_id=catalog_id))
    else:
        return render_template(
                'editCatalogItem.html', catalog_id=catalog_id,
                item_id=item_id, item=editedItem
        )


# set item as catalog thumbnail
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/setItemAsThumb')
def setItemAsThumb(catalog_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    # itemToDelete = session.query(CatalogItem).filter_by(id=item_id).one()

    # check if the user logged in is the item owner
    if catalog.user_id != login_session['user_id']:
        return redirect('/error')

    print item_id
    catalog.catalog_thumbnail = item_id
    session.add(catalog)
    session.commit()

    # return to list of catalogs so you can see the new thumbnail
    return redirect(url_for('showCatalogs'))


# Delete a catalog item
@app.route(
        '/catalog/<int:catalog_id>/item/<int:item_id>/delete',
        methods=['GET', 'POST']
)
def deleteCatalogItem(catalog_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    itemToDelete = session.query(CatalogItem).filter_by(id=item_id).one()

    # check if the user logged in is the item owner
    if itemToDelete.user_id != login_session['user_id']:
        return redirect('/error')

    if request.method == 'POST':
        # check if there is an image to delete
        print "in the post"
        if itemToDelete.item_image:
            print "image to delete: " + itemToDelete.item_image
            os.remove(
                "/vagrant/catalog/uploads/photos/" + itemToDelete.item_image
            )
        # end delete image
        session.delete(itemToDelete)
        session.commit()
        flash('Catalog Item \'%s\' Successfully Deleted' % itemToDelete.name)
        return redirect(url_for('showCatalog', catalog_id=catalog_id))
    if request.method == 'GET':
        # print "getting something"
        # flash('Catalog Item \'%s\' NOT Deleted' % itemToDelete.name)
        # return redirect(url_for('showCatalog', catalog_id=catalog_id))
        return render_template('deleteCatalogItem.html', item=itemToDelete)


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have been successfully logged out.")
        return redirect(url_for('showCatalogs'))
    else:
        flash("You were not logged in to begin with!")
        return redirect(url_for('showCatalogs'))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
