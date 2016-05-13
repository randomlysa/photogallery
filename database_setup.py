from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

class Catalog(Base):
    __tablename__ = 'catalog'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    header_image = Column(String(250))
    header_image_tn = Column(String(250))
    header_color = Column(String(8))
    catalog_thumbnail = Column(String(250))
    catalog_image_type = Column(String(25))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
           'header_image'    : self.header_image,
           'header_image_tn'    : self.header_image_tn,
       }

class CatalogItem(Base):
    __tablename__ = 'catalog_item'


    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(2500))
    item_image = Column(String(250))
    item_image_tn = Column(String(250))
    catalog_id = Column(Integer,ForeignKey('catalog.id'))
    catalog = relationship(Catalog)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'          : self.id,
           'name'         : self.name,
           'description'    : self.description,
           'image'        : self.item_image,
           'thumbnail'     : self.item_image_tn
       }



engine = create_engine('sqlite:///catalogwithusers.db')


Base.metadata.create_all(engine)
