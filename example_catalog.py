from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Catalog, Base, CatalogItem, User

engine = create_engine('sqlite:///catalogwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Sasha A", email="contact@oddlyindifferent.com")
session.add(User1)
session.commit()

# Catalog Dallas Arboretum

catalog1 = Catalog(
    user_id=1,
    name = "Dallas Arboretum",
    header_image = "user1_catalog1_header.jpg",
    header_image_tn = "user1_catalog1_header-tn.jpg",
    header_color = "FFFFFF",
    catalog_image_type = "item_image_tn"
)

session.add(catalog1)
session.commit()

# Example photos were taken by the author of this project, Sasha Afanasyev, 
# and are available on flickr (https://www.flickr.com/photos/sasha55068)
# under the creative commons Attribution-NonCommercial 2.0 Generic 
# CC BY-NC 2.0) license. https://creativecommons.org/licenses/by-nc/2.0/

catalogItem1 = CatalogItem(
    user_id=1, 
    name = "Dallas Arboretum",
    item_image="user1_catalog1_item1.jpg",
    item_image_tn="user1_catalog1_item1-tn.jpg",
    catalog_id=1    
)

session.add(catalogItem1)
session.commit()

catalogItem2 = CatalogItem(
    user_id=1, 
    name = "Dallas Arboretum",
    item_image="user1_catalog1_item2.jpg",
    item_image_tn="user1_catalog1_item2-tn.jpg",
    catalog_id=1    
)

session.add(catalogItem2)
session.commit()

catalogItem3 = CatalogItem(
    user_id=1, 
    name = "Dallas Arboretum",
    item_image="user1_catalog1_item3.jpg",
    item_image_tn="user1_catalog1_item3-tn.jpg",
    catalog_id=1    
)

session.add(catalogItem3)
session.commit()


print "added catalog items!"

